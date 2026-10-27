import React, { useState, useRef } from 'react';
import {
  Upload, Image as ImageIcon, CheckCircle2, XCircle, Sliders,
  Sparkles, AlertCircle, Loader2, RefreshCw, FileText, Check, Trash2, Plus,
  Activity, Clock, ShieldCheck, Cpu, Eye
} from 'lucide-react';
import ValidationBadge from '../components/ValidationBadge';

import { analyzeCompletePipelineApi, validateImageApi } from '../services/api';

export default function ImageAnalysis({ setActiveTab, setAnalysisData }) {
  const MAX_IMAGES = 50;

  const [isDragOver, setIsDragOver] = useState(false);

  // Track selected files state array & preview URLs
  const [selectedFilesList, setSelectedFilesList] = useState([]);

  // Track processed images state array dynamically
  const [processedImages, setProcessedImages] = useState([]);

  // Pipeline processing state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [pipelineElapsedSeconds, setPipelineElapsedSeconds] = useState(0);
  const [activeFileName, setActiveFileName] = useState('');

  const fileInputRef = useRef(null);

  // Batch progress & notice state
  const [processingProgress, setProcessingProgress] = useState('');
  const [invalidNotice, setInvalidNotice] = useState(null);

  // Dynamic Count Calculations
  const selectedCount = selectedFilesList.length;
  const processedCount = processedImages.length;
  const currentCount = Math.max(selectedCount, processedCount);
  const remainingSlots = Math.max(0, MAX_IMAGES - currentCount);
  const isMaxReached = currentCount >= MAX_IMAGES;

  // Step 1: File Selection Handler (No Auto-Upload)
  const handleFilesSelect = (filesList) => {
    if (!filesList || filesList.length === 0) return;

    const availableSlots = Math.max(0, MAX_IMAGES - selectedFilesList.length);

    if (availableSlots <= 0) {
      setErrorMessage('Maximum 50 images limit reached! Cannot select more than 50 images.');
      return;
    }

    const rawFiles = Array.from(filesList);
    // Accept strictly up to remaining slots (maximum 50 total)
    const filesToAdd = rawFiles.slice(0, availableSlots);
    const omittedCount = rawFiles.length - filesToAdd.length;

    // Create file objects with local preview URL and quick keyword check for non-microscopy files
    const newFileItems = filesToAdd.map((file) => {
      const fname = file.name.toLowerCase();
      const invalidKeywords = ['doc', 'pdf', 'text', 'screenshot', 'selfie', 'paper', 'nature', 'landscape', 'cat', 'dog', 'invalid'];
      const isInvalidKeyword = invalidKeywords.some(kw => fname.includes(kw));

      const formattedSize = file.size < 1024 * 1024
        ? `${(file.size / 1024).toFixed(1)} KB`
        : `${(file.size / (1024 * 1024)).toFixed(2)} MB`;

      return {
        file,
        id: Math.random().toString(36).substring(2, 9) + Date.now(),
        name: file.name,
        size: formattedSize,
        previewUrl: URL.createObjectURL(file),
        isValid: isInvalidKeyword ? false : true
      };
    });

    const updatedList = [...selectedFilesList, ...newFileItems].slice(0, MAX_IMAGES);
    setSelectedFilesList(updatedList);
    setInvalidNotice(null);

    // Asynchronously validate each file in background to ensure accurate stain/microscopy check
    newFileItems.forEach(async (item) => {
      try {
        const formData = new FormData();
        formData.append('image', item.file);
        const valRes = await validateImageApi(formData);
        const isValid = valRes?.is_valid === true && !valRes?.status?.toLowerCase().includes('invalid');
        setSelectedFilesList((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, isValid, validationReason: valRes?.reason } : f))
        );
      } catch (err) {
        // preserve current status
      }
    });

    if (omittedCount > 0) {
      setErrorMessage(`Maximum 50 images limit reached! Added first ${filesToAdd.length} images; ${omittedCount} extra images were rejected.`);
    } else {
      setErrorMessage(null);
    }
  };

  const removeFileAt = (indexToRemove) => {
    const updated = selectedFilesList.filter((_, idx) => idx !== indexToRemove);
    setSelectedFilesList(updated);
    setErrorMessage(null);
    setInvalidNotice(null);
  };

  // Step 2: Dedicated Upload & Analysis Action Handler (Fast Parallel Worker Queue)
  const runBatchAnalysis = async () => {
    if (selectedFilesList.length === 0 || isAnalyzing) return;

    // Requirement: Skip invalid images in results page, only analyze valid images & predict
    const validItemsToProcess = selectedFilesList.filter(item => item.isValid !== false);

    if (validItemsToProcess.length === 0) {
      setErrorMessage("No valid blood-smear microscopy slides found. All selected images were rejected during cytology validation. Only genuine blood smear slides can be analyzed.");
      return;
    }

    const skippedCount = selectedFilesList.length - validItemsToProcess.length;
    if (skippedCount > 0) {
      setInvalidNotice(`${skippedCount} non-microscopic slide(s) were skipped. Only valid blood-smear microscopy slides are being analyzed.`);
    }

    setIsAnalyzing(true);
    setErrorMessage(null);
    setPipelineElapsedSeconds(0);

    const timer = setInterval(() => {
      setPipelineElapsedSeconds((s) => s + 0.5);
    }, 500);

    const totalToProcess = validItemsToProcess.length;

    // Requirement: When upload button is clicked, redirect to Results page immediately and show pipeline
    const initialPlaceholders = validItemsToProcess.map((item, idx) => ({
      status: 'processing',
      previewUrl: item.previewUrl,
      selectedFileName: item.name,
      file_size_formatted: item.size,
      file_size_bytes: item.file.size,
      is_valid: true,
      origIdx: idx
    }));

    if (setAnalysisData) {
      setAnalysisData(initialPlaceholders);
    }
    setActiveTab('results');

    let completedResults = [...initialPlaceholders];
    let currentIndex = 0;
    const CONCURRENCY = 2; // Stable CPU concurrency

    const processItem = async (index) => {
      const item = validItemsToProcess[index];
      const file = item.file;
      setActiveFileName(item.name);
      setProcessingProgress(`Analyzing ${index + 1} of ${totalToProcess}: ${item.name}`);

      const formData = new FormData();
      formData.append('image', file);

      try {
        const resultData = await analyzeCompletePipelineApi(formData);
        const isItemValid = resultData?.is_valid === true && !resultData?.status?.toLowerCase().includes('invalid') && !resultData?.prediction?.toLowerCase().includes('invalid');

        if (isItemValid) {
          const itemResult = {
            ...(resultData || {}),
            previewUrl: item.previewUrl,
            selectedFileName: item.name,
            file_size_bytes: file.size,
            file_size_formatted: item.size,
            status: 'completed',
            is_valid: true
          };
          completedResults[index] = itemResult;
        } else {
          // If rejected by backend, skip it
          completedResults[index] = null;
        }

        // Live update Results page as each valid item completes
        if (setAnalysisData) {
          const currentValid = completedResults.filter(Boolean);
          if (currentValid.length > 0) {
            setAnalysisData([...currentValid]);
          }
        }
      } catch (err) {
        console.error('Analysis error for slide', item.name, err);
        completedResults[index] = null;
      }
    };

    const worker = async () => {
      while (currentIndex < totalToProcess) {
        const indexToRun = currentIndex++;
        await processItem(indexToRun);
      }
    };

    const workers = [];
    for (let i = 0; i < Math.min(CONCURRENCY, totalToProcess); i++) {
      workers.push(worker());
    }

    try {
      await Promise.all(workers);
    } catch (err) {
      setErrorMessage(err.message || 'Batch pipeline execution failed.');
    } finally {
      clearInterval(timer);
      setIsAnalyzing(false);
      setProcessingProgress('');

      // Pass only valid completed items to Results page
      const finalItems = completedResults.filter(Boolean);
      if (setAnalysisData && finalItems.length > 0) {
        setAnalysisData(finalItems);
      }
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (isMaxReached || isAnalyzing) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelect(e.dataTransfer.files);
    }
  };

  const handleReset = () => {
    setSelectedFilesList([]);
    setProcessedImages([]);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-8 py-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-xs text-center max-w-3xl mx-auto space-y-2">
        <span className="text-xs font-bold uppercase tracking-wider text-sky-700 bg-sky-50 px-3 py-1 rounded-full border border-sky-200">
          Automatic Research Pipeline
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Blood-Smear Microscopy Slide Analysis
        </h1>
        <p className="text-xs sm:text-sm text-slate-600">
          Upload microscopic blood slides (up to 50 max) for automatic validation, GAN + CBAM reconstruction, ResNet50 & DenseNet121 leukemia prediction, and Grad-CAM visualization.
        </p>
      </div>

      {/* Main Upload Zone */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between border-b border-slate-100 pb-4 gap-4">
          <div className="flex items-center gap-3">
            <Upload className="w-5 h-5 text-sky-600" />
            <div>
              <h2 className="text-lg font-bold text-slate-900">Automatic Slide Upload & Validation</h2>
              <div className="flex items-center gap-3 text-xs font-mono font-semibold mt-0.5">
                <span className="text-sky-700 bg-sky-50 border border-sky-200 px-2.5 py-0.5 rounded-full">
                  {currentCount} / {MAX_IMAGES} Images Selected
                </span>
                <span className="text-slate-600 font-sans">
                  {remainingSlots} images remaining
                </span>
              </div>
            </div>
          </div>

          {selectedCount > 0 && !isAnalyzing && (
            <button
              onClick={handleReset}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset Selection</span>
            </button>
          )}
        </div>

        {/* Hidden Input File Element */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => {
            if (e.target.files?.length) {
              handleFilesSelect(e.target.files);
              e.target.value = '';
            }
          }}
          accept="image/jpeg,image/jpg,image/png"
          multiple
          disabled={isMaxReached || isAnalyzing}
          className="hidden"
        />

        {selectedCount === 0 ? (
          /* Dropzone when 0 files selected */
          <div
            onDragOver={(e) => { e.preventDefault(); if (!isMaxReached) setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={onDrop}
            onClick={() => !isMaxReached && !isAnalyzing && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 ${
              isMaxReached
                ? 'border-slate-300 bg-slate-100/80 cursor-not-allowed opacity-75'
                : isDragOver
                ? 'border-sky-500 bg-sky-50/80 scale-[1.01] cursor-pointer'
                : 'border-slate-300 hover:border-sky-400 bg-slate-50/50 hover:bg-sky-50/30 cursor-pointer'
            }`}
          >
            {isMaxReached ? (
              <div className="space-y-2 py-4">
                <AlertCircle className="w-12 h-12 text-amber-600 mx-auto" />
                <h3 className="text-base font-extrabold text-slate-900">
                  Maximum 50 images reached
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  You have reached the maximum limit of {MAX_IMAGES} images. Click "Reset Selection" to upload a new batch.
                </p>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-sky-100 text-sky-700 flex items-center justify-center mx-auto mb-4 shadow-inner">
                  <ImageIcon className="w-8 h-8" />
                </div>

                <h3 className="text-base font-bold text-slate-900 mb-1">
                  Drag & Drop Blood-Smear Microscopy Images Here (Up to 50 Max)
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
                  Supports <strong className="text-slate-700">JPG, JPEG, PNG</strong> files. Maximum 50 images per batch.
                </p>

                <span className="inline-flex items-center gap-2 px-5 py-2.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-xl shadow-md shadow-sky-600/20 transition-colors">
                  <Upload className="w-4 h-4" />
                  <span>Browse Image Files ({remainingSlots} remaining)</span>
                </span>
              </>
            )}
          </div>
        ) : (
          /* Selected Files Thumbnail Grid & Action Buttons (No Auto-Upload) */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Selected Slide Images ({selectedCount} / {MAX_IMAGES})
              </h3>
              {remainingSlots > 0 && !isAnalyzing && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-700 hover:text-sky-900 bg-sky-50 border border-sky-200 px-3 py-1.5 rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add More Images ({remainingSlots} left)</span>
                </button>
              )}
            </div>

            {/* Grid of Selected Thumbnails */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 max-h-80 overflow-y-auto p-1 border border-slate-100 rounded-2xl">
              {selectedFilesList.map((item, idx) => (
                <div key={item.id} className={`relative group bg-slate-50 border rounded-xl p-2 flex flex-col items-center ${item.isValid === false ? 'border-rose-300 bg-rose-50/40' : 'border-slate-200'}`}>
                  <div className="w-full h-24 rounded-lg overflow-hidden bg-slate-200 mb-2 relative">
                    <img src={item.previewUrl} alt={item.name} className="w-full h-full object-cover" />
                    {item.isValid === false && (
                      <span className="absolute top-1 left-1 bg-rose-600 text-white text-[10px] font-black px-1.5 py-0.5 rounded shadow-md flex items-center gap-1 z-10">
                        <XCircle className="w-3 h-3 text-white" /> Invalid
                      </span>
                    )}
                    {!isAnalyzing && (
                      <button
                        type="button"
                        onClick={() => removeFileAt(idx)}
                        className="absolute top-1 right-1 p-1 bg-rose-600 text-white rounded-full shadow-md hover:bg-rose-700 opacity-90 group-hover:opacity-100 transition-opacity z-10"
                        title="Remove Image"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <p className="text-[11px] font-medium text-slate-700 truncate w-full text-center" title={item.name}>
                    {item.name}
                  </p>
                  <div className="flex items-center justify-between w-full text-[10px] mt-0.5">
                    <span className="text-slate-400 font-mono">{item.size}</span>
                    {item.isValid === false && (
                      <span className="font-bold text-rose-600">Invalid</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Dedicated Upload & Run Analysis Action Button */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-500">
                Ready to analyze <strong className="text-slate-800">{selectedCount} microscopy slides</strong> in fast parallel batch mode.
              </p>
              <button
                type="button"
                onClick={runBatchAnalysis}
                disabled={isAnalyzing}
                className="w-full sm:w-auto px-8 py-3.5 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-extrabold text-sm rounded-xl shadow-lg shadow-sky-600/25 transition-all flex items-center justify-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing Batch in Parallel...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Upload & Analyze ({selectedCount} {selectedCount === 1 ? 'Slide' : 'Slides'})</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

      </section>

      {/* Live Pipeline Execution Progress Monitor */}
      {isAnalyzing && (
        <section className="bg-white border-2 border-sky-400 rounded-3xl p-6 sm:p-8 shadow-md space-y-5 transition-all">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-50 text-sky-700 text-xs font-bold border border-sky-200 mb-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-600" />
                <span>Live Pipeline Execution</span>
              </div>
              <h2 className="text-xl font-extrabold text-slate-900">
                Processing: <span className="text-sky-700 font-mono">{activeFileName || 'Microscopy Slide'}</span>
              </h2>
              <p className="text-xs text-slate-500">
                Executing verified 5-stage reconstruction and deep learning pipeline...
              </p>
            </div>
            <div className="flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-2xl border border-slate-200">
              <Clock className="w-4 h-4 text-sky-600" />
              <span className="text-xs font-mono font-bold text-slate-800">
                Elapsed: {pipelineElapsedSeconds.toFixed(1)}s
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            <div className="p-3.5 rounded-2xl border border-sky-200 bg-sky-50/70 text-center space-y-1">
              <ShieldCheck className="w-5 h-5 text-sky-700 mx-auto" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Stage 1</span>
              <span className="text-xs font-black text-slate-900 block">Cytology Validation</span>
              <span className="text-[10px] text-slate-600 block">Stain signature check</span>
            </div>

            <div className="p-3.5 rounded-2xl border border-sky-200 bg-sky-50/70 text-center space-y-1">
              <Sparkles className="w-5 h-5 text-sky-700 mx-auto" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Stage 2</span>
              <span className="text-xs font-black text-slate-900 block">GAN + CBAM</span>
              <span className="text-[10px] text-slate-600 block">Attention denoising</span>
            </div>

            <div className="p-3.5 rounded-2xl border border-sky-200 bg-sky-50/70 text-center space-y-1">
              <Activity className="w-5 h-5 text-sky-700 mx-auto" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Stage 3</span>
              <span className="text-xs font-black text-slate-900 block">Acuity & Metrics</span>
              <span className="text-[10px] text-slate-600 block">PSNR / SSIM / MAE</span>
            </div>

            <div className="p-3.5 rounded-2xl border border-sky-200 bg-sky-50/70 text-center space-y-1">
              <Cpu className="w-5 h-5 text-sky-700 mx-auto" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Stage 4</span>
              <span className="text-xs font-black text-slate-900 block">Hybrid Model</span>
              <span className="text-[10px] text-slate-600 block">ResNet50 + DenseNet</span>
            </div>

            <div className="p-3.5 rounded-2xl border border-sky-200 bg-sky-50/70 text-center space-y-1">
              <Eye className="w-5 h-5 text-sky-700 mx-auto" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-sky-800 block">Stage 5</span>
              <span className="text-xs font-black text-slate-900 block">Grad-CAM Map</span>
              <span className="text-[10px] text-slate-600 block">Blast activation heatmap</span>
            </div>
          </div>
        </section>
      )}

      {/* Invalid Excluded Notice Banner */}
      {invalidNotice && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-950 text-xs flex items-center gap-3 shadow-xs">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <div>
            <strong className="block text-amber-950 font-bold">Strict Validation Guard Notice</strong>
            <span>{invalidNotice}</span>
          </div>
        </div>
      )}

      {/* Validation / Analysis Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center gap-3 shadow-xs">
          <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <div>
            <strong className="block text-rose-950 font-bold">Image Selection Info</strong>
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

    </div>
  );
}
