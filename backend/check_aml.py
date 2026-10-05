import json
import torch
import torchvision.transforms as transforms
from PIL import Image
import torch.nn.functional as F
import os
from models.cnn.resnet_classifier import LeukemiaResNet50
from models.cnn.densenet_classifier import LeukemiaDenseNet121
from models.cnn.hybrid_classifier import LeukemiaHybridResNetDenseNet

# Load checkpoints
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

resnet = LeukemiaResNet50().to(device)
resnet.load_state_dict(torch.load('models/checkpoints/leukemia_resnet50.pth', map_location=device))
resnet.eval()

densenet = LeukemiaDenseNet121().to(device)
densenet.load_state_dict(torch.load('models/checkpoints/leukemia_densenet121.pth', map_location=device))
densenet.eval()

hybrid = LeukemiaHybridResNetDenseNet().to(device)
hybrid.load_state_dict(torch.load('models/checkpoints/leukemia_hybrid_resnet50_densenet121.pth', map_location=device))
hybrid.eval()

CLASSES = ['ALL', 'AML', 'CLL', 'CML', 'Normal']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
print("CLASS_TO_IDX mapping:", CLASS_TO_IDX)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

with open('models/checkpoints/dataset_split.json', 'r') as f:
    data = json.load(f)

aml_test_samples = [x for x in data['test'] if x[1] == 'AML']
print(f"Total AML test samples: {len(aml_test_samples)}")

with torch.no_grad():
    for i, (path, label) in enumerate(aml_test_samples[:10]):
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        img = Image.open(path).convert('RGB')
        tensor = transform(img).unsqueeze(0).to(device)
        
        # ResNet
        res_out = resnet(tensor)
        res_prob = F.softmax(res_out, dim=1)[0].cpu().numpy()
        
        # DenseNet
        den_out = densenet(tensor)
        den_prob = F.softmax(den_out, dim=1)[0].cpu().numpy()
        
        # Hybrid
        hyb_out = hybrid(tensor)
        hyb_prob = F.softmax(hyb_out, dim=1)[0].cpu().numpy()
        
        print(f"\n--- Sample {i+1}: {os.path.basename(path)} ---")
        print(f"True Label: {label} (Idx: {CLASS_TO_IDX[label]})")
        
        for name, probs in [("ResNet50", res_prob), ("DenseNet121", den_prob), ("Hybrid", hyb_prob)]:
            pred_idx = probs.argmax()
            pred_class = CLASSES[pred_idx]
            print(f"{name} Prediction: {pred_class} ({probs[pred_idx]*100:.2f}%)")
            prob_str = ", ".join([f"{c}: {p*100:.2f}%" for c, p in zip(CLASSES, probs)])
            print(f"  Probs: {prob_str}")
