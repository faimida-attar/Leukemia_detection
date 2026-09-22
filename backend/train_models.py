import os
import io
import cv2
import glob
import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image, ImageDraw, ImageFilter
import torchvision.transforms as transforms

# Import project model architectures
from models.validation.validator import ValidationCNN
from models.gan.generator import GANCBAMGenerator
from models.gan.discriminator import GANDiscriminator
from models.cnn.resnet_classifier import LeukemiaResNet50

BASE_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "dataset"))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_images")

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

# Map class names to dataset subfolders
DATASET_CLASS_MAP = {
    "ALL": "ALL TEST-20230225T082325Z-001",
    "AML": "AML TEST-20230225T082630Z-001",
    "CLL": "CLL TEST-20230225T082851Z-001",
    "CML": "CML TEST-20230225T083148Z-001",
    "Normal": "H TEST-20230225T083612Z-001"
}

CLASS_TO_IDX = {"ALL": 0, "AML": 1, "CLL": 2, "CML": 3, "Normal": 4}

def get_all_dataset_image_paths():
    """Scan and index all image filepaths in the dataset directory grouped by class."""
    class_paths = {}
    for cls_name, subfolder in DATASET_CLASS_MAP.items():
        folder_path = os.path.join(DATASET_DIR, subfolder)
        image_files = []
        if os.path.exists(folder_path):
            image_files.extend(glob.glob(os.path.join(folder_path, "**", "*.jpg"), recursive=True))
            image_files.extend(glob.glob(os.path.join(folder_path, "**", "*.jpeg"), recursive=True))
            image_files.extend(glob.glob(os.path.join(folder_path, "**", "*.png"), recursive=True))
        class_paths[cls_name] = image_files
        print(f"[Dataset] Class '{cls_name}': {len(image_files)} real microscopy images found.", flush=True)
    return class_paths


