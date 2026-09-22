import os
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, TensorDataset
from torchvision import transforms
from PIL import Image

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
SPLIT_JSON_PATH = os.path.join(CHECKPOINT_DIR, "dataset_split.json")

sys.path.append(BASE_DIR)
from models.cnn.resnet_classifier import LeukemiaResNet50
from models.cnn.densenet_classifier import LeukemiaDenseNet121

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

def train_standalone():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train Standalone] Device: {device}")

    if not os.path.exists(SPLIT_JSON_PATH):
        print(f"[Error] Split json not found: {SPLIT_JSON_PATH}")
        return

    with open(SPLIT_JSON_PATH, "r") as f:
        split_data = json.load(f)

    CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]
    class_to_idx = {c: i for i, c in enumerate(CLASSES)}

    train_samples = [(p, class_to_idx[c]) for p, c in split_data["train"]]
    val_samples = [(p, class_to_idx[c]) for p, c in split_data["val"]]

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = LeukemiaDataset(train_samples, transform=transform)
    val_ds = LeukemiaDataset(val_samples, transform=transform)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=False)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)

    # 1. ResNet50
    print("\n--- Training Standalone ResNet50 ---")
    r_model = LeukemiaResNet50(num_classes=5, pretrained=True).to(device)
    # Extract 2048-dim features
    r_feature_extractor = nn.Sequential(*list(r_model.resnet.children())[:-1])
    r_feature_extractor.eval()

    r_train_feats, r_train_lbls = [], []
    r_val_feats, r_val_lbls = [], []

    with torch.no_grad():
        for imgs, lbls in train_loader:
            feats = torch.flatten(r_feature_extractor(imgs.to(device)), 1)
            r_train_feats.append(feats.cpu())
            r_train_lbls.append(lbls)
        for imgs, lbls in val_loader:
            feats = torch.flatten(r_feature_extractor(imgs.to(device)), 1)
            r_val_feats.append(feats.cpu())
            r_val_lbls.append(lbls)

    r_train_ds = TensorDataset(torch.cat(r_train_feats), torch.cat(r_train_lbls))
    r_val_ds = TensorDataset(torch.cat(r_val_feats), torch.cat(r_val_lbls))
    r_train_ld = DataLoader(r_train_ds, batch_size=64, shuffle=True)
    r_val_ld = DataLoader(r_val_ds, batch_size=64, shuffle=False)

    opt_r = optim.AdamW(r_model.resnet.fc.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    best_acc_r = 0.0

    for ep in range(15):
        r_model.resnet.fc.train()
        for f, l in r_train_ld:
            f, l = f.to(device), l.to(device)
            opt_r.zero_grad()
            out = r_model.resnet.fc(f)
            loss = criterion(out, l)
            loss.backward()
            opt_r.step()

        r_model.resnet.fc.eval()
        corr, tot = 0, 0
        with torch.no_grad():
            for f, l in r_val_ld:
                f, l = f.to(device), l.to(device)
                out = r_model.resnet.fc(f)
                _, p = torch.max(out, 1)
                corr += (p == l).sum().item()
                tot += l.size(0)
        val_acc = (corr / tot) * 100
        print(f"  ResNet50 Epoch [{ep+1:2d}/15] Val Acc: {val_acc:.2f}%")
        if val_acc >= best_acc_r:
            best_acc_r = val_acc
            safe_save_checkpoint(r_model.state_dict(), os.path.join(CHECKPOINT_DIR, "leukemia_resnet50.pth"))

    print(f"ResNet50 Best Val Acc: {best_acc_r:.2f}%")

    # 2. DenseNet121
    print("\n--- Training Standalone DenseNet121 ---")
    d_model = LeukemiaDenseNet121(num_classes=5, pretrained=True).to(device)
    d_feature_extractor = nn.Sequential(d_model.densenet.features, nn.AdaptiveAvgPool2d((1, 1)))
    d_feature_extractor.eval()

    d_train_feats, d_train_lbls = [], []
    d_val_feats, d_val_lbls = [], []

    with torch.no_grad():
        for imgs, lbls in train_loader:
            feats = torch.flatten(d_feature_extractor(imgs.to(device)), 1)
            d_train_feats.append(feats.cpu())
            d_train_lbls.append(lbls)
        for imgs, lbls in val_loader:
            feats = torch.flatten(d_feature_extractor(imgs.to(device)), 1)
            d_val_feats.append(feats.cpu())
            d_val_lbls.append(lbls)

    d_train_ds = TensorDataset(torch.cat(d_train_feats), torch.cat(d_train_lbls))
    d_val_ds = TensorDataset(torch.cat(d_val_feats), torch.cat(d_val_lbls))
    d_train_ld = DataLoader(d_train_ds, batch_size=64, shuffle=True)
    d_val_ld = DataLoader(d_val_ds, batch_size=64, shuffle=False)

    opt_d = optim.AdamW(d_model.densenet.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
    best_acc_d = 0.0

    for ep in range(15):
        d_model.densenet.classifier.train()
        for f, l in d_train_ld:
            f, l = f.to(device), l.to(device)
            opt_d.zero_grad()
            out = d_model.densenet.classifier(f)
            loss = criterion(out, l)
            loss.backward()
            opt_d.step()

        d_model.densenet.classifier.eval()
        corr, tot = 0, 0
        with torch.no_grad():
            for f, l in d_val_ld:
                f, l = f.to(device), l.to(device)
                out = d_model.densenet.classifier(f)
                _, p = torch.max(out, 1)
                corr += (p == l).sum().item()
                tot += l.size(0)
        val_acc = (corr / tot) * 100
        print(f"  DenseNet121 Epoch [{ep+1:2d}/15] Val Acc: {val_acc:.2f}%")
        if val_acc >= best_acc_d:
            best_acc_d = val_acc
            safe_save_checkpoint(d_model.state_dict(), os.path.join(CHECKPOINT_DIR, "leukemia_densenet121.pth"))

    print(f"DenseNet121 Best Val Acc: {best_acc_d:.2f}%")

if __name__ == "__main__":
    train_standalone()
