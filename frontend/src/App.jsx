import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import ImageAnalysis from './pages/ImageAnalysis';
import Results from './pages/Results';
import ModelPerformance from './pages/ModelPerformance';
import ErrorBoundary from './components/ErrorBoundary';
import LogsDrawer from './components/LogsDrawer';
import { analyzeCompletePipelineApi } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('analysis');
  const [analysisData, setAnalysisData] = useState(null);

  // Batch Execution State & Logs Management (Supports up to 50 images)
  const [batchLogs, setBatchLogs] = useState([]);
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
  const [batchElapsedSeconds, setBatchElapsedSeconds] = useState(0);
  const [activeProcessingFileName, setActiveProcessingFileName] = useState('');
  const [isLogsDrawerOpen, setIsLogsDrawerOpen] = useState(false);

  const batchTimerRef = useRef(null);
  const batchStartTimeRef = useRef(null);

  // Real-time live elapsed timer ticker (updates batch timer and running items)
  useEffect(() => {
    if (isBatchAnalyzing) {
      batchStartTimeRef.current = Date.now();
      batchTimerRef.current = setInterval(() => {
        const now = Date.now();
        const elapsed = (now - batchStartTimeRef.current) / 1000;
        setBatchElapsedSeconds(elapsed);

        // Update elapsed time for all items currently running
        setBatchLogs((prevLogs) =>
          prevLogs.map((item) => {
            if (item.status === 'running' && item.startTimestamp) {
              const itemElapsed = (now - item.startTimestamp) / 1000;
              return { ...item, elapsedSeconds: itemElapsed };
            }
            return item;
          })
        );
      }, 200);
    } else {
      if (batchTimerRef.current) {
        clearInterval(batchTimerRef.current);
        batchTimerRef.current = null;
      }
    }

    return () => {
      if (batchTimerRef.current) {
        clearInterval(batchTimerRef.current);
      }
    };
  }, [isBatchAnalyzing]);

  // Primary Batch Execution Engine for up to 50 images
  const startBatchAnalysis = async (selectedFiles) => {
    if (!selectedFiles || selectedFiles.length === 0 || isBatchAnalyzing) return;

    // Filter valid slides
    const validItems = selectedFiles.filter(item => item.isValid !== false);
    if (validItems.length === 0) return;

    const totalToProcess = validItems.length;

    // 1. Initialize real-time batch logs for all uploaded images (all 50 images!)
    const initialLogs = validItems.map((item, idx) => ({
      id: `slide_${idx + 1}_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      index: idx + 1,
      filename: item.name,
      file: item.file,
      fileSizeBytes: item.file.size,
      fileSizeFormatted: item.size,
      previewUrl: item.previewUrl,
      status: 'pending',
      currentStage: 'Queued (Waiting for worker)',
      currentStageIndex: 0,
      startTime: null,
      completionTime: null,
      elapsedSeconds: 0,
      startTimestamp: null,
      prediction: null,
      confidence: null,
      error: null,
      stages: [
        { stage: '1. Image validation', status: 'Pending', details: 'Wright-Giemsa microscopy verification' },
        { stage: '2. GAN + CBAM reconstruction', status: 'Pending', details: 'Attention-guided residual denoising' },
        { stage: '3. Image enhancement & PSNR/SSIM/MAE calculation', status: 'Pending', details: 'High-frequency edge sharpness & pixel fidelity' },
        { stage: '4. ResNet50 feature extraction', status: 'Pending', details: 'Deep residual bottleneck activation' },
        { stage: '5. DenseNet121 feature extraction', status: 'Pending', details: 'Dense connectivity feature mapping' },
        { stage: '6. Hybrid classification and prediction', status: 'Pending', details: 'Multi-head feature fusion & posterior probabilities' },
        { stage: '7. Grad-CAM generation', status: 'Pending', details: 'Explainability visual heatmap overlay' },
        { stage: '8. Final result preparation', status: 'Pending', details: 'Benchmark metrics and report payload packaging' }
      ],
      resultData: null
    }));

    setBatchLogs(initialLogs);
    setBatchElapsedSeconds(0);
    setIsBatchAnalyzing(true);

    // Initial placeholder items for Results view
    const initialPlaceholders = validItems.map((item, idx) => ({
      status: 'processing',
      previewUrl: item.previewUrl,
      selectedFileName: item.name,
      file_size_formatted: item.size,
      file_size_bytes: item.file.size,
      is_valid: true,
      origIdx: idx
    }));

    setAnalysisData(initialPlaceholders);

    // Immediate redirection to Results page as required
    setActiveTab('results');

    let completedResults = [...initialPlaceholders];
    let currentIndex = 0;
    const CONCURRENCY = 2; // Optimal concurrency for CPU PyTorch inference

    const processItem = async (index) => {
      const item = validItems[index];
      const logId = initialLogs[index].id;
      const file = item.file;
      const startMs = Date.now();
      const startTimeStr = new Date().toLocaleTimeString();

      setActiveProcessingFileName(item.name);

      // Update log to Running
      setBatchLogs((prevLogs) =>
        prevLogs.map((l) =>
          l.id === logId
            ? {
                ...l,
                status: 'running',
                startTime: startTimeStr,
                startTimestamp: startMs,
                currentStage: '1. Image validation',
                currentStageIndex: 1
              }
            : l
        )
      );

      const formData = new FormData();
      formData.append('image', file);

      try {
        const resultData = await analyzeCompletePipelineApi(formData);
        const completionTimeStr = new Date().toLocaleTimeString();
        const durationSec = resultData?.total_execution_time_seconds || Math.max(0.1, (Date.now() - startMs) / 1000);
        const isItemValid = resultData?.is_valid === true &&
          !resultData?.status?.toLowerCase().includes('invalid') &&
          !resultData?.prediction?.toLowerCase().includes('invalid');

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

          // Update log to Completed
          setBatchLogs((prevLogs) =>
            prevLogs.map((l) =>
              l.id === logId
                ? {
                    ...l,
                    status: 'completed',
                    completionTime: completionTimeStr,
                    elapsedSeconds: durationSec,
                    currentStage: 'All 8 stages completed',
                    currentStageIndex: 8,
                    prediction: resultData.hybrid_pred || resultData.prediction || 'ALL',
                    confidence: resultData.hybrid_conf ?? resultData.confidence,
                    stages: resultData.pipeline_logs || l.stages,
                    resultData: itemResult
                  }
                : l
            )
          );
        } else {
          // Validation failed / rejected
          completedResults[index] = null;

          setBatchLogs((prevLogs) =>
            prevLogs.map((l) =>
              l.id === logId
                ? {
                    ...l,
                    status: 'failed',
                    completionTime: completionTimeStr,
                    elapsedSeconds: durationSec,
                    currentStage: 'Validation Rejected',
                    error: resultData?.message || resultData?.validation?.reason || 'Non-microscopy slide rejected',
                    stages: resultData.pipeline_logs || l.stages
                  }
                : l
            )
          );
        }

        // Live update Results view with valid items
        const currentValid = completedResults.filter(Boolean);
        if (currentValid.length > 0) {
          setAnalysisData([...currentValid]);
        }
      } catch (err) {
        console.error('Batch error for slide:', item.name, err);
        const completionTimeStr = new Date().toLocaleTimeString();
        const durationSec = Math.max(0.1, (Date.now() - startMs) / 1000);
        completedResults[index] = null;

        setBatchLogs((prevLogs) =>
          prevLogs.map((l) =>
            l.id === logId
              ? {
                  ...l,
                  status: 'failed',
                  completionTime: completionTimeStr,
                  elapsedSeconds: durationSec,
                  currentStage: 'Failed during inference',
                  error: err.message || 'Pipeline execution failed for this slide'
                }
              : l
          )
        );
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
      console.error('Batch execution error:', err);
    } finally {
      setIsBatchAnalyzing(false);
      setActiveProcessingFileName('');

      // Final pass: provide all completed valid items to Results view
      const finalItems = completedResults.filter(Boolean);
      if (finalItems.length > 0) {
        setAnalysisData(finalItems);
      }
    }
  };

  const openLogsDrawer = () => setIsLogsDrawerOpen(true);
  const closeLogsDrawer = () => setIsLogsDrawerOpen(false);

  const renderActivePage = () => {
    switch (activeTab) {
      case 'analysis':
        return (
          <ImageAnalysis
            setActiveTab={setActiveTab}
            setAnalysisData={setAnalysisData}
            isBatchAnalyzing={isBatchAnalyzing}
            startBatchAnalysis={startBatchAnalysis}
            batchLogs={batchLogs}
            openLogsDrawer={openLogsDrawer}
          />
        );
      case 'comparison':
        return (
          <ModelPerformance
            setActiveTab={setActiveTab}
            analysisData={analysisData}
          />
        );
      case 'results':
        return (
          <Results
            setActiveTab={setActiveTab}
            analysisData={analysisData}
            batchLogs={batchLogs}
            isBatchAnalyzing={isBatchAnalyzing}
            activeProcessingFileName={activeProcessingFileName}
            openLogsDrawer={openLogsDrawer}
          />
        );
      default:
        return (
          <ImageAnalysis
            setActiveTab={setActiveTab}
            setAnalysisData={setAnalysisData}
            isBatchAnalyzing={isBatchAnalyzing}
            startBatchAnalysis={startBatchAnalysis}
            batchLogs={batchLogs}
            openLogsDrawer={openLogsDrawer}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased selection:bg-sky-500 selection:text-white">
      {/* Top Header Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1">
        <ErrorBoundary onNavigateHome={() => setActiveTab('analysis')}>
          {renderActivePage()}
        </ErrorBoundary>
      </main>

      {/* Right-Side Logs Drawer Panel */}
      <LogsDrawer
        isOpen={isLogsDrawerOpen}
        onClose={closeLogsDrawer}
        batchLogs={batchLogs}
        isBatchAnalyzing={isBatchAnalyzing}
        batchElapsedSeconds={batchElapsedSeconds}
      />
    </div>
  );
}
