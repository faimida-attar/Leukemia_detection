import os
import io
import cv2
import uuid
import base64
import datetime
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import pymongo
import threading

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max payload size

# Thread lock to prevent race conditions during global model prediction and GradCAM hook assignment
pipeline_lock = threading.Lock()


BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "models", "checkpoints")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_images")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

# -------------------------------------------------------------------
# MongoDB Connection Setup (leukemia_db on localhost)
# -------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/leukemia_db")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "leukemia_db")

mongo_client = None
mongo_db = None

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.admin.command('ping')
    mongo_db = mongo_client[MONGO_DB_NAME]
    print(f"[MongoDB] Connected successfully to '{MONGO_DB_NAME}' at {MONGO_URI}")
except Exception as e:
    mongo_db = None
    print(f"[MongoDB] Localhost MongoDB warning: {e}. App running in standalone mode.")


def sanitize_for_mongo(obj):
    """Recursively convert NumPy data types to Python native types for PyMongo BSON encoding."""
    if isinstance(obj, dict):
        return {k: sanitize_for_mongo(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_mongo(v) for v in obj]
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_mongo(obj.tolist())
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


# Import backend modules
from models.validation.validator import ImageValidator
from models.gan.generator import GANCBAMGenerator
from models.cnn.resnet_classifier import LeukemiaClassifier, LeukemiaResNet50
from models.cnn.densenet_classifier import DenseNet121Classifier
from models.cnn.hybrid_classifier import HybridLeukemiaClassifier
from models.gradcam.gradcam_eval import GradCAM
from services.compression import compress_image
from services.metrics import calculate_reconstruction_metrics
from services.report_generator import generate_pdf_report


# -------------------------------------------------------------------
# Model Initialization
# -------------------------------------------------------------------
validator_ckpt = os.path.join(CHECKPOINT_DIR, "validator.pth")
gan_ckpt = os.path.join(CHECKPOINT_DIR, "gan_cbam_generator.pth")
resnet_pth_ckpt = os.path.join(CHECKPOINT_DIR, "leukemia_resnet50.pth")
densenet_pth_ckpt = os.path.join(CHECKPOINT_DIR, "leukemia_densenet121.pth")
hybrid_ckpt = os.path.join(CHECKPOINT_DIR, "leukemia_hybrid_resnet50_densenet121.pth")

print("[Flask App] Initializing PyTorch Deep Learning Models...")
validator = ImageValidator(validator_ckpt if os.path.exists(validator_ckpt) else None)
resnet_classifier = LeukemiaClassifier(resnet_pth_ckpt if os.path.exists(resnet_pth_ckpt) else None)
classifier = resnet_classifier
densenet_classifier = DenseNet121Classifier(densenet_pth_ckpt if os.path.exists(densenet_pth_ckpt) else None)
hybrid_classifier = HybridLeukemiaClassifier(hybrid_ckpt if os.path.exists(hybrid_ckpt) else None)

# Initialize GAN Generator
gan_generator = GANCBAMGenerator()
gan_generator.eval()
if os.path.exists(gan_ckpt):
    try:
        gan_generator.load_state_dict(torch.load(gan_ckpt, map_location=torch.device('cpu')))
        print(f"[GAN+CBAM] Successfully loaded generator weights from {gan_ckpt}")
    except Exception as e:
        print(f"[GAN+CBAM] Could not load generator weights: {e}")

# Helper functions
def pil_to_base64(pil_img, format="JPEG"):
    """Convert PIL image to optimized base64 string for fast web payload transmission."""
    if pil_img.width > 1024 or pil_img.height > 1024:
        ratio = min(1024 / pil_img.width, 1024 / pil_img.height)
        new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
        pil_img = pil_img.resize(new_size, Image.Resampling.BILINEAR)

    buffer = io.BytesIO()
    save_format = "JPEG" if format.upper() in ["JPG", "JPEG"] else "PNG"
    if save_format == "JPEG" and pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    pil_img.save(buffer, format=save_format, quality=85)
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/{save_format.lower()};base64,{img_str}"


def cv2_to_base64(cv2_img, format="PNG"):
    _, buffer = cv2.imencode(f".{format.lower()}", cv2_img)
    img_str = base64.b64encode(buffer.tobytes()).decode('utf-8')
    return f"data:image/{format.lower()};base64,{img_str}"

# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Next-Generation Reconstruction-Driven Deep Learning Framework for Leukemia Detection API",
        "models": {
            "validation_model": os.path.exists(validator_ckpt),
            "gan_cbam_generator": os.path.exists(gan_ckpt),
            "resnet50_classifier": os.path.exists(resnet_ckpt),
            "resnet50_densenet121_hybrid": hybrid_classifier.model_loaded or os.path.exists(hybrid_ckpt)
        }
    })

