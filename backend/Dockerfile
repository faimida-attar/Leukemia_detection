# ============================================================
# Dockerfile — Leukemia Detection Flask API
# For deployment on Hugging Face Spaces (Docker SDK)
# Serves both the Flask REST API and the built React frontend
# ============================================================

FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# ── System dependencies ──────────────────────────────────────
# Required by: opencv-python-headless, matplotlib, reportlab
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
# Copy requirements first — Docker caches this layer.
# If requirements.txt doesn't change, pip install is skipped on re-deploy.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────
COPY . .

# Create runtime directories (uploads, results, sample_images)
RUN mkdir -p uploads results sample_images

# ── Hugging Face Spaces REQUIRES port 7860 ───────────────────
EXPOSE 7860

# ── Startup command ──────────────────────────────────────────
# --workers 1     : Critical! Each worker loads ALL models into RAM.
#                   1 worker = ~1.5GB RAM. 2 workers = ~3GB. Keep it at 1.
# --timeout 300   : Allow 5 min for slow image analysis requests (GAN + 3 models)
# --bind 0.0.0.0  : Listen on all network interfaces so HF can reach it
CMD ["gunicorn", \
     "--bind", "0.0.0.0:7860", \
     "--workers", "1", \
     "--timeout", "300", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "app:app"]
