import os
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

class LeukemiaResNet50(nn.Module):
    """
    ResNet50 Architecture for Multiclass Leukemia Classification
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

    def __init__(self, num_classes=5, pretrained=False):
        super(LeukemiaResNet50, self).__init__()
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        self.resnet = models.resnet50(weights=weights)
        
        in_features = self.resnet.fc.in_features
        self.resnet.fc = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.resnet(x)

    def get_final_conv_layer(self):
        """Returns the final convolutional layer of ResNet50 for Grad-CAM targeting"""
        return self.resnet.layer4[-1].conv3


class LeukemiaClassifier:
    """
    Classifier wrapper handling image preprocessing, Keras/PyTorch inference,
    class probability computation, and confidence scores.
    """
    def __init__(self, model_path=None):
        self.model = LeukemiaResNet50(num_classes=5)
        self.model.eval()
        self.keras_model = None
        self.is_keras = False
        self.model_loaded = False
        
        if model_path and os.path.exists(model_path):
            try:
                if model_path.endswith('.h5'):
                    # 1. Try loading as Keras / TensorFlow model first
                    loaded_keras = False
                    try:
                        import tensorflow as tf
                        self.keras_model = tf.keras.models.load_model(model_path, compile=False)
                        self.is_keras = True
                        self.model_loaded = True
                        loaded_keras = True
                        print(f"[LeukemiaClassifier] Successfully loaded Keras .h5 model from {model_path}")
                    except Exception as keras_err:
                        print(f"[LeukemiaClassifier] Keras load note: {keras_err}")

                    # 2. If not Keras, try loading PyTorch HDF5 state dict
                    if not loaded_keras:
                        try:
                            import h5py
                            with h5py.File(model_path, 'r') as f:
                                state_dict = {}
                                for k in f.keys():
                                    val = f[k][()]
                                    state_dict[k] = torch.from_numpy(val)
                                self.model.load_state_dict(state_dict)
                                self.model_loaded = True
                                print(f"[LeukemiaClassifier] Successfully loaded HDF5 PyTorch weights from {model_path}")
                        except Exception as h5_err:
                            print(f"[LeukemiaClassifier] Warning: Could not parse HDF5 file: {h5_err}")

                    # 3. Fallback to .pth in same directory if .h5 failed
                    if not self.model_loaded:
                        pth_fallback = os.path.join(os.path.dirname(model_path), "leukemia_resnet50.pth")
                        if os.path.exists(pth_fallback):
                            state_dict = torch.load(pth_fallback, map_location=torch.device('cpu'))
                            self.model.load_state_dict(state_dict)
                            self.model_loaded = True
                            print(f"[LeukemiaClassifier] Loaded fallback PyTorch model from {pth_fallback}")
                else:
                    state_dict = torch.load(model_path, map_location=torch.device('cpu'))
                    self.model.load_state_dict(state_dict)
                    self.model_loaded = True
                    print(f"[LeukemiaClassifier] Successfully loaded PyTorch model from {model_path}")
            except Exception as e:
                print(f"[LeukemiaClassifier] Warning: Could not load model from {model_path}: {e}")

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, pil_image, filename=None, eval_mode=False):
        """
        Run classification on PIL Image using the loaded deep learning model (.h5 or .pth).
        Returns top prediction (ALL, AML, CLL, CML, Normal), full probability breakdown, and confidence score.
        """
        prob_dict = {}

        if self.is_keras and self.keras_model is not None:
            import numpy as np
            img_resized = pil_image.convert("RGB").resize((224, 224))
            img_arr = np.array(img_resized, dtype=np.float32) / 255.0
            img_arr = np.expand_dims(img_arr, axis=0)

            raw_preds = self.keras_model.predict(img_arr, verbose=0)[0]
            # Convert logits/softmax to percentages
            exp_preds = np.exp(raw_preds - np.max(raw_preds))
            probs = exp_preds / np.sum(exp_preds) if np.sum(raw_preds) != 1.0 else raw_preds

            for idx, cls in enumerate(LeukemiaResNet50.CLASSES):
                prob_dict[cls] = round(float(probs[idx]) * 100.0, 1)
        else:
            tensor_img = self.transform(pil_image.convert("RGB")).unsqueeze(0)
            with torch.no_grad():
                logits = self.model(tensor_img)
                probs = torch.softmax(logits, dim=1)[0]

            for idx, cls in enumerate(LeukemiaResNet50.CLASSES):
                prob_dict[cls] = round(float(probs[idx].item()) * 100.0, 1)

        # Determine top prediction
        sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        predicted_class = sorted_probs[0][0]
        confidence = sorted_probs[0][1]

        return {
            "prediction": predicted_class,
            "full_name": LeukemiaResNet50.CLASS_LABELS[predicted_class],
            "confidence": confidence,
            "probabilities": prob_dict
        }
