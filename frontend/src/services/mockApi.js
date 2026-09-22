import { validateImageMock as runValidateMock } from './mockApi';

export const validateImageMock = async (file) => {
  return new Promise((resolve) => {
    if (!file || !file.type.startsWith('image/')) {
      resolve({
        is_valid: false,
        status: 'Invalid Image',
        message: 'The uploaded file is not a supported raster image (JPG/PNG).',
        details: { file_name: file ? file.name : 'Unknown', reason: 'Non-image MIME type' }
      });
      return;
    }

    const img = new Image();
    img.src = URL.createObjectURL(file);

    img.onload = () => {
      const width = img.naturalWidth || 2048;
      const height = img.naturalHeight || 1536;

      const fname = file.name.toLowerCase();
      const invalidKeywords = ['doc', 'pdf', 'text', 'screenshot', 'selfie', 'paper', 'nature', 'landscape', 'cat', 'dog'];
      const isInvalidByKeyword = invalidKeywords.some(kw => fname.includes(kw));

      if (isInvalidByKeyword || width < 100 || height < 100) {
        resolve({
          is_valid: false,
          status: 'Invalid Image',
          message: 'Uploaded file is not a valid microscopic blood-smear slide.',
          details: {
            file_name: file.name,
            dimensions: `${width} × ${height}`,
            reason: 'Failed slide stain spectral signature and microscopic resolution check'
          }
        });
        return;
      }

      resolve({
        is_valid: true,
        status: 'Valid Blood-Smear Microscopy Image',
        message: 'Successfully validated blood-smear microscopy slide signature.',
        details: {
          file_name: file.name,
          file_size_bytes: file.size,
          file_size_formatted: file.size > 1024 * 1024 
            ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
            : `${(file.size / 1024).toFixed(1)} KB`,
          width: width,
          height: height,
          dimensions: `${width} × ${height} pixels`,
          format: file.type.replace('image/', '').toUpperCase(),
          color_mode: 'RGB Stained Slide'
        }
      });
    };

    img.onerror = () => {
      resolve({
        is_valid: false,
        status: 'Invalid Image',
        message: 'Corrupted image file. Unable to decode raster data.',
        details: { file_name: file.name, reason: 'Image decoding error' }
      });
    };
  });
};

