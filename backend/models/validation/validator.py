import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image

class ValidationCNN(nn.Module):
    """
    Lightweight PyTorch Binary Classifier for Blood Smear Microscopy Image Validation
    Class 1: Valid Blood Smear Microscopy Image
    Class 0: Invalid Non-Microscopy Image (Photos, Screenshots, Documents, Landscapes, etc.)
    """
    def __init__(self):
        super(ValidationCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 2)
        )

    def forward(self, x):
        features = self.features(x)
        logits = self.classifier(features)
        return logits


class ImageValidator:
    """
    Comprehensive Image Validation Engine combining Wright-Giemsa stain color space
    statistics, nuclear density analysis, and PyTorch deep learning verification.
    """
    def __init__(self, model_path=None):
        self.model = ValidationCNN()
        self.model.eval()
        self.model_loaded = False
        
        if model_path:
            try:
                state_dict = torch.load(model_path, map_location=torch.device('cpu'))
                self.model.load_state_dict(state_dict)
                self.model_loaded = True
            except Exception as e:
                print(f"[Validator] Warning: Could not load model from {model_path}: {e}")

        self.transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def analyze_color_stain_features(self, cv2_img):
        """
        Inspect Wright-Giemsa / Leishman stain color profiles:
        - Purple/Violet nucleus hue range in HSV
        - Pinkish/Red cytoplasm/RBC hue range
        - Background brightness & saturation distribution
        """
        if cv2_img is None or cv2_img.size == 0:
            return 0.0, "Empty image"

        hsv = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        # Purple/Violet nucleus stain mask (Hue 125 - 165 in OpenCV 0-180 range)
        purple_mask = cv2.inRange(hsv, np.array([120, 40, 40]), np.array([168, 255, 255]))
        purple_ratio = np.sum(purple_mask > 0) / (cv2_img.shape[0] * cv2_img.shape[1])

        # Pinkish/Red RBC stain mask
        pink_mask = cv2.inRange(hsv, np.array([165, 30, 60]), np.array([180, 255, 255])) + \
                    cv2.inRange(hsv, np.array([0, 30, 60]), np.array([15, 255, 255]))
        pink_ratio = np.sum(pink_mask > 0) / (cv2_img.shape[0] * cv2_img.shape[1])

        # Bright background ratio (typical in slide microscopy)
        bright_bg_ratio = np.sum(v > 180) / (cv2_img.shape[0] * cv2_img.shape[1])

        # Calculate composite biological microscopy stain index
        stain_score = (purple_ratio * 4.0) + (pink_ratio * 2.0) + (bright_bg_ratio * 0.5)

        # Check for non-microscopy anomalies (e.g. document text / high contrast sharp black-white edges)
        gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        return stain_score, purple_ratio, pink_ratio, bright_bg_ratio, laplacian_var

    def validate(self, pil_image, cv2_image=None):
        """
        Validate whether uploaded image is a genuine blood-smear microscopy image.
        Returns dictionary with validation outcome, confidence score, and details.
        """
        try:
            if cv2_image is None:
                cv2_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            w, h = pil_image.size
            if w < 50 or h < 50:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image",
                    "reason": "Image resolution too small to be a readable microscopy slide."
                }

            # 1. Color stain & morphology analysis
            stain_score, purple_ratio, pink_ratio, bright_bg, lap_var = self.analyze_color_stain_features(cv2_image)

            # 2. PyTorch Deep Learning Classifier validation
            tensor_img = self.transform(pil_image).unsqueeze(0)
            with torch.no_grad():
                logits = self.model(tensor_img)
                probs = torch.softmax(logits, dim=1)[0]
                valid_prob = probs[1].item()
                invalid_prob = probs[0].item()

            # Rule combination: Deep Learning score + Stain Feature rule checking
            # Non-microscopy images (text, landscapes, natural photos) usually have zero or negligible purple stain ratio
            # Genuine blood smears have softer textures (lap_var typically < 800) and substantial stain.
            is_microscopy_texture = lap_var < 1000
            
            has_microscopy_stain = (
                (purple_ratio > 0.015 or pink_ratio > 0.05)
                and is_microscopy_texture
            )

            if self.model_loaded:
                is_valid = (valid_prob > 0.5) and has_microscopy_stain
                confidence = valid_prob if is_valid else invalid_prob
            else:
                # Fallback stain feature verification if model checkpoint not yet initialized
                is_valid = has_microscopy_stain
                confidence = min(0.99, max(0.60, stain_score * 0.85))

            if is_valid:
                return {
                    "is_valid": True,
                    "confidence": round(float(confidence), 4),
                    "status": "Valid Microscopy Image",
                    "reason": "Valid Blood-Smear Microscopy Image confirmed (Wright-Giemsa stained blood cell structures detected).",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }
            else:
                return {
                    "is_valid": False,
                    "confidence": round(float(confidence), 4),
                    "status": "Invalid Image – No Classification",
                    "reason": "Invalid Image – No Classification: Uploaded file does not contain blood-smear microscopy cell structures.",
                    "prediction": "Invalid Image – No Classification",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }
        except Exception as e:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "status": "Invalid Image",
                "reason": f"Error validating image structure: {str(e)}"
            }
