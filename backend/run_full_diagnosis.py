import os
import sys
import glob
import json
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")

sys.path.append(BASE_DIR)
from models.cnn.hybrid_classifier import LeukemiaHybridResNetDenseNet, HybridLeukemiaClassifier
from models.cnn.resnet_classifier import LeukemiaResNet50, LeukemiaClassifier
from models.cnn.densenet_classifier import LeukemiaDenseNet121, DenseNet121Classifier

def diagnose():
    print("=========================================================================")
    print("         SYSTEMATIC DIAGNOSIS OF LEUKEMIA CLASSIFICATION PIPELINE        ")
    print("=========================================================================\n")

    # 1. Dataset Folder-to-Label Mapping & Image Counts
    print("--- 1 & 2. DATASET FOLDER MAPPING & IMAGE COUNTS ---")
    data_cache = os.path.join(BASE_DIR, "dataset_cache_224")
    orig_dataset = "c:/Users/FAIMIDA/OneDrive/Desktop/Lihatech/dataset/dataset"

    classes_expected = ["ALL", "AML", "CLL", "CML", "Normal"]
    counts_cache = {}
    if os.path.exists(data_cache):
        for c in classes_expected:
            cp = os.path.join(data_cache, c)
            if os.path.exists(cp):
                imgs = [f for f in os.listdir(cp) if f.lower().endswith(('.jpg','.png','.jpeg'))]
                counts_cache[c] = len(imgs)
            else:
                counts_cache[c] = 0
        print(f"Dataset Cache ('{data_cache}'): {counts_cache}")

    orig_dirs = {}
    if os.path.exists(orig_dataset):
        for item in os.listdir(orig_dataset):
            full_p = os.path.join(orig_dataset, item)
            if os.path.isdir(full_p):
                imgs = glob.glob(os.path.join(full_p, "**", "*.jpg"), recursive=True) + glob.glob(os.path.join(full_p, "**", "*.png"), recursive=True)
                orig_dirs[item] = len(imgs)
        print(f"Original Dataset Folders ('{orig_dataset}'):")
        for k, v in orig_dirs.items():
            print(f"  Folder '{k}': {v} images")

    # 3. Class Index Order Verification
    print("\n--- 3. CLASS INDEX ORDER VERIFICATION ---")
    print("LeukemiaHybridResNetDenseNet.CLASSES:", LeukemiaHybridResNetDenseNet.CLASSES)
    print("LeukemiaResNet50.CLASSES            :", LeukemiaResNet50.CLASSES)
    print("LeukemiaDenseNet121.CLASSES         :", LeukemiaDenseNet121.CLASSES)

    # 4. Checkpoint Loading Verification
    print("\n--- 4. CHECKPOINT LOADING VERIFICATION ---")
    hybrid_path = os.path.join(CHECKPOINT_DIR, "leukemia_hybrid_resnet50_densenet121.pth")
    resnet_path = os.path.join(CHECKPOINT_DIR, "leukemia_resnet50.pth")
    densenet_path = os.path.join(CHECKPOINT_DIR, "leukemia_densenet121.pth")

    print(f"Hybrid Checkpoint ('{hybrid_path}'): Exists={os.path.exists(hybrid_path)}, Size={os.path.getsize(hybrid_path) if os.path.exists(hybrid_path) else 0} bytes")
    print(f"ResNet50 Checkpoint ('{resnet_path}'): Exists={os.path.exists(resnet_path)}, Size={os.path.getsize(resnet_path) if os.path.exists(resnet_path) else 0} bytes")
    print(f"DenseNet121 Checkpoint ('{densenet_path}'): Exists={os.path.exists(densenet_path)}, Size={os.path.getsize(densenet_path) if os.path.exists(densenet_path) else 0} bytes")

    hybrid_clf = HybridLeukemiaClassifier(hybrid_path)
    resnet_clf = LeukemiaClassifier(resnet_path)
    densenet_clf = DenseNet121Classifier(densenet_path)

    print(f"Hybrid Model Loaded     : {hybrid_clf.model_loaded}")
    print(f"ResNet50 Model Loaded   : {resnet_clf.model_loaded}")
    print(f"DenseNet121 Model Loaded: {densenet_clf.model_loaded}")

    # 5. Preprocessing Pipeline Verification
    print("\n--- 5. PREPROCESSING PIPELINE VERIFICATION ---")
    print("Inference Transform:")
    print(hybrid_clf.transform)

    # 6, 7 & 8. Testing Specific Known Images (AML & CLL) across all 3 models
    print("\n--- 6, 7 & 8. DIRECT MODEL TEST ON SPECIFIC AML & CLL IMAGES ---")

    # Find specific uploaded AML and CLL images
    aml_test_files = glob.glob("c:/Users/FAIMIDA/OneDrive/Desktop/Lihatech/**/20 AML TEST*", recursive=True)
    cll_test_files = glob.glob("c:/Users/FAIMIDA/OneDrive/Desktop/Lihatech/**/cll-test*", recursive=True)

    test_targets = []
    if aml_test_files:
        test_targets.append(("AML", aml_test_files[0]))
    if cll_test_files:
        test_targets.append(("CLL", cll_test_files[0]))

    # Also add 1 sample from each class in dataset_cache_224
    for c in classes_expected:
        cp = os.path.join(data_cache, c)
        if os.path.exists(cp):
            imgs = [os.path.join(cp, f) for f in os.listdir(cp) if f.lower().endswith(('.jpg','.png'))]
            if imgs:
                test_targets.append((c, imgs[0]))

    transform = hybrid_clf.transform

    for true_cls, img_path in test_targets:
        fname = os.path.basename(img_path)
        print(f"\n=======================================================")
        print(f" TEST IMAGE: '{fname}' (Ground Truth: {true_cls})")
        print(f" Path: {img_path}")
        print(f"=======================================================")

        try:
            pil_img = Image.open(img_path).convert("RGB")
            t_img = transform(pil_img).unsqueeze(0)

            # 1. Hybrid Model Inference
            with torch.no_grad():
                h_logits = hybrid_clf.model(t_img)[0]
                h_probs = torch.softmax(h_logits, dim=0)
            
            h_probs_pct = {cls: round(float(h_probs[idx]) * 100.0, 2) for idx, cls in enumerate(classes_expected)}
            h_pred_idx = torch.argmax(h_logits).item()
            h_pred_cls = classes_expected[h_pred_idx]

            print(f" [HYBRID MODEL] ResNet50 + DenseNet121 Feature Fusion:")
            print(f"   -> Raw Logits      : {[round(float(x), 4) for x in h_logits]}")
            print(f"   -> Probabilities   : {h_probs_pct}")
            print(f"   -> Top Prediction  : {h_pred_cls} (Confidence: {h_probs_pct[h_pred_cls]}%)")

            # 2. ResNet50 Standalone Inference
            with torch.no_grad():
                r_logits = resnet_clf.model(t_img)[0]
                r_probs = torch.softmax(r_logits, dim=0)
            
            r_probs_pct = {cls: round(float(r_probs[idx]) * 100.0, 2) for idx, cls in enumerate(classes_expected)}
            r_pred_idx = torch.argmax(r_logits).item()
            r_pred_cls = classes_expected[r_pred_idx]

            print(f" [RESNET50 STANDALONE]:")
            print(f"   -> Raw Logits      : {[round(float(x), 4) for x in r_logits]}")
            print(f"   -> Probabilities   : {r_probs_pct}")
            print(f"   -> Top Prediction  : {r_pred_cls} (Confidence: {r_probs_pct[r_pred_cls]}%)")

            # 3. DenseNet121 Standalone Inference
            with torch.no_grad():
                d_logits = densenet_clf.model(t_img)[0]
                d_probs = torch.softmax(d_logits, dim=0)
            
            d_probs_pct = {cls: round(float(d_probs[idx]) * 100.0, 2) for idx, cls in enumerate(classes_expected)}
            d_pred_idx = torch.argmax(d_logits).item()
            d_pred_cls = classes_expected[d_pred_idx]

            print(f" [DENSENET121 STANDALONE]:")
            print(f"   -> Raw Logits      : {[round(float(x), 4) for x in d_logits]}")
            print(f"   -> Probabilities   : {d_probs_pct}")
            print(f"   -> Top Prediction  : {d_pred_cls} (Confidence: {d_probs_pct[d_pred_cls]}%)")

        except Exception as err:
            print(f" Error analyzing '{fname}': {err}")

    # 9. Web App Endpoint Inspection
    print("\n--- 9. WEB APP PIPELINE INPUT CHECK ---")
    import app
    with app.app.test_client() as client:
        if test_targets:
            t_cls, t_path = test_targets[0]
            with open(t_path, "rb") as f:
                img_bytes = f.read()
            res = client.post('/api/analyze', data={'image': (io.BytesIO(img_bytes), os.path.basename(t_path)), 'quality': 50}, content_type='multipart/form-data')
            res_json = res.get_json()
            print(f"API /api/analyze Test Call for '{os.path.basename(t_path)}':")
            print(f"  HTTP Status: {res.status_code}")
            print(f"  Hybrid Pred: {res_json.get('hybrid_pred')}")
            print(f"  Hybrid Conf: {res_json.get('hybrid_conf')}")
            print(f"  Probabilities: {res_json.get('hybrid', {}).get('probabilities')}")

if __name__ == "__main__":
    import io
    diagnose()
