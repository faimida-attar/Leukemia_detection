import os
import sys
import json
import glob
from PIL import Image

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
SPLIT_JSON_PATH = os.path.join(CHECKPOINT_DIR, "dataset_split.json")
HYBRID_CKPT_PATH = os.path.join(CHECKPOINT_DIR, "leukemia_hybrid_resnet50_densenet121.pth")

sys.path.append(BASE_DIR)
from models.cnn.hybrid_classifier import HybridLeukemiaClassifier, LeukemiaHybridResNetDenseNet

CLASSES = ["ALL", "AML", "CLL", "CML", "Normal"]

def run_prediction_tests():
    print("=======================================================================", flush=True)
    print("       TESTING HYBRID RESNET50 + DENSENET121 PREDICTIONS ON TEST SET    ", flush=True)
    print("=======================================================================", flush=True)

    if not os.path.exists(HYBRID_CKPT_PATH):
        print(f"[Error] Hybrid model checkpoint not found at '{HYBRID_CKPT_PATH}'", flush=True)
        return

    classifier = HybridLeukemiaClassifier(HYBRID_CKPT_PATH)
    classifier.model.eval()

    # Load test split samples
    test_samples_by_class = {c: [] for c in CLASSES}

    if os.path.exists(SPLIT_JSON_PATH):
        with open(SPLIT_JSON_PATH, "r") as f:
            split_data = json.load(f)
        for fpath, cls_name in split_data.get("test", []):
            if os.path.exists(fpath) and cls_name in test_samples_by_class:
                test_samples_by_class[cls_name].append(fpath)

    print("\n--- SAMPLE PREDICTIONS PER CLASS (RAW PROBABILITIES & CONFIDENCE) ---", flush=True)

    correct_counts = {c: 0 for c in CLASSES}
    total_tested = 0

    for cls_name in CLASSES:
        paths = test_samples_by_class.get(cls_name, [])
        print(f"\n=======================================================")
        print(f" GROUND TRUTH CLASS: {cls_name} ({len(paths)} test images available)")
        print(f"=======================================================")

        sample_paths = paths[:5]  # Test 5 images per class
        for idx, fpath in enumerate(sample_paths):
            total_tested += 1
            fname = os.path.basename(fpath)
            try:
                pil_img = Image.open(fpath).convert("RGB")
                res = classifier.predict(pil_img, filename=fname, eval_mode=True)
                pred_cls = res["prediction"]
                conf = res["confidence"]
                probs = res["probabilities"]

                is_correct = (pred_cls == cls_name)
                if is_correct:
                    correct_counts[cls_name] += 1

                status_tag = "[CORRECT]" if is_correct else "[MISCLASSIFIED]"
                print(f"  Sample {idx+1}: {fname[:40]:40s} {status_tag}")
                print(f"    -> True Class      : {cls_name}")
                print(f"    -> Predicted Class : {pred_cls} (Confidence: {conf}%)")
                print(f"    -> Probabilities   : {probs}")
            except Exception as err:
                print(f"  Sample {idx+1}: Error processing '{fname}': {err}")

    print("\n-------------------------------------------------------", flush=True)
    print(" SUMMARY OF TEST PREDICTIONS", flush=True)
    print("-------------------------------------------------------", flush=True)
    for c in CLASSES:
        n_tested = min(5, len(test_samples_by_class.get(c, [])))
        n_corr = correct_counts[c]
        pct = (n_corr / n_tested * 100) if n_tested > 0 else 0
        print(f" Class {c:6s}: {n_corr}/{n_tested} Correct ({pct:.1f}%)", flush=True)

if __name__ == "__main__":
    run_prediction_tests()
