import numpy as np
from skimage.metrics import peak_signal_noise_ratio as compute_psnr
from skimage.metrics import structural_similarity as compute_ssim
from PIL import Image

def calculate_reconstruction_metrics(original_pil, reconstructed_pil):
    """
    Calculate image quality & reconstruction similarity metrics dynamically for each uploaded image:
    - PSNR (Peak Signal-to-Noise Ratio, higher is better)
    - SSIM (Structural Similarity Index, [0, 1], higher is better)
    - MAE (Mean Absolute Error, normalized [0, 1], lower is better)
    """
    eval_dim = (512, 512)
    orig_eval = original_pil.resize(eval_dim, Image.Resampling.BILINEAR)
    recon_eval = reconstructed_pil.resize(eval_dim, Image.Resampling.BILINEAR)

    orig_arr = np.array(orig_eval.convert('RGB'), dtype=np.float32)
    recon_arr = np.array(recon_eval.convert('RGB'), dtype=np.float32)

    # MAE computation (normalized [0, 1] scale)
    mae_val = float(np.mean(np.abs(orig_arr / 255.0 - recon_arr / 255.0)))

    # Convert to uint8 for PSNR and SSIM
    orig_u8 = np.uint8(np.clip(orig_arr, 0, 255))
    recon_u8 = np.uint8(np.clip(recon_arr, 0, 255))

    # MSE computation for pure mathematical fallback
    mse_val = float(np.mean((orig_arr - recon_arr) ** 2))

    # PSNR computation
    if mse_val == 0:
        psnr_val = 100.0
    else:
        try:
            psnr_val = float(compute_psnr(orig_u8, recon_u8, data_range=255))
            if np.isinf(psnr_val) or np.isnan(psnr_val):
                psnr_val = float(10 * np.log10((255.0 ** 2) / mse_val))
        except Exception:
            psnr_val = float(10 * np.log10((255.0 ** 2) / mse_val))

    # SSIM computation
    try:
        ssim_val = float(compute_ssim(orig_u8, recon_u8, channel_axis=2, data_range=255))
    except Exception:
        try:
            ssim_val = float(compute_ssim(orig_u8, recon_u8, multichannel=True, data_range=255))
        except Exception:
            # Fallback to single channel average if multichannel fails
            ssim_vals = [float(compute_ssim(orig_u8[:, :, c], recon_u8[:, :, c], data_range=255)) for c in range(3)]
            ssim_val = float(np.mean(ssim_vals))

    return {
        "psnr": round(psnr_val, 2),
        "psnr_db": round(psnr_val, 2),
        "ssim": round(ssim_val, 4),
        "mae": round(mae_val, 4)
    }


def compute_roc_auc_ovr(y_true_binary, y_scores):
    """
    Compute One-vs-Rest AUC-ROC score from ground truth binary indicators and predicted probabilities.
    Uses trapezoidal integration over sorted threshold points.
    """
    y_true_binary = np.array(y_true_binary, dtype=np.int32)
    y_scores = np.array(y_scores, dtype=np.float64)

    # If all positive or all negative, AUC is not strictly defined; return 1.0 or 0.5
    pos_count = np.sum(y_true_binary == 1)
    neg_count = np.sum(y_true_binary == 0)
    if pos_count == 0 or neg_count == 0:
        return 0.5

    # Sort descending by score
    desc_indices = np.argsort(-y_scores)
    y_true_sorted = y_true_binary[desc_indices]
    y_scores_sorted = y_scores[desc_indices]

    # Calculate True Positive Rate and False Positive Rate points
    tps = np.cumsum(y_true_sorted)
    fps = np.cumsum(1 - y_true_sorted)

    tpr = tps / pos_count
    fpr = fps / neg_count

    # Add (0,0) baseline
    tpr = np.concatenate(([0.0], tpr))
    fpr = np.concatenate(([0.0], fpr))

    # Calculate trapezoidal area under curve
    auc = np.trapz(tpr, fpr)
    return float(np.clip(auc, 0.0, 1.0))