def generate_invalid_image(img_type="document", img_size=(256, 256)):
    """Generate non-microscopy images for Validation model negative samples."""
    w, h = img_size
    if img_type == "document":
        img = Image.new("RGB", (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        for y in range(20, h - 20, 18):
            line_w = random.randint(80, w - 40)
            draw.line([30, y, line_w, y], fill=(40, 40, 40), width=3)
    elif img_type == "landscape":
        img = Image.new("RGB", (w, h), (100, 180, 245))
        draw = ImageDraw.Draw(img)
        draw.polygon([(0, h), (w//2, h//2), (w, h)], fill=(40, 140, 50))
        draw.ellipse([w - 60, 20, w - 20, 60], fill=(255, 220, 50))
    else:
        img = Image.new("RGB", (w, h), (220, 190, 160))
        draw = ImageDraw.Draw(img)
        draw.ellipse([w//4, h//4, 3*w//4, 3*h//4], fill=(70, 40, 20))

    return img


def train_validation_model(class_paths):
    print("\n=======================================================", flush=True)
    print("[Training 1/3] Training Validation Model (Microscopy vs Invalid)...", flush=True)
    print("=======================================================", flush=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ValidationCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    valid_paths = []
    for paths in class_paths.values():
        valid_paths.extend(paths)

    if not valid_paths:
        print("[Warning] No real dataset images found for validator training.", flush=True)
        return

    random.shuffle(valid_paths)

    epochs = 3
    steps_per_epoch = 15
    model.train()

    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0

        for step in range(steps_per_epoch):
            batch_tensors = []
            batch_labels = []

            # 16 Valid Microscopy Slides from real dataset
            sampled_valid = random.sample(valid_paths, 16)
            for p in sampled_valid:
                try:
                    img = Image.open(p).convert("RGB")
                    batch_tensors.append(transform(img))
                    batch_labels.append(1) # Valid microscopy
                except Exception:
                    continue

            # 16 Invalid non-microscopy slides
            for _ in range(16):
                itype = random.choice(["document", "landscape", "photo"])
                img = generate_invalid_image(itype)
                batch_tensors.append(transform(img))
                batch_labels.append(0) # Invalid non-microscopy

            if len(batch_tensors) == 0:
                continue

            t_x = torch.stack(batch_tensors).to(device)
            t_y = torch.tensor(batch_labels, dtype=torch.long).to(device)

            optimizer.zero_grad()
            outputs = model(t_x)
            loss = criterion(outputs, t_y)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            correct += (preds == t_y).sum().item()
            total += t_y.size(0)

        acc = (correct / total) * 100 if total > 0 else 0
        avg_loss = running_loss / steps_per_epoch
        print(f"Epoch [{epoch+1}/{epochs}] Loss: {avg_loss:.4f} | Accuracy: {acc:.2f}%", flush=True)

    save_path = os.path.join(CHECKPOINT_DIR, "validator.pth")
    torch.save(model.state_dict(), save_path)
    print(f" Saved Validation model to {save_path}", flush=True)


def train_gan_cbam_model(class_paths):
    print("\n=======================================================", flush=True)
    print("[Training 2/3] Training GAN + CBAM Reconstruction Model...", flush=True)
    print("=======================================================", flush=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    generator = GANCBAMGenerator().to(device)
    discriminator = GANDiscriminator().to(device)
    
    g_optimizer = optim.Adam(generator.parameters(), lr=0.0002, betas=(0.5, 0.999))
    d_optimizer = optim.Adam(discriminator.parameters(), lr=0.0002, betas=(0.5, 0.999))
    
    pixel_loss = nn.L1Loss()
    adv_loss = nn.BCELoss()

    transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor()
    ])

    all_paths = []
    for paths in class_paths.values():
        all_paths.extend(paths)

    if not all_paths:
        print("[Warning] No real dataset images found for GAN training.", flush=True)
        return

    epochs = 3
    steps_per_epoch = 15
    batch_size = 6

    generator.train()
    discriminator.train()

    for epoch in range(epochs):
        g_running_loss = 0.0
        d_running_loss = 0.0

        for step in range(steps_per_epoch):
            batch_paths = random.sample(all_paths, batch_size)
            orig_tensors = []
            comp_tensors = []

            for p in batch_paths:
                try:
                    orig_img = Image.open(p).convert("RGB").resize((256, 256))

                    # Compress using JPEG quality (15-35)
                    buf = io.BytesIO()
                    orig_img.save(buf, format="JPEG", quality=random.randint(15, 35))
                    buf.seek(0)
                    comp_img = Image.open(buf).convert("RGB")

                    orig_tensors.append(transform(orig_img))
                    comp_tensors.append(transform(comp_img))
                except Exception:
                    continue

            if len(orig_tensors) == 0:
                continue

            real_imgs = torch.stack(orig_tensors).to(device)
            comp_imgs = torch.stack(comp_tensors).to(device)
            b_size = real_imgs.size(0)

            real_labels = torch.ones(b_size, 1).to(device)
            fake_labels = torch.zeros(b_size, 1).to(device)

            # Train Discriminator
            d_optimizer.zero_grad()
            recon_imgs = generator(comp_imgs)
            d_real = discriminator(real_imgs)
            d_fake = discriminator(recon_imgs.detach())

            d_loss_real = adv_loss(d_real, real_labels)
            d_loss_fake = adv_loss(d_fake, fake_labels)
            d_loss = (d_loss_real + d_loss_fake) / 2.0
            d_loss.backward()
            d_optimizer.step()

            # Train Generator
            g_optimizer.zero_grad()
            d_fake_g = discriminator(recon_imgs)
            g_adv = adv_loss(d_fake_g, real_labels)
            g_pix = pixel_loss(recon_imgs, real_imgs) * 100.0
            g_loss = g_adv + g_pix
            g_loss.backward()
            g_optimizer.step()

            g_running_loss += g_loss.item()
            d_running_loss += d_loss.item()

        print(f"Epoch [{epoch+1}/{epochs}] G Loss: {g_running_loss/steps_per_epoch:.4f} | D Loss: {d_running_loss/steps_per_epoch:.4f}", flush=True)

    save_path = os.path.join(CHECKPOINT_DIR, "gan_cbam_generator.pth")
    torch.save(generator.state_dict(), save_path)
    print(f" Saved GAN+CBAM Generator model to {save_path}", flush=True)


def train_resnet_classifier(class_paths):
    print("\n=======================================================", flush=True)
    print("[Training 3/3] Training ResNet50 Classifier (ALL, AML, CLL, CML, Normal)...", flush=True)
    print("=======================================================", flush=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Initialize with pretrained weights for feature transfer learning
    model = LeukemiaResNet50(num_classes=5, pretrained=True).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.0001, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    epochs = 8
    steps_per_epoch = 30

    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0

        for step in range(steps_per_epoch):
            batch_imgs = []
            batch_labels = []

            for cls_name, idx in CLASS_TO_IDX.items():
                paths = class_paths.get(cls_name, [])
                if not paths:
                    continue

                # Sample 8 images per class
                sampled = random.sample(paths, min(8, len(paths)))
                for p in sampled:
                    try:
                        img = Image.open(p).convert("RGB")
                        batch_imgs.append(train_transform(img))
                        batch_labels.append(idx)
                    except Exception:
                        continue

            if len(batch_imgs) == 0:
                continue

            t_x = torch.stack(batch_imgs).to(device)
            t_y = torch.tensor(batch_labels, dtype=torch.long).to(device)

            optimizer.zero_grad()
            outputs = model(t_x)
            loss = criterion(outputs, t_y)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            correct += (preds == t_y).sum().item()
            total += t_y.size(0)

        acc = (correct / total) * 100 if total > 0 else 0
        avg_loss = running_loss / steps_per_epoch
        print(f"Epoch [{epoch+1}/{epochs}] Classifier Loss: {avg_loss:.4f} | Accuracy: {acc:.2f}%", flush=True)

    save_path = os.path.join(CHECKPOINT_DIR, "leukemia_resnet50.pth")
    torch.save(model.state_dict(), save_path)
    print(f" Saved ResNet50 Classifier PyTorch checkpoint to {save_path}", flush=True)

    # Export to .h5 format using h5py
    h5_save_path = os.path.join(CHECKPOINT_DIR, "leukemia_resnet50.h5")
    try:
        import h5py
        with h5py.File(h5_save_path, 'w') as f:
            for param_name, param_tensor in model.state_dict().items():
                f.create_dataset(param_name, data=param_tensor.cpu().numpy())
        print(f" Saved ResNet50 Classifier model to {h5_save_path}", flush=True)
    except Exception as h5_err:
        print(f" Note: Could not export to .h5 ({h5_err})", flush=True)



def generate_preset_sample_images(class_paths):
    print("\n=======================================================", flush=True)
    print("[Sample Extraction] Copying real dataset sample slides to sample_images/...", flush=True)
    print("=======================================================", flush=True)
    
    samples_map = {
        "ALL": "sample_all.jpg",
        "AML": "sample_aml.jpg",
        "CLL": "sample_cll.jpg",
        "CML": "sample_cml.jpg",
        "Normal": "sample_normal.jpg"
    }

    for cls_name, fname in samples_map.items():
        paths = class_paths.get(cls_name, [])
        if paths:
            chosen = random.choice(paths)
            img = Image.open(chosen).convert("RGB").resize((512, 512))
            dest = os.path.join(SAMPLE_DIR, fname)
            img.save(dest, format="JPEG", quality=90)
            print(f" Saved real dataset preset sample: {dest}", flush=True)

    invalid_img = generate_invalid_image("document", (512, 512))
    invalid_dest = os.path.join(SAMPLE_DIR, "sample_invalid_photo.jpg")
    invalid_img.save(invalid_dest, format="JPEG", quality=90)
    print(f" Saved invalid document preset sample: {invalid_dest}", flush=True)


if __name__ == "__main__":
    print("=======================================================", flush=True)
    print("      TRAINING PYTORCH LEUKEMIA RESEARCH MODELS        ", flush=True)
    print("=======================================================", flush=True)
    
    class_paths = get_all_dataset_image_paths()
    train_validation_model(class_paths)
    train_gan_cbam_model(class_paths)
    train_resnet_classifier(class_paths)
    generate_preset_sample_images(class_paths)
    
    print("\n[SUCCESS] All PyTorch models trained on real dataset images successfully!", flush=True)

