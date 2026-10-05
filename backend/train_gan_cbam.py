import os
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
SPLIT_JSON_PATH = os.path.join(CHECKPOINT_DIR, "dataset_split.json")

sys.path.append(BASE_DIR)
from models.gan.generator import GANCBAMGenerator
from models.gan.discriminator import GANDiscriminator
from services.metrics import calculate_reconstruction_metrics

class LeukemiaReconDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, _ = self.samples[idx]
        img = Image.open(path).convert('RGB')
        
        # Original target
        target = self.transform(img)
        
        # Simulate compression artifact (JPEG quality 15 like in evaluate_models)
        import io
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=15)
        buf.seek(0)
        comp_img = Image.open(buf).convert('RGB')
        comp_tensor = self.transform(comp_img)
        
        return comp_tensor, target

def safe_save_checkpoint(state_dict, save_path):
    tmp_path = save_path + ".tmp"
    torch.save(state_dict, tmp_path)
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
        except Exception:
            pass
    import shutil
    shutil.move(tmp_path, save_path)

def train_gan():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train GAN+CBAM] Device: {device}")

    with open(SPLIT_JSON_PATH, "r") as f:
        split_data = json.load(f)

    CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]
    class_to_idx = {c: i for i, c in enumerate(CLASSES)}
    train_samples = [(p, class_to_idx[c]) for p, c in split_data["train"]]
    val_samples = [(p, class_to_idx[c]) for p, c in split_data["val"]]

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        # Normalize to [-1, 1] for GANs often works well, but existing evaluate_models 
        # just uses ToTensor() and then transforms.ToPILImage(), which implies [0, 1] range.
    ])

    train_ds = LeukemiaReconDataset(train_samples, transform=transform)
    val_ds = LeukemiaReconDataset(val_samples, transform=transform)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=16, shuffle=False)

    generator = GANCBAMGenerator().to(device)
    discriminator = GANDiscriminator().to(device)

    # Load existing checkpoint if it exists to fine-tune and get better PSNR
    gen_ckpt = os.path.join(CHECKPOINT_DIR, "gan_cbam_generator.pth")
    if os.path.exists(gen_ckpt):
        generator.load_state_dict(torch.load(gen_ckpt, map_location=device))
        print(f"Loaded existing generator weights from {gen_ckpt}")

    disc_ckpt = os.path.join(CHECKPOINT_DIR, "gan_cbam_discriminator.pth")
    if os.path.exists(disc_ckpt):
        discriminator.load_state_dict(torch.load(disc_ckpt, map_location=device))

    # Optimizers
    opt_g = optim.Adam(generator.parameters(), lr=2e-4, betas=(0.5, 0.999))
    opt_d = optim.Adam(discriminator.parameters(), lr=2e-4, betas=(0.5, 0.999))

    # Losses
    criterion_gan = nn.BCEWithLogitsLoss()
    criterion_l1 = nn.L1Loss() # Crucial for higher PSNR (sharp edges)

    best_psnr = 0.0

    print("[Step 2] Fine-tuning GAN with L1 Loss for better PSNR...")
    # Just a few epochs to fine-tune
    for ep in range(5):
        generator.train()
        discriminator.train()
        
        for b_idx, (comp, target) in enumerate(train_loader):
            comp, target = comp.to(device), target.to(device)

            # Train Discriminator
            opt_d.zero_grad()
            real_out = discriminator(target)
            fake_img = generator(comp)
            fake_out = discriminator(fake_img.detach())
            
            # Label smoothing for real
            loss_d_real = criterion_gan(real_out, torch.full_like(real_out, 0.9))
            loss_d_fake = criterion_gan(fake_out, torch.zeros_like(fake_out))
            loss_d = (loss_d_real + loss_d_fake) / 2
            loss_d.backward()
            opt_d.step()

            # Train Generator
            opt_g.zero_grad()
            fake_out = discriminator(fake_img)
            loss_g_gan = criterion_gan(fake_out, torch.ones_like(fake_out))
            # Lambda=100 for L1 loss to prioritize PSNR/MSE
            loss_g_l1 = criterion_l1(fake_img, target) * 100 
            loss_g = loss_g_gan + loss_g_l1
            loss_g.backward()
            opt_g.step()
            if b_idx % 20 == 0:
                print(f"Epoch {ep+1}, Batch {b_idx}/{len(train_loader)} - G Loss: {loss_g.item():.4f}")

        # Validation
        generator.eval()
        total_psnr = 0.0
        val_batches = 0
        with torch.no_grad():
            for comp, target in val_loader:
                comp, target = comp.to(device), target.to(device)
                fake_img = generator(comp)
                
                # Calculate PSNR manually for validation loop
                mse = nn.MSELoss()(fake_img, target)
                if mse == 0:
                    psnr = 100
                else:
                    psnr = 10 * torch.log10(1.0 / mse).item()
                    
                total_psnr += psnr
                val_batches += 1

        avg_psnr = total_psnr / val_batches
        print(f" Epoch [{ep+1:2d}/5] Val PSNR: {avg_psnr:.2f} dB")

        if avg_psnr > best_psnr:
            best_psnr = avg_psnr
            safe_save_checkpoint(generator.state_dict(), gen_ckpt)
            safe_save_checkpoint(discriminator.state_dict(), disc_ckpt)
            print(f"   [SAVED BEST GAN] {avg_psnr:.2f} dB -> {gen_ckpt}")

if __name__ == "__main__":
    train_gan()