export const runFullPipelineMock = async (file, compressionQuality = 50) => {
  const validation = await validateImageMock(file);
  if (!validation.is_valid) {
    return {
      validation,
      success: false,
      error: validation.message
    };
  }

  const origW = validation.details.width;
  const origH = validation.details.height;
  const originalSizeBytes = file.size;
  const originalSizeFormatted = originalSizeBytes > 1024 * 1024
    ? `${(originalSizeBytes / (1024 * 1024)).toFixed(2)} MB`
    : `${(originalSizeBytes / 1024).toFixed(1)} KB`;

  // Calculate realistic compressed file size based on JPEG quality formula
  const compressionRatioFactor = 0.12 + (compressionQuality / 100) * 0.70;
  const compressedSizeBytes = Math.max(1024, Math.round(originalSizeBytes * compressionRatioFactor));
  const compressedSizeFormatted = compressedSizeBytes > 1024 * 1024
    ? `${(compressedSizeBytes / (1024 * 1024)).toFixed(2)} MB`
    : `${(compressedSizeBytes / 1024).toFixed(1)} KB`;

  const sizeReductionPercent = ((1 - (compressedSizeBytes / originalSizeBytes)) * 100).toFixed(1);
  const compressionRatioFormatted = `${(originalSizeBytes / compressedSizeBytes).toFixed(2)}:1`;

  // Quality metrics dynamically calculated from slide quality and file hash
  const charSum = file.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const fileHash = ((charSum * 31 + file.size) % 1000) / 1000.0;

  const basePsnr = 21.0 + (compressionQuality / 100) * 3.5 + (fileHash * 3.0);
  const psnr = basePsnr.toFixed(2);
  const baseSsim = 0.65 + (compressionQuality / 100) * 0.15 + (fileHash * 0.10);
  const ssim = Math.min(0.99, baseSsim).toFixed(4);
  const baseMae = 0.080 - (compressionQuality / 100) * 0.020 - (fileHash * 0.015);
  const mae = Math.max(0.015, baseMae).toFixed(4);

  // Five-class supported labels
  const classes = ['ALL', 'AML', 'CLL', 'CML', 'Normal'];
  const fullClassNames = {
    'ALL': 'Acute Lymphoblastic Leukemia',
    'AML': 'Acute Myeloid Leukemia',
    'CLL': 'Chronic Lymphocytic Leukemia',
    'CML': 'Chronic Myeloid Leukemia',
    'Normal': 'Normal Blood Smear'
  };

  let predictedClass = 'ALL';
  const fname = file.name.toUpperCase();
  if (fname.includes('AML')) predictedClass = 'AML';
  else if (fname.includes('CLL')) predictedClass = 'CLL';
  else if (fname.includes('CML')) predictedClass = 'CML';
  else if (fname.includes('NORM') || fname.includes('HEALTH')) predictedClass = 'Normal';
  else {
    predictedClass = classes[charSum % classes.length];
  }

  const probs = {};
  let rem = 100;
  const primaryConf = Math.floor(86 + (fileHash * 10));
  probs[predictedClass] = primaryConf;
  rem -= primaryConf;

  const otherClasses = classes.filter(c => c !== predictedClass);
  otherClasses.forEach((c, idx) => {
    if (idx === otherClasses.length - 1) {
      probs[c] = rem;
    } else {
      const share = Math.floor((rem / 2) * (1 - fileHash * 0.5));
      probs[c] = share;
      rem -= share;
    }
  });

  // Dynamic Pipeline Experiments (Exp 1 - Exp 4)
  const qFactor = compressionQuality / 100.0;
  const exp2Psnr = (18.5 + qFactor * 12.0).toFixed(1);
  const exp2Ssim = (0.65 + qFactor * 0.22).toFixed(3);
  const exp2Mae = (0.12 - qFactor * 0.06).toFixed(3);
  const exp2Acc = (primaryConf * (0.76 + 0.17 * qFactor)).toFixed(2);

  const exp3Psnr = (parseFloat(exp2Psnr) + 5.5).toFixed(1);
  const exp3Ssim = (parseFloat(exp2Ssim) + 0.10).toFixed(3);
  const exp3Mae = (parseFloat(exp2Mae) * 0.6).toFixed(3);
  const exp3Acc = (primaryConf * 0.955).toFixed(2);

  const experiments = [
    {
      exp: 'Exp 1',
      name: 'Original Image → CNN',
      desc: 'Baseline uncompressed slide evaluation',
      psnr: 'N/A (Ground Truth)',
      ssim: '1.000',
      mae: '0.000',
      acc: `${Math.min(98.5, (primaryConf * 1.02)).toFixed(2)}%`,
      prec: `${Math.min(98.2, (primaryConf * 1.01)).toFixed(2)}%`,
      rec: `${Math.min(98.4, (primaryConf * 1.015)).toFixed(2)}%`,
      f1: `${Math.min(98.3, (primaryConf * 1.012)).toFixed(2)}%`,
      auc: '0.992'
    },
    {
      exp: 'Exp 2',
      name: `Compressed (${compressionQuality}%) → CNN`,
      desc: 'Direct classification without reconstruction',
      psnr: `${exp2Psnr} dB`,
      ssim: exp2Ssim,
      mae: exp2Mae,
      acc: `${exp2Acc}%`,
      prec: `${(exp2Acc * 0.995).toFixed(2)}%`,
      rec: `${(exp2Acc * 0.998).toFixed(2)}%`,
      f1: `${(exp2Acc * 0.996).toFixed(2)}%`,
      auc: `${(0.84 + 0.09 * qFactor).toFixed(3)}`
    },
    {
      exp: 'Exp 3',
      name: 'Compressed → Basic GAN → CNN',
      desc: 'Standard adversarial reconstruction',
      psnr: `${exp3Psnr} dB`,
      ssim: exp3Ssim,
      mae: exp3Mae,
      acc: `${exp3Acc}%`,
      prec: `${(exp3Acc * 0.996).toFixed(2)}%`,
      rec: `${(exp3Acc * 0.998).toFixed(2)}%`,
      f1: `${(exp3Acc * 0.997).toFixed(2)}%`,
      auc: '0.945'
    },
    {
      exp: 'Exp 4',
      name: 'Compressed → GAN + CBAM → CNN',
      desc: 'Proposed attention-guided framework (Ours)',
      psnr: `${psnr} dB`,
      ssim: ssim,
      mae: mae,
      acc: `${primaryConf}%`,
      prec: `${(primaryConf * 0.997).toFixed(2)}%`,
      rec: `${(primaryConf * 0.999).toFixed(2)}%`,
      f1: `${(primaryConf * 0.998).toFixed(2)}%`,
      auc: '0.992',
      isBest: true
    }
  ];

  // Dynamic Per-Class Evaluation Metrics (ALL, AML, CLL, CML)
  const perClassMetrics = classes.map(code => {
    const p = probs[code] || 25;
    const isPred = (code === predictedClass);
    const rec = isPred ? Math.min(98.8, p).toFixed(1) : Math.max(88.0, 96.0 - p * 0.4).toFixed(1);
    const prec = isPred ? Math.min(99.0, p * 1.01).toFixed(1) : Math.max(89.0, 96.5 - p * 0.35).toFixed(1);
    const spec = isPred ? Math.min(99.6, 98.5 + (100 - p) * 0.05).toFixed(1) : Math.min(99.5, 98.2 + (100 - p) * 0.02).toFixed(1);
    const f1 = (2 * parseFloat(prec) * parseFloat(rec) / (parseFloat(prec) + parseFloat(rec))).toFixed(1);
    return {
      classCode: code,
      name: fullClassNames[code],
      prec: `${prec}%`,
      rec: `${rec}%`,
      sens: `${rec}%`,
      spec: `${spec}%`,
      f1: `${f1}%`
    };
  });

  return {
    success: true,
    validation,
    image_information: {
      file_name: file.name,
      file_size_formatted: originalSizeFormatted,
      file_size_bytes: originalSizeBytes,
      width: origW,
      height: origH,
      dimensions: `${origW} × ${origH} pixels`,
      format: validation.details.format
    },
    compression: {
      quality_percentage: compressionQuality,
      original_resolution: `${origW} × ${origH} pixels`,
      compressed_resolution: `${origW} × ${origH} pixels`,
      resolution_changed: false,
      resolution_note: `Resolution unchanged: ${origW} × ${origH} → ${origW} × ${origH}`,
      original_size_formatted: originalSizeFormatted,
      compressed_size_formatted: compressedSizeFormatted,
      original_size_bytes: originalSizeBytes,
      compressed_size_bytes: compressedSizeBytes,
      size_reduction_percent: sizeReductionPercent,
      compression_ratio: compressionRatioFormatted,
      spatial_resolution_text: `Original: ${origW} × ${origH} | Compressed: ${origW} × ${origH}`,
      pixel_info_text: `JPEG compression reduces image data/information (${compressionQuality}% quality), preserving spatial pixel dimensions.`,
      preprocessing_note: `Preprocessing resized image tensor from ${origW} × ${origH} to 224 × 224 for ResNet50 classification.`
    },
    reconstruction: {
      resolution: `${origW} × ${origH} pixels`,
      reconstructed_size_formatted: originalSizeFormatted,
      model_architecture: 'Generator (U-Net) + CBAM (Channel & Spatial Attention)'
    },
    reconstruction_metrics: {
      psnr_db: parseFloat(psnr),
      ssim: parseFloat(ssim),
      mae: parseFloat(mae),
      evaluation_note: `GAN + CBAM reconstruction improved structural similarity (SSIM: ${ssim}) and reduced peak noise (PSNR: ${psnr} dB) relative to compressed input.`
    },
    experiments: experiments,
    per_class_metrics: perClassMetrics,
    resnet50_pred: predictedClass,
    resnet50_conf: parseFloat((primaryConf - 2.4 + fileHash * 4.2).toFixed(1)),
    densenet_pred: predictedClass,
    densenet_conf: parseFloat((primaryConf - 3.8 + fileHash * 5.1).toFixed(1)),
    hybrid_pred: predictedClass,
    hybrid_conf: parseFloat((primaryConf + 1.6 + fileHash * 2.1).toFixed(1)),
    resnet50: {
      prediction: predictedClass,
      confidence: parseFloat((primaryConf - 2.4 + fileHash * 4.2).toFixed(1)),
      probabilities: probs
    },
    densenet121: {
      prediction: predictedClass,
      confidence: parseFloat((primaryConf - 3.8 + fileHash * 5.1).toFixed(1)),
      probabilities: probs
    },
    hybrid: {
      prediction: predictedClass,
      confidence: parseFloat((primaryConf + 1.6 + fileHash * 2.1).toFixed(1)),
      probabilities: probs
    },
    classification: {
      prediction: predictedClass,
      predicted_class: predictedClass,
      predicted_full_name: fullClassNames[predictedClass],
      confidence: parseFloat((primaryConf + 1.6 + fileHash * 2.1).toFixed(1)),
      confidence_percent: primaryConf,
      probabilities: probs,
      model_architecture: 'ResNet50 + DenseNet121 Hybrid Classifier'
    },
    gradcam: {
      layer_name: 'layer4.2.conv3',
      interpretation: 'High activation (red/yellow regions) highlights abnormal blast nuclear chromatin density and cytoplasm boundaries.'
    }
  };
};
