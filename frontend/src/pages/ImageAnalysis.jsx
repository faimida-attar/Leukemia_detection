import React, { useState, useRef } from 'react';
import {
  Upload, Image as ImageIcon, CheckCircle2, XCircle, Sliders,
  Sparkles, AlertCircle, Loader2, RefreshCw, FileText, Check, Trash2, Plus
} from 'lucide-react';
import ValidationBadge from '../components/ValidationBadge';
import { validateImageMock, runFullPipelineMock } from '../services/mockApi';
import { analyzeCompletePipelineApi, validateImageApi } from '../services/api';

export default function ImageAnalysis({ setActiveTab, setAnalysisData }) {
  const MAX_IMAGES = 50;

  const [isDragOver, setIsDragOver] = useState(false);

  // Track selected files state array & preview URLs
  const [selectedFilesList, setSelectedFilesList] = useState([]);

  // Track processed images state array dynamically
  const [processedImages, setProcessedImages] = useState([]);

  // Compression slider state (10% to 90%)
  const [compressionQuality, setCompressionQuality] = useState(50);

  // Pipeline processing state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

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

      return {
        file,
        id: Math.random().toString(36).substring(2, 9) + Date.now(),
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
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
        const valRes = await validateImageApi(formData).catch(() => validateImageMock(item.file));
        const isValid = valRes?.is_valid !== false && valRes?.status !== 'Invalid Image';
        setSelectedFilesList((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, isValid } : f))
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

    // Filter out invalid images from analysis (Strict Validation Guard)
    const validSelection = selectedFilesList.filter(item => item.isValid !== false);
    const rejectedCount = selectedFilesList.length - validSelection.length;

    if (rejectedCount > 0) {
      setInvalidNotice(`${rejectedCount} invalid image(s) detected and excluded from analysis.`);
    } else {
      setInvalidNotice(null);
    }

    if (validSelection.length === 0) {
      setErrorMessage('No valid blood-smear microscopy slide detected in selected batch. Excluded invalid items.');
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);

    // 1. Instantly prepare initial placeholders for ONLY VALID selected files
    const initialResults = validSelection.map((item, idx) => ({
      id: item.id || idx,
      selectedFileName: item.name,
      previewUrl: item.previewUrl,
      status: 'processing',
      is_valid: true
    }));

    // 2. Immediately set analysisData and navigate to Results tab (0ms delay!)
    if (setAnalysisData) {
      setAnalysisData(initialResults);
    }
    setActiveTab('results');

    // 3. Parallel Worker Queue with Concurrency = 4
    const CONCURRENCY = 4;
    const totalToProcess = validSelection.length;
    let completedResults = [...initialResults];
    let currentIndex = 0;

    const processItem = async (index) => {
      const item = validSelection[index];
      const file = item.file;

      const formData = new FormData();
      formData.append('image', file);
      formData.append('quality', compressionQuality);

      let resultData;
      try {
        resultData = await analyzeCompletePipelineApi(formData);
      } catch (backendError) {
        resultData = await runFullPipelineMock(file, compressionQuality);
      }

      const itemResult = {
        ...(resultData || {}),
        previewUrl: item.previewUrl,
        selectedFileName: item.name,
        status: 'completed',
        is_valid: resultData?.is_valid !== false && resultData?.success !== false
      };

      completedResults[index] = itemResult;
      setProcessedImages((prev) => [...prev, itemResult]);

      // Only pass valid processed items to Results page
      const validOnlyResults = completedResults.filter(res => res?.is_valid !== false);

      if (setAnalysisData) {
        setAnalysisData([...validOnlyResults]);
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
      setIsAnalyzing(false);
      setProcessingProgress('');
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