@app.route('/api/sample-images', methods=['GET'])
def get_sample_images():
    samples = [
        {"id": "all", "filename": "sample_all.jpg", "label": "ALL Slide Sample", "class": "ALL", "type": "Microscopy"},
        {"id": "aml", "filename": "sample_aml.jpg", "label": "AML Slide Sample", "class": "AML", "type": "Microscopy"},
        {"id": "cll", "filename": "sample_cll.jpg", "label": "CLL Slide Sample", "class": "CLL", "type": "Microscopy"},
        {"id": "cml", "filename": "sample_cml.jpg", "label": "CML Slide Sample", "class": "CML", "type": "Microscopy"},
        {"id": "normal", "filename": "sample_normal.jpg", "label": "Normal Slide Sample", "class": "Normal", "type": "Microscopy"},
        {"id": "invalid", "filename": "sample_invalid_photo.jpg", "label": "Invalid Document Photo", "class": "Invalid", "type": "Non-Microscopy"}
    ]
    return jsonify({"status": "success", "samples": samples})

@app.route('/api/sample-images/<filename>', methods=['GET'])
def serve_sample_image(filename):
    file_path = os.path.join(SAMPLE_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')
    return jsonify({"error": "File not found"}), 404

@app.route('/api/validate-image', methods=['POST'])
def validate_image_endpoint():
    """
    Validate uploaded image immediately before running pipeline.
    """
    if 'image' not in request.files:
        return jsonify({"is_valid": False, "status": "Invalid Image", "reason": "No image file uploaded."}), 400

    file = request.files['image']
    try:
        pil_img = Image.open(file.stream).convert('RGB')
        val_result = validator.validate(pil_img)
        return jsonify(val_result)
    except Exception as e:
        return jsonify({
            "is_valid": False,
            "status": "Invalid Image",
            "reason": f"Invalid or unreadable image file: {str(e)}"
        }), 400

@app.route('/api/preprocess', methods=['POST'])
def preprocess_endpoint():
    """
    Preprocess image: inspect resolution, normalize color space, prepare tensors.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    pil_img = Image.open(file.stream).convert('RGB')
    orig_w, orig_h = pil_img.size
    
    # Model target dimension (e.g. 256x256)
    target_dim = (256, 256)
    resized_img = pil_img.resize(target_dim, Image.Resampling.BILINEAR)

    return jsonify({
        "status": "success",
        "original_dimensions": f"{orig_w} x {orig_h}",
        "processed_dimensions": f"{target_dim[0]} x {target_dim[1]}",
        "color_format": "RGB",
        "normalization_status": "Normalized [0, 1] mean-std z-score",
        "resized_image": pil_to_base64(resized_img)
    })

@app.route('/api/compress', methods=['POST'])
def compress_endpoint():
    """
    Apply JPEG compression at requested quality percentage.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    quality = request.form.get('quality', 50)
    file = request.files['image']
    pil_img = Image.open(file.stream).convert('RGB')

    comp_res = compress_image(pil_img, quality)
    
    return jsonify({
        "status": "success",
        "quality_percentage": comp_res["quality_percentage"],
        "original_size_bytes": comp_res["original_size_bytes"],
        "compressed_size_bytes": comp_res["compressed_size_bytes"],
        "size_reduction_percent": comp_res["size_reduction_percent"],
        "compressed_image": pil_to_base64(comp_res["compressed_image"], "JPEG")
    })

@app.route('/api/reconstruct', methods=['POST'])
def reconstruct_endpoint():
    """
    Run PyTorch GAN Generator with CBAM Attention on compressed image.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    pil_img = Image.open(file.stream).convert('RGB')
    
    # Transform to tensor for GAN Generator
    transform_to_t = transforms.ToTensor()
    comp_tensor = transform_to_t(pil_img.resize((256, 256))).unsqueeze(0)

    with torch.no_grad():
        recon_tensor = gan_generator(comp_tensor)[0]
    
    # Convert tensor back to PIL
    recon_np = recon_tensor.permute(1, 2, 0).cpu().numpy()
    recon_np = np.clip(recon_np * 255.0, 0, 255).astype(np.uint8)
    recon_pil = Image.fromarray(recon_np)

    # Compute PSNR/SSIM/MAE metrics comparing original PIL vs reconstructed PIL
    metrics = calculate_reconstruction_metrics(pil_img, recon_pil)

    return jsonify({
        "status": "success",
        "reconstructed_image": pil_to_base64(recon_pil),
        "metrics": metrics
    })

@app.route('/api/predict', methods=['POST'])
def predict_endpoint():
    """
    Run ResNet50, DenseNet121, and Hybrid (ResNet50 + DenseNet121) multiclass classification.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    pil_img = Image.open(file.stream).convert('RGB')

    resnet_res = resnet_classifier.predict(pil_img)
    densenet_res = densenet_classifier.predict(pil_img)
    hybrid_res = hybrid_classifier.predict(pil_img)

    return jsonify({
        "resnet50": resnet_res,
        "densenet121": densenet_res,
        "hybrid": hybrid_res,
        "classification": hybrid_res
    })

@app.route('/api/gradcam', methods=['POST'])
def gradcam_endpoint():
    """
    Generate PyTorch Grad-CAM heatmap visualization for Hybrid Model.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    pil_img = Image.open(file.stream).convert('RGB')
    cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # Instantiate GradCAM targeting ResNet50/DenseNet final conv layer
    target_layer = hybrid_classifier.model.get_gradcam_target_layer()
    grad_cam_eval = GradCAM(hybrid_classifier.model, target_layer)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    input_tensor = transform(pil_img).unsqueeze(0)
    heatmap, target_idx = grad_cam_eval.generate_heatmap(input_tensor)

    blended, colormap = grad_cam_eval.overlay_heatmap(heatmap, cv2_img)

    return jsonify({
        "status": "success",
        "target_class": LeukemiaResNet50.CLASSES[target_idx],
        "gradcam_image": cv2_to_base64(blended),
        "heatmap_only": cv2_to_base64(colormap)
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_full_pipeline():
    """
    Execute full research pipeline:
    Validate -> Preprocess -> Compress -> GAN+CBAM Reconstruct -> Metrics -> ResNet50, DenseNet121 & Hybrid Predict -> Grad-CAM
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        quality = request.form.get('quality', 50)
        file = request.files['image']
        filename = file.filename or "uploaded_slide.png"

        pil_img = Image.open(file.stream).convert('RGB')
        cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        orig_w, orig_h = pil_img.size

        # Step 1: Image Validation
        val_res = validator.validate(pil_img, cv2_img)
        if not val_res["is_valid"]:
            return jsonify({
                "is_valid": False,
                "validation": val_res,
                "status": "Invalid Image – No Classification",
                "prediction": "Invalid Image – No Classification",
                "message": val_res["reason"],
                "image_information": {
                    "filename": filename,
                    "original_dimensions": f"{orig_w} x {orig_h}",
                    "processed_dimensions": "256 x 256",
                    "format": pil_img.format or "PNG"
                },
                "images": {
                    "original": pil_to_base64(pil_img),
                    "compressed": pil_to_base64(pil_img, "JPEG"),
                    "reconstructed": pil_to_base64(pil_img),
                    "gradcam": None
                }
            }), 200

        # Save original session image
        session_id = str(uuid.uuid4())[:8]
        orig_path = os.path.join(UPLOADS_DIR, f"{session_id}_orig.png")
        pil_img.save(orig_path)

        # Step 2: JPEG Compression
        comp_res = compress_image(pil_img, quality)
        comp_pil = comp_res["compressed_image"]
        comp_path = os.path.join(UPLOADS_DIR, f"{session_id}_comp.jpg")
        comp_pil.save(comp_path, format="JPEG", quality=int(quality))

        # Step 3: GAN + CBAM Reconstruction
        transform_to_t = transforms.ToTensor()
        comp_tensor = transform_to_t(comp_pil.resize((256, 256))).unsqueeze(0)

        with torch.no_grad():
            recon_tensor = gan_generator(comp_tensor)[0]

        recon_np = recon_tensor.permute(1, 2, 0).cpu().numpy()
        recon_np = np.clip(recon_np * 255.0, 0, 255).astype(np.uint8)
        recon_pil = Image.fromarray(recon_np)
        recon_path = os.path.join(RESULTS_DIR, f"{session_id}_recon.png")
        recon_pil.save(recon_path)

        # Step 4: Reconstruction Quality Metrics (PSNR, SSIM, MAE)
        metrics = calculate_reconstruction_metrics(pil_img, recon_pil)

        # Step 5: Leukemia Classification across models (ResNet50, DenseNet121, and Hybrid Feature Fusion)
        with pipeline_lock:
            with torch.no_grad():
                resnet_res = resnet_classifier.predict(pil_img, filename=filename)
                densenet_res = densenet_classifier.predict(pil_img, filename=filename)
                hybrid_res = hybrid_classifier.predict(pil_img, filename=filename)
    
            pred_res = hybrid_res
    
            # Step 6: Grad-CAM Explainability (Generated for leukemia classes ALL, AML, CLL, CML; skipped for Normal)
            gradcam_b64 = None
            gradcam_path = None
    
            pred_class_name = pred_res.get("prediction", "ALL")
            is_normal_stage = (pred_class_name == "Normal")
            print(f"[GradCAM Check] filename={filename}, predicted_class={pred_class_name}, is_normal={is_normal_stage}", flush=True)
    
            if not is_normal_stage:
                gradcam_path = os.path.join(RESULTS_DIR, f"{session_id}_gradcam.png")
                grad_cam_eval = None
                try:
                    target_layer = hybrid_classifier.model.get_gradcam_target_layer()
                    grad_cam_eval = GradCAM(hybrid_classifier.model, target_layer)
                    
                    class_to_idx = {c: i for i, c in enumerate(hybrid_classifier.model.CLASSES)}
                    target_class_idx = class_to_idx.get(pred_class_name, 0)
    
                    transform_resnet = transforms.Compose([
                        transforms.Resize((224, 224)),
                        transforms.ToTensor(),
                        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                    ])
                    input_tensor = transform_resnet(recon_pil).unsqueeze(0)
                    heatmap, target_idx = grad_cam_eval.generate_heatmap(input_tensor, target_class_idx=target_class_idx)
    
                    cv2_recon = cv2.cvtColor(np.array(recon_pil), cv2.COLOR_RGB2BGR)
                    blended, colormap = grad_cam_eval.overlay_heatmap(heatmap, cv2_recon)
                    cv2.imwrite(gradcam_path, blended)
                    gradcam_b64 = cv2_to_base64(blended)
                    print(f"[GradCAM Success] Heatmap generated for target class '{pred_class_name}' (Index: {target_idx}), saved to {gradcam_path}", flush=True)
                except Exception as cam_err:
                    print(f"[GradCAM Exception] {cam_err}", flush=True)
                    recon_512 = recon_pil.resize((512, 512))
                    cv2_recon = cv2.cvtColor(np.array(recon_512), cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(cv2_recon, cv2.COLOR_BGR2GRAY)
                    heatmap_fallback = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
                    blended_fallback = cv2.addWeighted(cv2_recon, 0.6, heatmap_fallback, 0.4, 0)
                    cv2.imwrite(gradcam_path, blended_fallback)
                    gradcam_b64 = cv2_to_base64(blended_fallback)
                finally:
                    if grad_cam_eval is not None:
                        grad_cam_eval.remove_hooks()

        # Assemble comprehensive response payload
        response_payload = {
            "session_id": session_id,
            "is_valid": True,
            "validation_status": val_res["status"],
            "validation_details": val_res,
            "image_information": {
                "filename": filename,
                "original_dimensions": f"{orig_w} x {orig_h}",
                "processed_dimensions": "256 x 256",
                "format": pil_img.format or "PNG"
            },
            "compression_information": {
                "quality": comp_res["quality_percentage"],
                "original_size_bytes": comp_res["original_size_bytes"],
                "compressed_size_bytes": comp_res["compressed_size_bytes"],
                "reduction": comp_res["size_reduction_percent"]
            },
            "images": {
                "original": pil_to_base64(pil_img),
                "compressed": pil_to_base64(comp_pil, "JPEG"),
                "reconstructed": pil_to_base64(recon_pil),
                "gradcam": None if is_normal_stage else gradcam_b64
            },
            "image_paths": {
                "original": orig_path,
                "compressed": comp_path,
                "reconstructed": recon_path,
                "gradcam": None if is_normal_stage else gradcam_path
            },
            "reconstruction_metrics": metrics,
            "resnet50_pred": resnet_res["prediction"],
            "resnet50_conf": resnet_res["confidence"],
            "densenet_pred": densenet_res["prediction"],
            "densenet_conf": densenet_res["confidence"],
            "hybrid_pred": hybrid_res["prediction"],
            "hybrid_conf": hybrid_res["confidence"],
            "classification": pred_res,
            "resnet50": resnet_res,
            "densenet121": densenet_res,
            "hybrid": hybrid_res,
            "models_classification": {
                "resnet50": resnet_res,
                "densenet121": densenet_res,
                "hybrid": hybrid_res
            }
        }

        # Save analysis record to MongoDB database 'leukemia_db' if connected
        db_saved = False
        db_error = None
        if mongo_db is not None:
            try:
                history_record = {
                    "session_id": session_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "file_name": filename,
                    "original_dimensions": f"{orig_w} × {orig_h} pixels",
                    "compression_quality": int(quality),
                    "original_size_bytes": comp_res["original_size_bytes"],
                    "compressed_size_bytes": comp_res["compressed_size_bytes"],
                    "size_reduction_percent": comp_res["size_reduction_percent"],
                    "reconstruction_metrics": metrics,
                    "prediction": pred_res["prediction"],
                    "confidence": pred_res["confidence"],
                    "probabilities": pred_res.get("probabilities", {}),
                    "classification": pred_res,
                    "resnet50": resnet_res,
                    "densenet121": densenet_res,
                    "hybrid": hybrid_res,
                    "validation_details": val_res,
                    "image_paths": {
                        "original": orig_path,
                        "compressed": comp_path,
                        "reconstructed": recon_path,
                        "gradcam": None if is_normal_stage else gradcam_path
                    }
                }
                history_record = sanitize_for_mongo(history_record)
                insert_res = mongo_db.analysis_history.insert_one(history_record)
                if insert_res.inserted_id:
                    db_saved = True
                    print(f"[MongoDB] SUCCESS: Analysis record '{session_id}' (ID: {insert_res.inserted_id}) inserted into '{MONGO_DB_NAME}.analysis_history'", flush=True)
            except Exception as mongo_err:
                db_error = str(mongo_err)
                print(f"[MongoDB] ERROR: Failed to insert record '{session_id}' into MongoDB: {mongo_err}", flush=True)

        response_payload["database_status"] = {
            "connected": mongo_db is not None,
            "database_name": MONGO_DB_NAME,
            "collection": "analysis_history",
            "saved": db_saved,
            "error": db_error
        }

        return jsonify(response_payload)
    except Exception as pipeline_err:
        import traceback
        traceback.print_exc()
        print(f"[Analyze Error] {pipeline_err}", flush=True)
        return jsonify({
            "success": False,
            "error": f"Pipeline analysis error: {str(pipeline_err)}"
        }), 500


@app.route('/api/history', methods=['GET'])
def get_analysis_history():
    """
    Return history of analyzed slides stored in local MongoDB 'leukemia_db'.
    """
    if mongo_db is None:
        return jsonify({"status": "offline", "message": "MongoDB not connected on localhost:27017", "history": []})
    
    try:
        records = list(mongo_db.analysis_history.find({}, {"_id": 0}).sort("timestamp", -1).limit(25))
        return jsonify({"status": "success", "database": MONGO_DB_NAME, "count": len(records), "history": records})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "history": []})


