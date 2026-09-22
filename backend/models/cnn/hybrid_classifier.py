import os
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

class LeukemiaHybridResNetDenseNet(nn.Module):
    """
    Hybrid Deep Learning Architecture for Multiclass Leukemia Classification
    Backbone 1: ResNet50 (2048-dim feature vector)
    Backbone 2: DenseNet121 (1024-dim feature vector)
    Feature Fusion: Concatenation (3072-dim fused feature vector)
    Classification Head: Dense Linear layers for 5 classes (ALL, AML, CLL, CML, Normal)
    """
    CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]
    CLASS_LABELS = {
        "ALL": "Acute Lymphoblastic Leukemia",
        "AML": "Acute Myeloid Leukemia",
        "CLL": "Chronic Lymphocytic Leukemia",
        "CML": "Chronic Myeloid Leukemia",
        "Normal": "Normal Blood Smear"
    }

    def __init__(self, num_classes=5, pretrained=True):
        super(LeukemiaHybridResNetDenseNet, self).__init__()

        # ResNet50 Feature Extractor
        resnet_weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        self.resnet = models.resnet50(weights=resnet_weights)
        self.resnet_features = nn.Sequential(*list(self.resnet.children())[:-1])  # Output: (B, 2048, 1, 1)

        # DenseNet121 Feature Extractor
        densenet_weights = models.DenseNet121_Weights.DEFAULT if pretrained else None
        self.densenet = models.densenet121(weights=densenet_weights)
        self.densenet_features = self.densenet.features  # Output: (B, 1024, 7, 7) for 224x224 input
        self.densenet_pool = nn.AdaptiveAvgPool2d((1, 1))

        # Fusion Dimension: 2048 (ResNet) + 1024 (DenseNet) = 3072
        fusion_dim = 2048 + 1024

        # Fusion Classification Head
        self.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(fusion_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

    def extract_features(self, x):
        """
        Extract and fuse feature embeddings from ResNet50 and DenseNet121.
        Returns:
            fused_features: Tensor of shape (B, 3072)
        """
        r_feat = self.resnet_features(x)  # (B, 2048, 1, 1)
        r_feat = torch.flatten(r_feat, 1) # (B, 2048)

        d_feat = self.densenet_features(x)  # (B, 1024, H', W')
        d_feat = self.densenet_pool(d_feat) # (B, 1024, 1, 1)
        d_feat = torch.flatten(d_feat, 1)   # (B, 1024)

        # Feature Fusion via Concatenation
        fused_features = torch.cat((r_feat, d_feat), dim=1) # (B, 3072)
        return fused_features

    def forward(self, x):
        fused = self.extract_features(x)
        logits = self.classifier(fused)
        return logits

    def get_gradcam_target_layer(self):
        """
        Return target conv layer for Grad-CAM explainability.
        Returns ResNet50 final conv layer layer4[-1].conv3.
        """
        return self.resnet.layer4[-1].conv3


class HybridLeukemiaClassifier:
    """
    Classifier wrapper handling inference, feature fusion, class probabilities,
    and confidence scores for the ResNet50 + DenseNet121 hybrid model.
    """
    def __init__(self, model_path=None):
        self.model = LeukemiaHybridResNetDenseNet(num_classes=5, pretrained=True)
        self.model.eval()
        self.model_loaded = False
        
        if model_path and os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path, map_location=torch.device('cpu'))
                self.model.load_state_dict(state_dict)
                self.model_loaded = True
                print(f"[HybridLeukemiaClassifier] Successfully loaded hybrid PyTorch weights from {model_path}")
            except Exception as e:
                print(f"[HybridLeukemiaClassifier] Warning: Could not load hybrid model from {model_path}: {e}")
        else:
            print("[HybridLeukemiaClassifier] Initialized hybrid architecture with pretrained transfer learning weights.")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, pil_image, filename=None, eval_mode=False):
        """
        Run hybrid classification on PIL Image.
        Returns predicted class, full probabilities, confidence score, and feature info.
        """
        prob_dict = {}
        tensor_img = self.transform(pil_image.convert("RGB")).unsqueeze(0)

        with torch.no_grad():
            logits = self.model(tensor_img)
            probs = torch.softmax(logits, dim=1)[0]

        for idx, cls in enumerate(LeukemiaHybridResNetDenseNet.CLASSES):
            prob_dict[cls] = round(float(probs[idx].item()) * 100.0, 1)

        sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        predicted_class = sorted_probs[0][0]
        confidence = sorted_probs[0][1]

        return {
            "prediction": predicted_class,
            "full_name": LeukemiaHybridResNetDenseNet.CLASS_LABELS[predicted_class],
            "confidence": confidence,
            "probabilities": prob_dict,
            "architecture": "ResNet50 + DenseNet121 Hybrid (Feature Fusion)",
            "fusion_features": 3072
        }
