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
        Inspect Wright-Giemsa / Leishman stain color profiles and cytology metrics:
        - Purple/Violet nucleus chromatin hue & Azure B green-absorption profile
        - Pinkish/Salmon cytoplasm and RBC hue range (Eosin)
        - Brightfield slide background condenser illumination
        - Discrete cellular morphology and contour circularity
        """
        if cv2_img is None or cv2_img.size == 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

        orig_h, orig_w = cv2_img.shape[:2]

        # Memory & Speed Optimization:
        # Scale to max dimension 1024 for color stain & morphological analysis.
        # Color stain proportions, background luminance, and contour distributions
        # are scale-invariant, while reducing peak RAM from 1+ GB down to ~2 MB.
        if max(orig_h, orig_w) > 1024:
            scale = 1024.0 / max(orig_h, orig_w)
            target_w = max(64, int(orig_w * scale))
            target_h = max(64, int(orig_h * scale))
            cv2_eval = cv2.resize(cv2_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            cv2_eval = cv2_img

        h, w = cv2_eval.shape[:2]
        total_pixels = float(h * w)
        hsv = cv2.cvtColor(cv2_eval, cv2.COLOR_BGR2HSV)
        rgb = cv2.cvtColor(cv2_eval, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(cv2_eval, cv2.COLOR_BGR2GRAY)

        H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        # Use int16 to avoid 64-bit int allocations while preventing overflow
        R, G, B = rgb[:, :, 0].astype(np.int16), rgb[:, :, 1].astype(np.int16), rgb[:, :, 2].astype(np.int16)

        # 1. Color differentiation (rejects monochrome/grayscale medical images: X-Ray, CT, MRI, Ultrasound)
        color_diff = float(np.mean(np.abs(R - G) + np.abs(G - B) + np.abs(B - R)))
        s_mean = float(np.mean(S))
        v_mean = float(np.mean(V))

        # 2. Strict Wright-Giemsa Azure B purple nucleus chromatin stain:
        # Azure B binds to acidic nucleic acids, absorbing green light (550-650nm) -> B > G + 8 and R > G + 6.
        # Must have R >= 25 (rules out pure blue sky/objects), S >= 25, V >= 25, and Hue in violet/purple [126, 168].
        giemsa_purple = (B > G + 8) & (R > G + 6) & (S >= 25) & (V >= 25) & (R >= 25) & (H >= 126) & (H <= 168)
        purple_ratio = float(np.sum(giemsa_purple) / total_pixels)

        # 3. RBC Eosin Pink/Salmon stain mask
        eosin_rbc = ((H <= 18) | (H >= 165)) & (S >= 20) & (V >= 60) & (R > G)
        pink_ratio = float(np.sum(eosin_rbc) / total_pixels)

        # 4. Bright background ratio (microscopy condenser illumination)
        bright_bg_ratio = float(np.sum((V >= 135) & (S <= 95)) / total_pixels)

        # 5. Natural scene foliage green (grass, trees, plants)
        green_foliage = (H >= 35) & (H <= 82) & (S >= 35) & (G > R + 5)
        green_ratio = float(np.sum(green_foliage) / total_pixels)

        # 6. Laplacian variance (texture frequency)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())

        # 7. Discrete Leukocyte Chromatin Contour Analysis
        p_mask = giemsa_purple.astype(np.uint8) * 255
        p_contours, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_p_area = max(5, int(15 * (total_pixels / (4160 * 3120))))
        p_areas = [cv2.contourArea(c) for c in p_contours if cv2.contourArea(c) >= min_p_area]
        max_p_area = max(p_areas) if p_areas else 0.0
        max_purple_contour_ratio = float(max_p_area / total_pixels)
        p_count = len(p_areas)

        # 8. Combined Cellular Morphology Verification (isolated blood cells & confluent RBC monolayer)
        cell_mask = (giemsa_purple | eosin_rbc).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_mask = cv2.morphologyEx(cell_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cell_count = 0
        total_cell_area = 0.0
        max_contour_area = 0.0
        min_cell_area = max(10, int(50 * (total_pixels / (4160 * 3120))))

        for c in contours:
            area = cv2.contourArea(c)
            if area > max_contour_area:
                max_contour_area = area
            if min_cell_area <= area <= (total_pixels * 0.40):
                peri = cv2.arcLength(c, True)
                if peri > 0:
                    circularity = 4 * np.pi * area / (peri * peri)
                    if circularity >= 0.12:
                        cell_count += 1
                        total_cell_area += area

        cell_count = max(cell_count, p_count)
        cell_coverage = max(float(total_cell_area / total_pixels), float(np.sum(giemsa_purple) / total_pixels))
        max_contour_ratio = float(max_contour_area / total_pixels)
        stain_score = (purple_ratio * 4.0) + (pink_ratio * 2.0) + (bright_bg_ratio * 0.5)

        return (stain_score, purple_ratio, pink_ratio, bright_bg_ratio, laplacian_var,
                cell_count, cell_coverage, color_diff, s_mean, v_mean, green_ratio, max_contour_ratio,
                max_purple_contour_ratio, p_count)

    def validate(self, pil_image, cv2_image=None):
        """
        Validate whether uploaded image is a genuine blood-smear microscopy image.
        Rejects camera photographs, natural landscapes, portraits/selfies, documents/text,
        memes/quotes, and invalid non-blood-smear medical images (X-Rays, CTs, MRIs) before prediction.
        """
        try:
            w, h = pil_image.size
            total_pixels = float(w * h)

            # Check 1: Resolution & Aspect Ratio (evaluated on actual native dimensions)
            if w < 64 or h < 64:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image - No Classification",
                    "reason": "Image resolution is too small to be a diagnostic blood-smear microscopy slide.",
                    "prediction": "Invalid Image - No Classification"
                }

            aspect_ratio = max(w, h) / max(1, min(w, h))
            if aspect_ratio > 3.8:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image - No Classification",
                    "reason": "Abnormal aspect ratio. Microscopic slide images maintain balanced field proportions.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Create or downsample cv2_eval to avoid massive 99MB int64 memory allocations
            if cv2_image is None:
                cv2_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            if max(h, w) > 1024:
                scale = 1024.0 / max(h, w)
                cv2_eval = cv2.resize(cv2_image, (max(64, int(w * scale)), max(64, int(h * scale))), interpolation=cv2.INTER_AREA)
            else:
                cv2_eval = cv2_image

            eh, ew = cv2_eval.shape[:2]
            eval_pixels = float(eh * ew)

            # Check 2: Color stain & morphology analysis
            (stain_score, purple_ratio, pink_ratio, bright_bg, lap_var,
             cell_count, cell_cov, color_diff, s_mean, v_mean, green_ratio, max_contour_ratio,
             max_purple_contour_ratio, p_count) = self.analyze_color_stain_features(cv2_eval)

            # Check 3: Monochrome / Non-stained Medical Images (X-Ray, CT, MRI, Ultrasound)
            if color_diff < 12.0 or s_mean < 12.0:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image - No Classification",
                    "reason": "Monochrome or non-stained medical image (X-Ray, CT, MRI, Ultrasound) detected. Only Wright-Giemsa stained blood smear microscopy slides are accepted.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 4: Document / Text Photograph / Typography / Meme Detection
            gray_eval = cv2.cvtColor(cv2_eval, cv2.COLOR_BGR2GRAY)
            black_ratio = float(np.sum(gray_eval < 45) / eval_pixels)
            white_ratio = float(np.sum(gray_eval > 220) / eval_pixels)
            if (black_ratio > 0.03 and white_ratio > 0.55) or (black_ratio > 0.08 and white_ratio > 0.40):
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image - No Classification",
                    "reason": "Document or text photograph detected. Please upload a genuine peripheral blood-smear microscopic slide.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 4b: Digital Display Screen, Laptop/Monitor, and QR Code Grid Detection
            resized_512 = cv2.resize(cv2_eval, (512, 512))
            r_gray = cv2.cvtColor(resized_512, cv2.COLOR_BGR2GRAY)
            r_edges = cv2.Canny(r_gray, 60, 180)
            hough_lines = cv2.HoughLinesP(r_edges, 1, np.pi / 180, threshold=70, minLineLength=50, maxLineGap=5)
            ortho_count = 0
            if hough_lines is not None:
                for l in hough_lines:
                    pts = l.flatten()
                    if len(pts) == 4:
                        x1, y1, x2, y2 = pts
                        if abs(y2 - y1) <= 2 or abs(x2 - x1) <= 2:
                            ortho_count += 1
            if ortho_count >= 8:
                return {
                    "is_valid": False,
                    "confidence": 0.99,
                    "status": "Invalid Image - No Classification",
                    "reason": f"Digital display screen or structured man-made scene detected ({ortho_count} orthogonal grid edges). Blood-smear cytology exhibits organic curved cell morphology.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 5: Natural Scene / Outdoor Scenery Coloration (Foliage Green)
            if green_ratio > 0.035:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image - No Classification",
                    "reason": "Natural scene or landscape photograph detected (foliage/plant green coloration present).",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 6: Brightfield Illumination & Darkness Check
            dark_ratio = float(np.sum(cv2.cvtColor(cv2_eval, cv2.COLOR_BGR2HSV)[:, :, 2] < 50) / eval_pixels)
            if v_mean < 65.0 or dark_ratio > 0.60:
                return {
                    "is_valid": False,
                    "confidence": 0.97,
                    "status": "Invalid Image - No Classification",
                    "reason": "Dark or poorly-illuminated non-microscopic scene detected. Blood smear microscopy requires brightfield illumination.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 6b: Central Field Illumination (Brightfield microscope condenser focus vs dark digital screens)
            c_box = gray_eval[int(eh * 0.20):int(eh * 0.80), int(ew * 0.20):int(ew * 0.80)]
            center_dark_ratio = float(np.sum(c_box < 50) / c_box.size)
            if center_dark_ratio > 0.08 and bright_bg < 0.40:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image - No Classification",
                    "reason": "Dark non-illuminated central field detected. Blood-smear microscopy requires brightfield condenser illumination across the slide view.",
                    "prediction": "Invalid Image - No Classification"
                }

            # Check 6c: Cytological Monolayer Coherence (WBC / RBC / Brightfield Glass balance)
            if purple_ratio < 0.020 and pink_ratio < 0.050 and bright_bg < 0.40:
                return {
                    "is_valid": False,
                    "confidence": 0.98,
                    "status": "Invalid Image - No Classification",
                    "reason": "Invalid non-microscopy image: Lacks peripheral blood cytology (insufficient erythrocyte monolayer and brightfield illumination).",
                    "prediction": "Invalid Image - No Classification",
                    "stain_metrics": {
                        "purple_nucleus_ratio": round(float(purple_ratio), 4),
                        "pink_cytoplasm_ratio": round(float(pink_ratio), 4),
                        "background_luminance": round(float(bright_bg), 4)
                    }
                }

            # Check 7: Mandatory Wright-Giemsa Leukocyte Nucleus Verification
            if purple_ratio < 0.008 or p_count < 1:
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

            # Check 8: Monolithic scene rejection (Skin, walls, solid colors, tissue biopsy sheets)
            is_genuine_blood_smear = (purple_ratio >= 0.008) and (pink_ratio >= 0.05) and (p_count >= 2)

            if not is_genuine_blood_smear and (max_contour_ratio > 0.60 or cell_cov > 0.85):
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

            # Check 9: Discrete cellular morphology verification
            if cell_count < 2 and cell_cov < 0.008:
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

            # Check 10: PyTorch Deep Learning Classifier validation
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
                "status": "Invalid Image - No Classification",
                "prediction": "Invalid Image - No Classification",
                "reason": f"Error validating image structure: {str(e)}"
            }