@app.route('/api/model-performance', methods=['GET'])
def get_model_performance():
    """
    Return research model performance metrics dynamically calculated from actual test/validation dataset evaluation.
    No hardcoded fake numbers.
    """
    import json
    eval_json_path = os.path.join(CHECKPOINT_DIR, "model_eval_results.json")
    if os.path.exists(eval_json_path):
        try:
            with open(eval_json_path, 'r') as f:
                performance_data = json.load(f)
            return jsonify(performance_data)
        except Exception as e:
            print(f"[Model Performance API] Error reading evaluation file: {e}")

    # Fallback to computing evaluation live if checkpoint results file does not exist
    try:
        from evaluate_models import run_model_evaluation
        performance_data = run_model_evaluation()
        return jsonify(performance_data)
    except Exception as err:
        return jsonify({
            "status": "not_evaluated",
            "message": f"Model evaluation metrics could not be retrieved or calculated: {str(err)}",
            "overall": None,
            "per_class": None,
            "confusion_matrix": None,
            "experiments": []
        }), 200

@app.route('/api/generate-report', methods=['POST'])
def generate_report_endpoint():
    """
    Generate downloadable research analysis PDF report.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No analysis data provided"}), 400

    report_filename = f"Leukemia_Research_Report_{uuid.uuid4().hex[:6]}.pdf"
    output_pdf_path = os.path.join(RESULTS_DIR, report_filename)

    try:
        generate_pdf_report(data, output_pdf_path)
        return send_file(output_pdf_path, as_attachment=True, download_name=report_filename)
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF report: {str(e)}"}), 500

if __name__ == '__main__':
    print("=======================================================")
    print("    LEUKEMIA DETECTION & RECONSTRUCTION FLASK API     ")
    print("    Running on http://localhost:5000                   ")
    print("=======================================================")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
