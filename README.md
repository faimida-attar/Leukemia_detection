# 🩺 Leukemia Detection & Analysis System (ALL/AML/CLL/CML)

An end-to-end Deep Learning and Computer Vision framework designed for automated blood smear microscopic image validation, GAN-based denoising/enhancement, multi-class Leukemia classification, Grad-CAM visual explainability, and automated medical PDF report generation.

---

## 🌟 Key Features

- **Microscopic Image Validation**: Automated pre-screening filter (ImageValidator CNN) ensuring uploaded images are valid microscopic blood cell smears.
- **GAN + CBAM Denoising & Enhancement**: Generative Adversarial Network augmented with Convolutional Block Attention Module (CBAM) to reconstruct low-quality blood smear images, remove noise, and preserve crucial cellular morphology.
- **Multi-Class Deep Learning Classification**: ResNet-50 classifier categorizing microscopic images into 5 classes:
  - **ALL**: Acute Lymphoblastic Leukemia
  - **AML**: Acute Myeloid Leukemia
  - **CLL**: Chronic Lymphocytic Leukemia
  - **CML**: Chronic Myeloid Leukemia
  - **Normal**: Healthy blood sample
- **Explainable AI (Grad-CAM)**: Visual attention heatmaps highlight salient cellular regions (such as blast cells and abnormal nuclei) driving the model's diagnostic predictions.
- **Reconstruction & Compression Metrics**: Real-time evaluation of PSNR, SSIM, and MSE across reconstructed images, along with dynamic JPEG/WebP compression tuning.
- **Automated Medical PDF Reports**: PDF generation engine (via ReportLab) producing downloadable diagnostic reports including patient metadata, classification confidence, Grad-CAM visualization, and reconstruction metrics.
- **Persistent History & Database Sync**: Integrated with MongoDB for logging diagnostic records, with automatic graceful fallback to standalone mode if MongoDB is unavailable.
- **Modern Interactive Web Dashboard**: Responsive user interface built with React 19, Vite, and Tailwind CSS v4.

---

## 🏗 System Architecture

```
[ Blood Smear Image ] 
         │
         ▼
 1. Image Validation (Validator CNN) ──── (Rejects Non-Microscopic Images)
         │ (Valid)
         ▼
 2. Image Denoising & Enhancement (GAN + CBAM Generator)
         │
         ├─────────────────────────────────┐
         ▼                                 ▼
 3. ResNet-50 Classifier          4. Reconstruction Metrics
 (ALL, AML, CLL, CML, Normal)      (PSNR, SSIM, MSE)
         │
         ▼
 5. Grad-CAM Visual Heatmap
         │
         ▼
 6. PDF Diagnostic Report & MongoDB Sync
```

---

## 🛠 Tech Stack

### **Backend**
- **Framework**: Python 3.10+, Flask 3.0, Flask-CORS
- **Deep Learning / ML**: PyTorch, Torchvision, OpenCV, PIL, Scikit-Learn, Scikit-Image, NumPy, SciPy
- **Database**: PyMongo (MongoDB)
- **PDF Generation**: ReportLab
- **Data Visualization**: Matplotlib, Seaborn

### **Frontend**
- **Core**: React 19, Vite 8, JavaScript (ES Module)
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Linter**: Oxlint

---

## 📁 Project Structure

