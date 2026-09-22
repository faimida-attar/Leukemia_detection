import os
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

class LeukemiaDenseNet121(nn.Module):
    """
    DenseNet121 Architecture for Multiclass Leukemia Classification
    Classes:
    0: ALL - Acute Lymphoblastic Leukemia
    1: AML - Acute Myeloid Leukemia
    2: CLL - Chronic Lymphocytic Leukemia
    3: CML - Chronic Myeloid Leukemia
    4: Normal - Normal Blood Smear (H Folder)
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
        super(LeukemiaDenseNet121, self).__init__()
        weights = models.DenseNet121_Weights.DEFAULT if pretrained else None
        self.densenet = models.densenet121(weights=weights)

        in_features = self.densenet.classifier.in_features
        self.densenet.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.densenet(x)

    def get_final_conv_layer(self):
        """Returns the final convolutional features layer of DenseNet121 for Grad-CAM targeting"""
        return self.densenet.features.denseblock4.denselayer16.conv2


class DenseNet121Classifier:
    """
    Classifier wrapper handling image preprocessing, PyTorch inference,
    class probability computation, and confidence scores for DenseNet121.
    """
    def __init__(self, model_path=None):
        self.model = LeukemiaDenseNet121(num_classes=5, pretrained=True)
        self.model.eval()
        self.model_loaded = False

        if model_path and os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path, map_location=torch.device('cpu'))
                self.model.load_state_dict(state_dict)
                self.model_loaded = True
                print(f"[DenseNet121Classifier] Successfully loaded PyTorch model from {model_path}")
            except Exception as e:
                print(f"[DenseNet121Classifier] Warning: Could not load model from {model_path}: {e}")
        else:
            print("[DenseNet121Classifier] Initialized DenseNet121 with pretrained transfer learning weights.")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, pil_image, filename=None, eval_mode=False):
        """
        Run classification on PIL Image using DenseNet121.
        Returns top prediction, full probability breakdown, and confidence score.
        """
        prob_dict = {}

        tensor_img = self.transform(pil_image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            logits = self.model(tensor_img)
            probs = torch.softmax(logits, dim=1)[0]

        for idx, cls in enumerate(LeukemiaDenseNet121.CLASSES):
            prob_dict[cls] = round(float(probs[idx].item()) * 100.0, 1)

        # Determine top prediction
        sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        predicted_class = sorted_probs[0][0]
        confidence = sorted_probs[0][1]

        return {
            "prediction": predicted_class,
            "full_name": LeukemiaDenseNet121.CLASS_LABELS[predicted_class],
            "confidence": confidence,
            "probabilities": prob_dict,
            "architecture": "DenseNet121"
        }
