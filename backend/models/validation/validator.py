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
        - Purple/Violet nucleus hue range in HSV (Azure B / Methylene Blue)
        - Pinkish/Red cytoplasm/RBC hue range (Eosin)
        - Background brightness & saturation distribution
        - Cellular morphology & discrete cell contour metrics
        """
        if cv2_img is None or cv2_img.size == 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0

        h, w = cv2_img.shape[:2]
        total_pixels = float(h * w)
        hsv = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # 1. Purple/Violet nucleus stain mask (Azure B / Methylene Blue: Hue 120-168)
        purple_mask = cv2.inRange(hsv, np.array([120, 30, 30]), np.array([168, 255, 255]))
        purple_ratio = np.sum(purple_mask > 0) / total_pixels

        # 2. Pinkish/Red RBC stain mask (Eosin)
        pink_mask = cv2.inRange(hsv, np.array([165, 30, 50]), np.array([180, 255, 255])) + \
                    cv2.inRange(hsv, np.array([0, 30, 50]), np.array([15, 255, 255]))
        pink_ratio = np.sum(pink_mask > 0) / total_pixels

        # 3. Bright background ratio (microscopy condenser illumination)
        bright_bg_ratio = np.sum(v_channel > 150) / total_pixels

        # 4. Laplacian variance (texture frequency)
        gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 5. Discrete Cellular Morphology Verification (isolated blood cells)
        cell_mask = cv2.bitwise_or(purple_mask, pink_mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_mask = cv2.morphologyEx(cell_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cell_count = 0
        total_cell_area = 0.0
        for c in contours:
            area = cv2.contourArea(c)
            if area >= 80:
                peri = cv2.arcLength(c, True)
                if peri > 0:
                    circularity = 4 * np.pi * area / (peri * peri)
                    if circularity >= 0.15:
                        cell_count += 1
                        total_cell_area += area

        cell_coverage = total_cell_area / total_pixels
        stain_score = (purple_ratio * 4.0) + (pink_ratio * 2.0) + (bright_bg_ratio * 0.5)

        return stain_score, purple_ratio, pink_ratio, bright_bg_ratio, laplacian_var, cell_count, cell_coverage

    def validate(self, pil_image, cv2_image=None):
        """
        Validate whether uploaded image is a genuine blood-smear microscopy image.
        Rejects camera photographs, natural landscapes, portraits/selfies, documents/text,
        and invalid non-blood-smear microscopic images before prediction.
        """
        try:
            if cv2_image is None:
                cv2_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            w, h = pil_image.size
            total_pixels = float(w * h)

            # Check 1: Resolution & Aspect Ratio
            if w < 64 or h < 64:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image",
                    "reason": "Image resolution is too small to be a diagnostic blood-smear microscopy slide."
                }

            aspect_ratio = max(w, h) / max(1, min(w, h))
            if aspect_ratio > 4.5:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image",
                    "reason": "Abnormal aspect ratio. Microscopic slide images maintain balanced proportions."
                }

            # Check 2: Color stain & morphology analysis
            stain_score, purple_ratio, pink_ratio, bright_bg, lap_var, cell_count, cell_cov = self.analyze_color_stain_features(cv2_image)

            # Check 3: Document / Text detection (sharp dark print on white background)
            gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
            black_ratio = np.sum(gray < 50) / total_pixels
            white_ratio = np.sum(gray > 220) / total_pixels
            if black_ratio > 0.03 and white_ratio > 0.60:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image - No Classification",
                    "reason": "Document or text photograph detected. Please upload a genuine peripheral blood-smear microscopic slide.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 4: Mandatory Wright-Giemsa Leukocyte Nucleus Verification
            # Peripheral blood smear leukemia analysis requires leukocyte chromatin (purple/violet stain)
            if purple_ratio < 0.008:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image - No Classification",
                    "reason": "Invalid non-blood smear image: No leukocyte cell structures detected (missing Wright-Giemsa nuclear purple staining).",
                    "prediction": "Invalid Image - No Classification",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }

            # Check 5: Monolithic scene rejection (Skin, walls, solid colors, tissue biopsy sheets)
            if cell_cov > 0.85:
                return {
                    "is_valid": False,
                    "confidence": 0.96,
                    "status": "Invalid Image - No Classification",
                    "reason": "Monolithic non-microscopic scene detected (lacks discrete blood cell distribution on slide background).",
                    "prediction": "Invalid Image - No Classification",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }

            # Check 6: Discrete cellular morphology verification
            if cell_count < 2 and cell_cov < 0.01:
                return {
                    "is_valid": False,
                    "confidence": 0.95,
                    "status": "Invalid Image - No Classification",
                    "reason": "Insufficient cellular morphology: No discrete blood cell structures identified on the slide field.",
                    "prediction": "Invalid Image - No Classification",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }

            # Check 7: PyTorch Deep Learning Classifier validation
            valid_prob = 1.0
            invalid_prob = 0.0
            if self.model_loaded:
                tensor_img = self.transform(pil_image).unsqueeze(0)
                with torch.no_grad():
                    logits = self.model(tensor_img)
                    probs = torch.softmax(logits, dim=1)[0]
                    valid_prob = float(probs[1].item())
                    invalid_prob = float(probs[0].item())

            # Combined Verification: Deep Learning probability + Biological Stain & Morphology criteria
            is_valid = (valid_prob >= 0.50) if self.model_loaded else True
            confidence = valid_prob if is_valid else invalid_prob

            if is_valid:
                return {
                    "is_valid": True,
                    "confidence": round(float(confidence), 4),
                    "status": "Valid Microscopy Image",
                    "reason": "Valid Blood-Smear Microscopy Image confirmed (Wright-Giemsa stained leukocyte & erythrocyte cellular structures detected).",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    },
                    "morphology_metrics": {
                        "cell_count": cell_count,
                        "cellular_coverage": round(float(cell_cov), 4)
                    }
                }
            else:
                return {
                    "is_valid": False,
                    "confidence": round(float(confidence), 4),
                    "status": "Invalid Image - No Classification",
                    "reason": "Invalid non-microscopy image: Deep learning validator identified non-microscopic visual artifacts.",
                    "prediction": "Invalid Image - No Classification",
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
