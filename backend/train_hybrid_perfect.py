import os
import sys
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
SPLIT_JSON_PATH = os.path.join(CHECKPOINT_DIR, "dataset_split.json")

sys.path.append(BASE_DIR)
from models.cnn.hybrid_classifier import LeukemiaHybridResNetDenseNet

class LeukemiaDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, label

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

def train_hybrid_perfect():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train Hybrid Perfect] Device: {device}")

    if not os.path.exists(SPLIT_JSON_PATH):
        print(f"[Error] Split json not found: {SPLIT_JSON_PATH}")
        return

    with open(SPLIT_JSON_PATH, "r") as f:
        split_data = json.load(f)

    CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]
    class_to_idx = {c: i for i, c in enumerate(CLASSES)}

    train_samples = [(p, class_to_idx[c]) for p, c in split_data["train"]]
    val_samples = [(p, class_to_idx[c]) for p, c in split_data["val"]]

    # Data Augmentation to prevent ALL/AML confusion
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = LeukemiaDataset(train_samples, transform=train_transform)
    val_ds = LeukemiaDataset(val_samples, transform=val_transform)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

    # Load previously trained checkpoint if exists, otherwise pretrained=True
    save_path = os.path.join(CHECKPOINT_DIR, "leukemia_hybrid_resnet50_densenet121.pth")
    model = LeukemiaHybridResNetDenseNet(num_classes=5, pretrained=True).to(device)
    
    if os.path.exists(save_path):
        print("[Load Checkpoint] Loading existing hybrid weights to fine-tune...")
        model.load_state_dict(torch.load(save_path, map_location=device))

    # Fine-tuning: train the entire model end-to-end, but with a low learning rate
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-3)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-6)

    best_acc = 0.0

    print("[Step 2] Fine-tuning end-to-end with Augmentation...")
    for ep in range(1):
        model.train()
        t_corr, t_tot = 0, 0
        
        for b_idx, (imgs, lbls) in enumerate(train_loader):
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            
            # Using end-to-end forward pass
            r_feat = F.normalize(torch.flatten(model.resnet_features(imgs), 1), p=2, dim=1)
            d_feat = F.normalize(torch.flatten(model.densenet_pool(model.densenet_features(imgs)), 1), p=2, dim=1)
            fused = torch.cat((r_feat, d_feat), dim=1)
            out = model.classifier(fused)
            
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()

            _, p = torch.max(out, 1)
            t_corr += (p == lbls).sum().item()
            t_tot += lbls.size(0)

        scheduler.step()
        model.eval()
        v_corr, v_tot = 0, 0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs, lbls = imgs.to(device), lbls.to(device)
                r_feat = F.normalize(torch.flatten(model.resnet_features(imgs), 1), p=2, dim=1)
                d_feat = F.normalize(torch.flatten(model.densenet_pool(model.densenet_features(imgs)), 1), p=2, dim=1)
                fused = torch.cat((r_feat, d_feat), dim=1)
                out = model.classifier(fused)
                
                _, p = torch.max(out, 1)
                v_corr += (p == lbls).sum().item()
                v_tot += lbls.size(0)

        train_acc = (t_corr / t_tot) * 100
        val_acc = (v_corr / v_tot) * 100
        print(f" Epoch [{ep+1:2d}/10] Train Acc: {train_acc:6.2f}% | Val Acc: {val_acc:6.2f}%")

        if val_acc >= best_acc:
            best_acc = val_acc
            safe_save_checkpoint(model.state_dict(), save_path)
            print(f"   [SAVED BEST MODEL] {val_acc:.2f}% -> {save_path}")

    print(f"\n[Finished] Best Validation Accuracy: {best_acc:.2f}%\n")

if __name__ == "__main__":
    train_hybrid_perfect()
