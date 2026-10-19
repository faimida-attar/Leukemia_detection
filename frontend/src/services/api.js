/**
 * API Service for Flask Backend REST Endpoints
 * Project: Next-Generation Reconstruction-Driven Deep Learning Framework for Leukemia Detection
 */

const BASE_URL = '/api';

export const validateImageApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/validate-image`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: 'Validation request failed' }));
    throw new Error(err.message || 'Validation request failed');
  }
  return response.json();
};

export const preprocessImageApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/preprocess`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Preprocessing failed');
  return response.json();
};

export const reconstructImageApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/reconstruct`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Reconstruction failed');
  return response.json();
};

export const evaluateReconstructionApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/evaluate-reconstruction`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Reconstruction evaluation failed');
  return response.json();
};

export const predictLeukemiaApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/predict`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Classification request failed');
  return response.json();
};

export const getGradCamApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/gradcam`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Grad-CAM generation failed');
  return response.json();
};

export const getModelPerformanceApi = async () => {
  const response = await fetch(`${BASE_URL}/model-performance`);
  if (!response.ok) throw new Error('Failed to fetch model performance');
  return response.json();
};

export const analyzeCompletePipelineApi = async (formData) => {
  const response = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: 'Analysis failed' }));
    throw new Error(err.message || 'Pipeline analysis failed');
  }
  return response.json();
};

export const exportExcelReportApi = async (analysisData) => {
  // Strip large base64 strings to ensure ultra-fast and lightweight payload
  const sanitizeItem = (item) => {
    if (!item) return {};
    const { images, previewUrl, ...rest } = item;
    return rest;
  };

  const payload = Array.isArray(analysisData)
    ? analysisData.map(sanitizeItem)
    : sanitizeItem(analysisData);

  const response = await fetch(`${BASE_URL}/export-excel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: 'Failed to generate Excel report' }));
    throw new Error(err.error || 'Failed to export Excel report');
  }

  return response.blob();
};

export const generatePdfReportApi = async (analysisData) => {
  // Strip large base64 strings to keep request lightweight
  const sanitizeItem = (item) => {
    if (!item) return {};
    const { images, previewUrl, ...rest } = item;
    return rest;
  };

  const payload = sanitizeItem(analysisData);

  const response = await fetch(`${BASE_URL}/generate-report`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: 'Failed to generate PDF report' }));
    throw new Error(err.error || 'Failed to generate PDF report');
  }

  return response.blob();
};