```
leukemia_detection/
├── backend/
│   ├── app.py                      # Flask REST API server & pipeline runner
│   ├── train_models.py             # Model training script for dataset
│   ├── requirements.txt            # Python backend dependencies
│   ├── .env                        # Environment configuration
│   ├── models/
│   │   ├── cbam/                   # CBAM Attention Module implementation
│   │   ├── cnn/                    # ResNet-50 Classifier architecture
│   │   ├── gan/                    # Generator & Discriminator network architectures
│   │   ├── gradcam/                # Grad-CAM heatmap generation module
│   │   ├── validation/             # Image Validation CNN
│   │   └── checkpoints/            # Trained model weight checkpoints (.pth / .h5)
│   ├── services/
│   │   ├── compression.py          # Dynamic image compression service
│   │   ├── metrics.py              # PSNR, SSIM, MSE & classification metrics
│   │   └── report_generator.py     # PDF report generation engine
│   ├── sample_images/              # Pre-loaded sample blood smear images
│   ├── uploads/                    # Temporary uploaded images directory
│   └── results/                    # Generated output files & PDF reports
│
├── frontend/
│   ├── src/
│   │   ├── components/             # Reusable UI components (Navbar, ImageComparison, MetricCard, etc.)
│   │   ├── pages/                  # Main pages (ImageAnalysis, ModelPerformance, Results)
│   │   ├── services/               # API service integration
│   │   ├── App.jsx                 # Application routing and layout
│   │   └── main.jsx                # Vite entrypoint
│   ├── package.json                # Node.js dependencies & scripts
│   ├── vite.config.js              # Vite configuration
│   └── .env                        # Frontend environment variables
│
├── dataset/                        # Microscopic blood smear image dataset (ALL, AML, CLL, CML, Normal)
├── train_colab_keras.ipynb         # Google Colab notebook for Keras/TensorFlow training
└── train_colab_pytorch_h5.ipynb    # Google Colab notebook for PyTorch model training
```

---

## 📡 API Reference

### **System & Utility Endpoints**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check endpoint returning backend status |
| `GET` | `/api/sample-images` | List available pre-loaded sample microscopic images |
| `GET` | `/api/sample-images/<filename>` | Serve specific sample image file |

### **Analysis & Inference Endpoints**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/validate-image` | Validate whether an uploaded file is a blood cell microscopic image |
| `POST` | `/api/preprocess` | Apply color normalization / contrast stretching on cell images |
| `POST` | `/api/reconstruct` | Run GAN + CBAM enhancement and return reconstructed image + PSNR/SSIM/MSE |
| `POST` | `/api/predict` | Predict Leukemia class (ALL, AML, CLL, CML, Normal) & confidence scores |
| `POST` | `/api/gradcam` | Generate Grad-CAM attention heatmap overlay |
| `POST` | `/api/compress` | Perform dynamic JPEG/WebP compression quality analysis |
| `POST` | `/api/analyze` | Execute complete end-to-end pipeline (Validation ➔ GAN ➔ ResNet ➔ Grad-CAM ➔ DB Log) |

### **History, Performance & PDF Reports**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/history` | Retrieve past diagnostic analysis records |
| `GET` | `/api/model-performance` | Retrieve overall model metrics, evaluation statistics & confusion matrix |
| `POST` | `/api/generate-report` | Generate and download a PDF medical diagnostic report |

---

## ⚡ Quick Start Guide

### **Prerequisites**
- **Python**: `3.10+`
- **Node.js**: `18.0+`
- **MongoDB** *(Optional)*: `mongodb://localhost:27017` (App operates in standalone mode if omitted)

---

### **1. Backend Setup**

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (`backend/.env`):
   ```env
   PORT=5000
   MONGO_URI=mongodb://localhost:27017/leukemia_db
   MONGO_DB_NAME=leukemia_db
   ```

5. Train model checkpoints *(if model weights are not present in `models/checkpoints/`)*:
   ```bash
   python train_models.py
   ```

6. Launch the Flask API server:
   ```bash
   python app.py
   ```
   The backend API will start at `http://localhost:5000`.

---

### **2. Frontend Setup**

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure frontend environment variables (`frontend/.env`):
   ```env
   VITE_API_BASE_URL=http://localhost:5000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your web browser.

---

## 🎯 Model Training & Evaluation

To re-train or fine-tune models locally:
- **Local Training**: Execute `python backend/train_models.py`. This script automatically indexes images in `dataset/`, generates negative control samples for the validator, trains the GAN generator + discriminator with CBAM attention, fine-tunes ResNet-50, and saves checkpoint files to `backend/models/checkpoints/`.
- **Cloud / Colab Training**: Use `train_colab_keras.ipynb` or `train_colab_pytorch_h5.ipynb` to train models using GPU acceleration on Google Colab, then export the model weights to `backend/models/checkpoints/`.

---

## 📜 Medical Disclaimer

> [!WARNING]
> This system is designed solely for educational, research, and decision-support purposes. It is **not** intended for independent clinical diagnosis. All automated findings must be verified by a qualified pathologist or healthcare practitioner.