def compute_multiclass_metrics_from_eval(y_true, y_pred, y_probs, class_names, average_method="macro"):
    """
    Calculate scientific evaluation metrics from ground-truth labels and model predictions.

    Args:
        y_true (list/array): Ground truth class indices or class string names
        y_pred (list/array): Predicted class indices or class string names
        y_probs (array-like): Matrix of predicted class probabilities shape (N, num_classes)
        class_names (list): List of class string names e.g. ["ALL", "AML", "CLL", "CML", "Normal"]
        average_method (str): Averaging method for multi-class metrics ("macro" or "weighted")

    Returns:
        dict: Scientific overall and per-class performance metrics
    """
    num_classes = len(class_names)
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}

    # Convert true and predicted to integer indices
    y_true_idx = np.array([class_to_idx[y] if isinstance(y, str) else int(y) for y in y_true])
    y_pred_idx = np.array([class_to_idx[y] if isinstance(y, str) else int(y) for y in y_pred])
    y_probs = np.array(y_probs, dtype=np.float64)

    total_samples = len(y_true_idx)
    if total_samples == 0:
        return {"status": "not_evaluated", "reason": "No evaluation samples available."}

    # 1. Overall Accuracy
    correct = np.sum(y_true_idx == y_pred_idx)
    accuracy = float((correct / total_samples) * 100.0)

    # 2. Confusion Matrix (shape: num_classes x num_classes)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true_idx, y_pred_idx):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1

    # 3. Per-Class One-vs-Rest Calculations
    per_class_results = {}
    precisions, recalls, f1s, sensitivities, specificities, aucs, class_counts = [], [], [], [], [], [], []

    for i, cls_name in enumerate(class_names):
        # TP, FP, FN, TN for class i
        tp = int(cm[i, i])
        fp = int(np.sum(cm[:, i]) - tp)
        fn = int(np.sum(cm[i, :]) - tp)
        tn = int(np.sum(cm) - (tp + fp + fn))
        count = int(np.sum(cm[i, :]))

        # Sensitivity (Recall) = TP / (TP + FN)
        sens = float(tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
        # Specificity = TN / (TN + FP)
        spec = float(tn / (tn + fp)) * 100.0 if (tn + fp) > 0 else 0.0
        # Precision = TP / (TP + FP)
        prec = float(tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
        # F1-Score = 2 * (P * R) / (P + R)
        f1 = float((2 * prec * sens) / (prec + sens)) if (prec + sens) > 0 else 0.0

        # One-vs-Rest AUC-ROC using probability scores
        y_true_binary = (y_true_idx == i).astype(int)
        y_scores_cls = y_probs[:, i] if y_probs.ndim == 2 and y_probs.shape[1] > i else np.zeros(total_samples)
        auc = compute_roc_auc_ovr(y_true_binary, y_scores_cls)

        per_class_results[cls_name] = {
            "precision": round(prec, 2),
            "recall": round(sens, 2),
            "f1_score": round(f1, 2),
            "sensitivity": round(sens, 2),
            "specificity": round(spec, 2),
            "auc": round(auc, 3),
            "sample_count": count
        }

        precisions.append(prec)
        recalls.append(sens)
        f1s.append(f1)
        sensitivities.append(sens)
        specificities.append(spec)
        aucs.append(auc)
        class_counts.append(count)

    # 4. Overall Aggregate Metrics (Macro or Weighted)
    weights = np.array(class_counts, dtype=np.float64) / total_samples if np.sum(class_counts) > 0 else np.ones(num_classes) / num_classes

    if average_method.lower() == "weighted":
        overall_prec = float(np.sum(np.array(precisions) * weights))
        overall_rec = float(np.sum(np.array(recalls) * weights))
        overall_f1 = float(np.sum(np.array(f1s) * weights))
        overall_sens = float(np.sum(np.array(sensitivities) * weights))
        overall_spec = float(np.sum(np.array(specificities) * weights))
        overall_auc = float(np.sum(np.array(aucs) * weights))
    else:  # Default Macro
        overall_prec = float(np.mean(precisions))
        overall_rec = float(np.mean(recalls))
        overall_f1 = float(np.mean(f1s))
        overall_sens = float(np.mean(sensitivities))
        overall_spec = float(np.mean(specificities))
        overall_auc = float(np.mean(aucs))

    return {
        "status": "evaluated",
        "averaging_method": average_method,
        "total_test_samples": total_samples,
        "overall": {
            "accuracy": round(accuracy, 2),
            "precision": round(overall_prec, 2),
            "recall": round(overall_rec, 2),
            "f1_score": round(overall_f1, 2),
            "sensitivity": round(overall_sens, 2),
            "specificity": round(overall_spec, 2),
            "auc_roc": round(overall_auc, 3)
        },
        "per_class": per_class_results,
        "confusion_matrix": {
            "labels": class_names,
            "matrix": cm.tolist()
        }
    }
