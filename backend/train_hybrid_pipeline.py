import os
import sys
import glob
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader, TensorDataset

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)
SPLIT_JSON_PATH = os.path.join(CHECKPOINT_DIR, "dataset_split.json")

# Candidate dataset paths (prioritizing pre-resized 224x224 cache)
CACHE_DIR = os.path.join(BASE_DIR, "dataset_cache_224")
CANDIDATE_DATASET_DIRS = [
    CACHE_DIR,
    r"c:\Users\FAIMIDA\OneDrive\Desktop\Lihatech\dataset\dataset",
    os.path.abspath(os.path.join(BASE_DIR, "..", "dataset")),
    os.path.abspath(os.path.join(BASE_DIR, "dataset"))
]

DATASET_ROOT = None
for cdir in CANDIDATE_DATASET_DIRS:
    if os.path.exists(cdir) and os.path.isdir(cdir):
        DATASET_ROOT = cdir
        break

print(f"[Training Setup] Using Dataset Root: '{DATASET_ROOT}'", flush=True)

if DATASET_ROOT == CACHE_DIR:
    DATASET_CLASS_MAP = {
        "ALL": "ALL",
        "AML": "AML",
        "CLL": "CLL",
        "CML": "CML",
        "Normal": "Normal"
    }
else:
    DATASET_CLASS_MAP = {
        "ALL": "ALL TEST-20230225T082325Z-001",
        "AML": "AML TEST-20230225T082630Z-001",
        "CLL": "CLL TEST-20230225T082851Z-001",
        "CML": "CML TEST-20230225T083148Z-001",
        "Normal": "H TEST-20230225T083612Z-001"
    }

CLASS_TO_IDX = {"ALL": 0, "AML": 1, "CLL": 2, "CML": 3, "Normal": 4}
CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]

from models.cnn.resnet_classifier import LeukemiaResNet50
from models.cnn.densenet_classifier import LeukemiaDenseNet121
from models.cnn.hybrid_classifier import LeukemiaHybridResNetDenseNet

class LeukemiaDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

def load_and_split_dataset():
    samples_by_class = {cls_name: [] for cls_name in CLASSES}
    total_images = 0

    for cls_name, subfolder in DATASET_CLASS_MAP.items():
        folder_path = os.path.join(DATASET_ROOT, subfolder)
        idx = CLASS_TO_IDX[cls_name]
        files = []
        if os.path.exists(folder_path):
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
                files.extend(glob.glob(os.path.join(folder_path, '**', ext), recursive=True))
        files = sorted(list(set(files)))
        for f in files:
            samples_by_class[cls_name].append((f, idx))
        print(f"  Class '{cls_name:6s}': {len(files)} microscopic images verified.", flush=True)
        total_images += len(files)

    print(f"[Dataset Verification] Total Verified Microscopy Images: {total_images}", flush=True)

    random.seed(42)
    train_samples, val_samples, test_samples = [], [], []

    split_info = {"train": [], "val": [], "test": []}

    for cls_name, items in samples_by_class.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        
        c_train = items[:n_train]
        c_val = items[n_train:n_train + n_val]
        c_test = items[n_train + n_val:]

        train_samples.extend(c_train)
        val_samples.extend(c_val)
        test_samples.extend(c_test)

        split_info["train"].extend([(p, cls_name) for p, _ in c_train])
        split_info["val"].extend([(p, cls_name) for p, _ in c_val])
        split_info["test"].extend([(p, cls_name) for p, _ in c_test])

    with open(SPLIT_JSON_PATH, "w") as f:
        json.dump(split_info, f, indent=2)

    print(f"[Stratified Split] Saved split to {SPLIT_JSON_PATH}")
    print(f" -> Train: {len(train_samples)} | Validation: {len(val_samples)} | Unseen Test: {len(test_samples)}", flush=True)

    return train_samples, val_samples, test_samples

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

