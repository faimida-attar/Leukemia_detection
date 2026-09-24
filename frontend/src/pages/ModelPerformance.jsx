import React, { useState } from 'react';
import { BarChart3, CheckCircle2, Upload, Sparkles, Layers, Award, RefreshCw, AlertCircle, TrendingUp, Table, Image as ImageIcon } from 'lucide-react';

export default function ModelPerformance({ analysisData, setActiveTab }) {
  // Normalize analysisData to list of uploaded items
  const resultsList = Array.isArray(analysisData)
    ? analysisData
    : (analysisData ? [analysisData] : []);

  const totalUploaded = resultsList.length;

  // Empty state when no images have been uploaded yet
  if (totalUploaded === 0) {
    return (
      <div className="py-16 max-w-3xl mx-auto px-4 text-center">
        <div className="bg-white border border-slate-200 rounded-3xl p-10 shadow-xs space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-sky-50 text-sky-600 flex items-center justify-center mx-auto border border-sky-100">
            <BarChart3 className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-extrabold text-slate-900">No Uploaded Data Available for Model Comparison</h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Model performance comparison dynamically evaluates your uploaded microscopic blood smear images. Please select and upload images on the Slide Analysis page to view comparative model metrics.
          </p>
          <button
            onClick={() => setActiveTab && setActiveTab('analysis')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-xl shadow-md transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Images on Slide Analysis Page</span>
          </button>
        </div>
      </div>
    );
  }

  // Parse ground truth label from filename or item property
  const parseGroundTruth = (item) => {
    if (item.ground_truth) return item.ground_truth;
    const fname = (item.selectedFileName || item.image_information?.filename || '').toUpperCase();
    if (fname.includes('ALL')) return 'ALL';
    if (fname.includes('AML')) return 'AML';
    if (fname.includes('CLL')) return 'CLL';
    if (fname.includes('CML')) return 'CML';
    if (fname.includes('NORMAL') || fname.includes('HEALTHY') || fname.startsWith('H_') || fname.startsWith('H-')) return 'Normal';
    return null;
  };

  const validItems = resultsList.filter(item => item?.is_valid !== false);
  const labeledItems = validItems.filter(item => parseGroundTruth(item) !== null);
  const hasGroundTruth = labeledItems.length > 0;

  const [performanceData, setPerformanceData] = useState(null);

  React.useEffect(() => {
    import('../services/api').then(({ getModelPerformanceApi }) => {
      getModelPerformanceApi().then(data => setPerformanceData(data)).catch(console.error);
    });
  }, []);

  // Compute dynamic reconstruction quality metrics across uploaded images (Keep as requested)
  const avgPsnr = validItems.length > 0
    ? (validItems.reduce((acc, item) => acc + (item?.reconstruction_metrics?.psnr_db ?? item?.reconstruction_metrics?.psnr ?? 0), 0) / validItems.length).toFixed(2)
    : '0.00';

  const avgSsim = validItems.length > 0
    ? (validItems.reduce((acc, item) => acc + (item?.reconstruction_metrics?.ssim ?? 0), 0) / validItems.length).toFixed(4)
    : '0.0000';

  const avgMae = validItems.length > 0
    ? (validItems.reduce((acc, item) => acc + (item?.reconstruction_metrics?.mae ?? 0), 0) / validItems.length).toFixed(4)
    : '0.0000';

  // Use test-set evaluation metrics from backend
  const modelComparison = performanceData?.model_comparison || [
    { model: "ResNet50", accuracy: 'N/A', precision: 'N/A', recall: 'N/A', f1: 'N/A', sensitivity: 'N/A', specificity: 'N/A', auc: 'N/A' },
    { model: "DenseNet121", accuracy: 'N/A', precision: 'N/A', recall: 'N/A', f1: 'N/A', sensitivity: 'N/A', specificity: 'N/A', auc: 'N/A' },
    { model: "Hybrid ResNet50 + DenseNet121", accuracy: 'N/A', precision: 'N/A', recall: 'N/A', f1: 'N/A', sensitivity: 'N/A', specificity: 'N/A', auc: 'N/A', isBest: true }
  ];

  // Render static confusion matrix from test-set evaluation
  const renderConfusionMatrix = (modelKey, title) => {
    const labels = ["ALL", "AML", "CLL", "CML", "Normal"];
    const fallbackMatrix = [
      [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]
    ];
    
    let matrix = fallbackMatrix;
    if (performanceData?.confusion_matrices && performanceData.confusion_matrices[modelKey]) {
       matrix = performanceData.confusion_matrices[modelKey].matrix;
    }

    return (
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
        <span className="font-bold text-xs text-slate-800 block border-b border-slate-200 pb-2">{title}</span>
        <div className="overflow-x-auto">
          <table className="w-full text-center text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-[10px]">
                <th className="p-1.5 text-left font-sans">True \ Pred</th>
                {labels.map(l => <th key={l} className="p-1.5">{l}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {matrix.map((row, rIdx) => (
                <tr key={rIdx}>
                  <td className="p-1.5 text-left font-bold font-sans text-slate-700">
                    {labels[rIdx]}
                  </td>
                  {row.map((cell, cIdx) => (
                    <td
                      key={cIdx}
                      className={`p-1.5 font-bold ${
                        rIdx === cIdx ? 'bg-emerald-100 text-emerald-900 rounded' : cell > 0 ? 'bg-sky-100 text-sky-900 rounded' : 'text-slate-400'
                      }`}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-10 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      
      {/* Page Header */}
      <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-xs text-center max-w-3xl mx-auto space-y-3">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-50 text-sky-700 text-xs font-semibold border border-sky-200">
          <BarChart3 className="w-4 h-4 text-sky-600" />
          <span>Dynamic Model Comparison Dashboard</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Uploaded Image Model Performance & Evaluation
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          Robust evaluation calculated strictly from the <strong className="text-slate-900 font-bold">full unseen 750-image test set</strong> for <strong className="text-slate-900 font-semibold">ResNet50</strong>, <strong className="text-slate-900 font-semibold">DenseNet121</strong>, and the <strong className="text-slate-900 font-semibold">Hybrid ResNet50 + DenseNet121 Classifier</strong>.
        </p>
        
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-slate-100 border border-slate-200 rounded-full text-xs font-mono font-bold text-slate-800">
          <span>Processed Upload Count: {totalUploaded} / 50</span>
        </div>
      </div>

      {/* SECTION 1: Model Comparison Table */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-100 pb-4 gap-2">
          <div>
            <span className="text-xs font-bold text-sky-700 uppercase tracking-wider bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
              Model Comparison
            </span>
            <h2 className="text-xl font-extrabold text-slate-900 mt-2">
              ResNet50 vs DenseNet121 vs Hybrid ResNet50 + DenseNet121
            </h2>
            <p className="text-xs text-slate-500">Evaluated on the full 750-image test set</p>
          </div>
          <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
            Evaluated on 750 Test Slides
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold">
                <th className="p-3">Model Architecture</th>
                <th className="p-3">Accuracy</th>
                <th className="p-3">Precision</th>
                <th className="p-3">Recall</th>
                <th className="p-3">F1-Score</th>
                <th className="p-3">Sensitivity</th>
                <th className="p-3">Specificity</th>
                <th className="p-3">AUC-ROC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {modelComparison.map((m, idx) => (
                <tr
                  key={idx}
                  className={`hover:bg-slate-50 transition-colors ${
                    m.isBest ? 'bg-sky-50/70 font-bold border-l-4 border-l-sky-600' : ''
                  }`}
                >
                  <td className="p-3 font-sans font-extrabold text-slate-900">{m.model}</td>
                  <td className="p-3 font-bold text-slate-900">{m.accuracy !== 'N/A' ? `${m.accuracy}%` : 'N/A'}</td>
                  <td className="p-3">{m.precision !== 'N/A' ? `${m.precision}%` : 'N/A'}</td>
                  <td className="p-3">{m.recall !== 'N/A' ? `${m.recall}%` : 'N/A'}</td>
                  <td className="p-3 font-bold text-sky-800">{m.f1 !== 'N/A' ? `${m.f1}%` : 'N/A'}</td>
                  <td className="p-3">{m.sensitivity !== 'N/A' ? `${m.sensitivity}%` : 'N/A'}</td>
                  <td className="p-3">{m.specificity !== 'N/A' ? `${m.specificity}%` : 'N/A'}</td>
                  <td className="p-3 font-bold text-emerald-700">{m.auc !== 'N/A' ? m.auc : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SECTION 2: Dynamic Confusion Matrices */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="border-b border-slate-100 pb-4">
          <span className="text-xs font-bold text-sky-700 uppercase tracking-wider bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
            Confusion Matrices
          </span>
          <h2 className="text-xl font-extrabold text-slate-900 mt-2">
            Model Prediction Confusion Matrices
          </h2>
          <p className="text-xs text-slate-500">
            True class vs predicted class distributions evaluated across full 750-image test set
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {renderConfusionMatrix("resnet50", "ResNet50 Model Matrix")}
          {renderConfusionMatrix("densenet121", "DenseNet121 Model Matrix")}
          {renderConfusionMatrix("hybrid_resnet50_densenet121", "Hybrid ResNet50 + DenseNet121 Matrix")}
        </div>
      </section>

      {/* SECTION 3: Reconstruction Quality Metrics Across Uploads */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-100 pb-4 gap-2">
          <div>
            <span className="text-xs font-bold text-sky-700 uppercase tracking-wider bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
              Reconstruction Quality
            </span>
            <h2 className="text-xl font-extrabold text-slate-900 mt-2">GAN + CBAM Quality Benchmarks for Uploads</h2>
            <p className="text-xs text-slate-500">Average PSNR, SSIM, and MAE evaluated on {totalUploaded} uploaded microscopic slides</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="bg-sky-50/80 border border-sky-200 rounded-2xl p-5 text-center space-y-1">
            <span className="text-xs font-bold text-sky-700 uppercase block">Average PSNR</span>
            <span className="text-2xl font-black text-sky-950">{avgPsnr} dB</span>
            <span className="text-[11px] text-slate-500 block">Peak Signal-to-Noise Ratio</span>
          </div>
          <div className="bg-sky-50/80 border border-sky-200 rounded-2xl p-5 text-center space-y-1">
            <span className="text-xs font-bold text-sky-700 uppercase block">Average SSIM</span>
            <span className="text-2xl font-black text-sky-950">{avgSsim}</span>
            <span className="text-[11px] text-slate-500 block">Structural Similarity Index</span>
          </div>
          <div className="bg-sky-50/80 border border-sky-200 rounded-2xl p-5 text-center space-y-1">
            <span className="text-xs font-bold text-sky-700 uppercase block">Average MAE</span>
            <span className="text-2xl font-black text-sky-950">{avgMae}</span>
            <span className="text-[11px] text-slate-500 block">Mean Absolute Error</span>
          </div>
        </div>
      </section>

    </div>
  );
}