def train_model(model, train_loader, val_loader, epochs, lr, save_filename, device, is_hybrid=False):
    print(f"\n=======================================================", flush=True)
    print(f" Training Model: {save_filename} on {device}", flush=True)
    print(f"=======================================================", flush=True)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    save_path = os.path.join(CHECKPOINT_DIR, save_filename)
    best_acc = 0.0

    if is_hybrid:
        print("[Stage 1] Fast Feature Extraction & Classifier Head Pre-training...", flush=True)
        model.eval()
        train_feats_list, train_lbls_list = [], []
        val_feats_list, val_lbls_list = [], []

        with torch.no_grad():
            for b_idx, (imgs, labels) in enumerate(train_loader):
                imgs = imgs.to(device)
                fused = model.extract_features(imgs)
                train_feats_list.append(fused.cpu())
                train_lbls_list.append(labels)
                if (b_idx + 1) % 20 == 0 or (b_idx + 1) == len(train_loader):
                    print(f"   [Feature Extract Train] Batch {b_idx+1}/{len(train_loader)} completed", flush=True)
            
            for b_idx, (imgs, labels) in enumerate(val_loader):
                imgs = imgs.to(device)
                fused = model.extract_features(imgs)
                val_feats_list.append(fused.cpu())
                val_lbls_list.append(labels)
                if (b_idx + 1) % 10 == 0 or (b_idx + 1) == len(val_loader):
                    print(f"   [Feature Extract Val] Batch {b_idx+1}/{len(val_loader)} completed", flush=True)

        train_feats = torch.cat(train_feats_list, dim=0)
        train_lbls = torch.cat(train_lbls_list, dim=0)
        val_feats = torch.cat(val_feats_list, dim=0)
        val_lbls = torch.cat(val_lbls_list, dim=0)

        feat_train_ds = TensorDataset(train_feats, train_lbls)
        feat_val_ds = TensorDataset(val_feats, val_lbls)

        feat_train_loader = DataLoader(feat_train_ds, batch_size=64, shuffle=True)
        feat_val_loader = DataLoader(feat_val_ds, batch_size=64, shuffle=False)

        optimizer_head = optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

        for ep in range(15):
            model.classifier.train()
            t_loss, t_corr, t_tot = 0.0, 0, 0
            for f_batch, l_batch in feat_train_loader:
                f_batch, l_batch = f_batch.to(device), l_batch.to(device)
                optimizer_head.zero_grad()
                out = model.classifier(f_batch)
                loss = criterion(out, l_batch)
                loss.backward()
                optimizer_head.step()
                t_loss += loss.item() * f_batch.size(0)
                _, preds = torch.max(out, 1)
                t_corr += (preds == l_batch).sum().item()
                t_tot += l_batch.size(0)

            model.classifier.eval()
            v_corr, v_tot = 0, 0
            with torch.no_grad():
                for f_batch, l_batch in feat_val_loader:
                    f_batch, l_batch = f_batch.to(device), l_batch.to(device)
                    out = model.classifier(f_batch)
                    _, preds = torch.max(out, 1)
                    v_corr += (preds == l_batch).sum().item()
                    v_tot += l_batch.size(0)

            w_train_acc = (t_corr / t_tot) * 100
            w_val_acc = (v_corr / v_tot) * 100
            print(f"   Head Warmup Epoch [{ep+1:2d}/15] Train Acc: {w_train_acc:6.2f}% | Val Acc: {w_val_acc:6.2f}%", flush=True)

            if w_val_acc >= best_acc:
                best_acc = w_val_acc
                safe_save_checkpoint(model.state_dict(), save_path)
                print(f"      [SAVED WARMUP CHECKPOINT] ({w_val_acc:.2f}%) to {save_path}", flush=True)

        print("[Stage 2] End-to-End Fine-Tuning of All Backbone Layers...", flush=True)

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for b_idx, (imgs, labels) in enumerate(train_loader):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * imgs.size(0)
            _, preds = torch.max(outputs, 1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

            if (b_idx + 1) % 25 == 0 or (b_idx + 1) == len(train_loader):
                print(f"   Epoch [{epoch+1}/{epochs}] Batch {b_idx+1}/{len(train_loader)} Loss: {loss.item():.4f}", flush=True)

        train_acc = (train_correct / train_total) * 100

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * imgs.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_acc = (val_correct / val_total) * 100
        scheduler.step()

        print(f"Epoch [{epoch+1:2d}/{epochs}] Train Loss: {train_loss/train_total:.4f} | Train Acc: {train_acc:6.2f}% | Val Loss: {val_loss/val_total:.4f} | Val Acc: {val_acc:6.2f}%", flush=True)

        if val_acc >= best_acc:
            best_acc = val_acc
            safe_save_checkpoint(model.state_dict(), save_path)
            print(f"   [SAVED BEST MODEL] Saved checkpoint ({val_acc:.2f}%) to {save_path}", flush=True)

    print(f"\n Finished training {save_filename}. Best Validation Accuracy: {best_acc:.2f}%\n", flush=True)

def main():
    torch.set_num_threads(16)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using PyTorch compute device: {device}", flush=True)

    train_samples, val_samples, test_samples = load_and_split_dataset()
    if not train_samples:
        print("Error: No images loaded from dataset!", flush=True)
        return

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_dataset = LeukemiaDataset(train_samples, transform=train_transform)
    val_dataset = LeukemiaDataset(val_samples, transform=val_transform)

    batch_size = 32
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # 1. Train Hybrid ResNet50 + DenseNet121 Model
    hybrid_model = LeukemiaHybridResNetDenseNet(num_classes=5, pretrained=True).to(device)
    train_model(hybrid_model, train_loader, val_loader, epochs=6, lr=5e-5, save_filename="leukemia_hybrid_resnet50_densenet121.pth", device=device, is_hybrid=True)

    # 2. Train Standalone ResNet50 Model
    resnet_model = LeukemiaResNet50(num_classes=5, pretrained=True).to(device)
    train_model(resnet_model, train_loader, val_loader, epochs=5, lr=5e-5, save_filename="leukemia_resnet50.pth", device=device, is_hybrid=False)

    # 3. Train Standalone DenseNet121 Model
    densenet_model = LeukemiaDenseNet121(num_classes=5, pretrained=True).to(device)
    train_model(densenet_model, train_loader, val_loader, epochs=5, lr=5e-5, save_filename="leukemia_densenet121.pth", device=device, is_hybrid=False)

if __name__ == "__main__":
    main()
