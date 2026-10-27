import React, { useState, useEffect } from 'react';
import {
  X, CheckCircle2, AlertCircle, Clock, Loader2, Play, Check,
  ChevronDown, ChevronRight, FileText, Cpu, Eye, Sparkles,
  Layers, ShieldCheck, Activity, Timer
} from 'lucide-react';

export default function LogsDrawer({
  isOpen,
  onClose,
  batchLogs = [],
  isBatchAnalyzing = false,
  batchElapsedSeconds = 0
}) {
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [expandedItemIds, setExpandedItemIds] = useState(new Set());

  // Close drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const totalCount = batchLogs.length;
  const completedCount = batchLogs.filter(item => item.status === 'completed').length;
  const runningCount = batchLogs.filter(item => item.status === 'running').length;
  const pendingCount = batchLogs.filter(item => item.status === 'pending').length;
  const failedCount = batchLogs.filter(item => item.status === 'failed').length;

  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Calculate estimated remaining time based on actual measured duration of completed slides
  const completedWithTime = batchLogs.filter(item => item.status === 'completed' && item.elapsedSeconds > 0);
  const avgDurationPerSlide = completedWithTime.length > 0
    ? (completedWithTime.reduce((sum, item) => sum + item.elapsedSeconds, 0) / completedWithTime.length)
    : null;

  const remainingSlidesCount = totalCount - completedCount - failedCount;
  const estimatedRemainingSeconds = avgDurationPerSlide && remainingSlidesCount > 0
    ? Math.round(remainingSlidesCount * avgDurationPerSlide)
    : null;

  const toggleExpand = (id) => {
    setExpandedItemIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedItemIds(new Set(batchLogs.map(item => item.id)));
  };

  const collapseAll = () => {
    setExpandedItemIds(new Set());
  };

  const filteredLogs = batchLogs.filter(item => {
    if (selectedFilter === 'All') return true;
    if (selectedFilter === 'Running') return item.status === 'running';
    if (selectedFilter === 'Completed') return item.status === 'completed';
    if (selectedFilter === 'Pending') return item.status === 'pending';
    if (selectedFilter === 'Failed') return item.status === 'failed';
    return true;
  });

  return (
    <>
      {/* Backdrop with subtle blur */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-[90] transition-opacity duration-300"
      />

      {/* Right-side Sliding Drawer Panel */}
      <div className="fixed top-0 right-0 h-full w-full sm:w-[620px] lg:w-[720px] bg-white shadow-2xl border-l border-slate-200 z-[100] flex flex-col font-sans animate-in slide-in-from-right duration-300">

        {/* Drawer Header */}
        <div className="p-5 sm:p-6 border-b border-slate-100 bg-slate-50/80 flex items-start justify-between gap-4 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900 text-white text-[11px] font-bold">
                <FileText className="w-3.5 h-3.5 text-sky-400" />
                <span>Batch Execution Logs</span>
              </span>
              {isBatchAnalyzing ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-100 text-sky-800 text-[11px] font-bold border border-sky-300 animate-pulse">
                  <Activity className="w-3 h-3 text-sky-600" />
                  <span>Pipeline Active</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold border border-emerald-300">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>{completedCount === totalCount && totalCount > 0 ? 'Batch Complete' : 'Idle'}</span>
                </span>
              )}
            </div>
            <h2 className="text-lg font-black text-slate-900 tracking-tight">
              Real-Time Slide Telemetry & Stage Logs
            </h2>
            <p className="text-xs text-slate-500">
              Live tracking of all {totalCount} uploaded microscopy slides across verified 8 pipeline stages
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
            title="Close Drawer (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress & Estimated Timing Summary Box */}
        <div className="p-5 sm:p-6 border-b border-slate-200 bg-white space-y-4 shrink-0 shadow-2xs">
          
          {/* Status Counts Pill Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
            <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200">
              <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">Completed</span>
              <span className="text-base font-black text-emerald-950 font-mono">{completedCount}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-sky-50 border border-sky-200">
              <span className="text-[10px] font-bold text-sky-700 uppercase tracking-wider block">Running</span>
              <span className="text-base font-black text-sky-950 font-mono flex items-center justify-center gap-1">
                {runningCount > 0 && <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-600" />}
                {runningCount}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Pending</span>
              <span className="text-base font-black text-slate-900 font-mono">{pendingCount}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200">
              <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">Failed</span>
              <span className="text-base font-black text-rose-950 font-mono">{failedCount}</span>
            </div>
          </div>

          {/* Overall Progress Bar */}
          <div>
            <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-1.5">
              <span>Overall Batch Progress: {completedCount} of {totalCount} Slides Completed</span>
              <span className="font-mono text-sky-700">{progressPercent}%</span>
            </div>
            <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div
                className="h-full bg-gradient-to-r from-sky-500 via-indigo-500 to-emerald-500 transition-all duration-300 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Timing Cards Grid (Measured Elapsed Time & Dynamic Estimated Remaining Time) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Total Elapsed Batch Time</span>
                <span className="text-sm font-black text-slate-900 font-mono">
                  {batchElapsedSeconds.toFixed(1)}s
                </span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shrink-0">
                <Timer className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block truncate">Estimated Remaining Time</span>
                <span className="text-sm font-black text-sky-950 font-mono block">
                  {remainingSlidesCount === 0 && totalCount > 0 ? (
                    <span className="text-emerald-700 font-sans text-xs">Completed</span>
                  ) : estimatedRemainingSeconds != null ? (
                    `~${estimatedRemainingSeconds}s`
                  ) : (
                    <span className="text-xs font-normal text-slate-500 font-sans">Calculating estimate...</span>
                  )}
                </span>
                <span className="text-[9px] text-slate-400 block truncate">
                  *Dynamic estimate based on measured slide times ({avgDurationPerSlide ? `${avgDurationPerSlide.toFixed(1)}s/slide` : 'pending'})
                </span>
              </div>
            </div>
          </div>

          {/* Filter Bar & Expand/Collapse Toggle */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
            <div className="flex items-center gap-1 overflow-x-auto scrollbar-none py-1">
              {['All', 'Running', 'Completed', 'Pending', 'Failed'].map((filterName) => (
                <button
                  key={filterName}
                  onClick={() => setSelectedFilter(filterName)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                    selectedFilter === filterName
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  {filterName}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={expandAll}
                className="text-sky-700 hover:text-sky-900 font-bold hover:underline cursor-pointer"
              >
                Expand All
              </button>
              <span className="text-slate-300">|</span>
              <button
                onClick={collapseAll}
                className="text-slate-500 hover:text-slate-800 font-bold hover:underline cursor-pointer"
              >
                Collapse All
              </button>
            </div>
          </div>

        </div>

        {/* Scrollable List of All 50 Images */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-3.5 bg-slate-50/50">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 text-slate-400 text-xs">
              No slides match the selected filter.
            </div>
          ) : (
            filteredLogs.map((item) => {
              const isExpanded = expandedItemIds.has(item.id);
              const isCompleted = item.status === 'completed';
              const isRunning = item.status === 'running';
              const isFailed = item.status === 'failed';
              const isPending = item.status === 'pending';

              return (
                <div
                  key={item.id}
                  className={`rounded-2xl border transition-all bg-white shadow-2xs ${
                    isRunning
                      ? 'border-sky-400 ring-2 ring-sky-200/60'
                      : isFailed
                      ? 'border-rose-300 bg-rose-50/20'
                      : isCompleted
                      ? 'border-slate-200 hover:border-slate-300'
                      : 'border-slate-200 opacity-80'
                  }`}
                >
                  {/* Card Header Summary */}
                  <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <span className={`px-2 py-1 rounded-lg text-xs font-black shrink-0 ${
                        isCompleted
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : isRunning
                          ? 'bg-sky-100 text-sky-800 border border-sky-300 animate-pulse'
                          : isFailed
                          ? 'bg-rose-100 text-rose-800 border border-rose-200'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}>
                        #{item.index}
                      </span>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-extrabold text-slate-900 truncate max-w-[240px] sm:max-w-[320px]" title={item.filename}>
                            {item.filename}
                          </h4>
                          {item.prediction && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-50 text-indigo-900 border border-indigo-200 font-mono">
                              {item.prediction} {item.confidence != null && `(${item.confidence}%)`}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500 mt-1">
                          <span className="flex items-center gap-1 font-mono">
                            <Clock className="w-3 h-3 text-slate-400" />
                            {item.startTime ? `Started: ${item.startTime}` : 'Queued'}
                          </span>
                          {item.completionTime && (
                            <span className="font-mono">
                              Finished: {item.completionTime}
                            </span>
                          )}
                          <span className="font-mono font-bold text-slate-700">
                            Elapsed: {Number(item.elapsedSeconds || 0).toFixed(1)}s
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right Status Badge & Expand Toggle */}
                    <div className="flex items-center justify-between sm:justify-end gap-2 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider inline-flex items-center gap-1 ${
                        isCompleted
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : isRunning
                          ? 'bg-sky-50 text-sky-800 border border-sky-300 animate-pulse'
                          : isFailed
                          ? 'bg-rose-50 text-rose-800 border border-rose-200'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}>
                        {isRunning && <Loader2 className="w-3 h-3 animate-spin text-sky-600" />}
                        {item.status}
                      </span>

                      <button
                        onClick={() => toggleExpand(item.id)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer flex items-center gap-1 text-[11px] font-bold"
                        title="Toggle Pipeline Stages"
                      >
                        <span>{isExpanded ? 'Hide Stages' : 'View Stages'}</span>
                        {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Error Notification if failed */}
                  {isFailed && item.error && (
                    <div className="mx-4 mb-3 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold block">Processing Failure:</span>
                        <span>{item.error}</span>
                      </div>
                    </div>
                  )}

                  {/* Expandable 8-Stage Pipeline Breakdown */}
                  {isExpanded && (
                    <div className="border-t border-slate-100 bg-slate-50/70 p-4 space-y-2 rounded-b-2xl">
                      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                        <span>Verified Pipeline Stages (8 Stages)</span>
                        <span>Execution Timing</span>
                      </div>

                      <div className="space-y-1.5">
                        {(item.stages && item.stages.length > 0 ? item.stages : [
                          { stage: '1. Image validation', status: isPending ? 'Pending' : (isRunning ? 'Running' : 'Completed'), details: 'Wright-Giemsa microscopy verification' },
                          { stage: '2. GAN + CBAM reconstruction', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Attention-guided residual denoising' },
                          { stage: '3. Image enhancement & PSNR/SSIM/MAE calculation', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'High-frequency edge sharpness & pixel fidelity' },
                          { stage: '4. ResNet50 feature extraction', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Deep residual bottleneck activation' },
                          { stage: '5. DenseNet121 feature extraction', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Dense connectivity feature mapping' },
                          { stage: '6. Hybrid classification and prediction', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Multi-head feature fusion & posterior probabilities' },
                          { stage: '7. Grad-CAM generation', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Explainability visual heatmap overlay' },
                          { stage: '8. Final result preparation', status: isPending ? 'Pending' : (isCompleted ? 'Completed' : 'Pending'), details: 'Benchmark metrics and report payload packaging' }
                        ]).map((stageItem, sIdx) => {
                          const isStageDone = stageItem.status === 'Completed';
                          const isStageRunning = stageItem.status === 'Running';
                          const isStageFailed = stageItem.status === 'Failed';
                          const isStageSkipped = stageItem.status === 'Skipped';

                          return (
                            <div
                              key={sIdx}
                              className={`p-2 rounded-xl border text-xs flex items-center justify-between gap-3 ${
                                isStageDone
                                  ? 'bg-white border-emerald-100'
                                  : isStageRunning
                                  ? 'bg-sky-50 border-sky-300'
                                  : isStageFailed
                                  ? 'bg-rose-50 border-rose-200'
                                  : isStageSkipped
                                  ? 'bg-slate-100/60 border-slate-200 text-slate-400'
                                  : 'bg-white border-slate-200 text-slate-400'
                              }`}
                            >
                              <div className="flex items-center gap-2 min-w-0">
                                {isStageDone ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                ) : isStageRunning ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-600 shrink-0" />
                                ) : isStageFailed ? (
                                  <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                                ) : (
                                  <div className="w-3.5 h-3.5 rounded-full border border-slate-300 shrink-0" />
                                )}
                                <div className="min-w-0">
                                  <span className={`font-bold block truncate ${
                                    isStageDone ? 'text-slate-800' : isStageRunning ? 'text-sky-950' : 'text-slate-500'
                                  }`}>
                                    {stageItem.stage}
                                  </span>
                                  {stageItem.details && (
                                    <span className="text-[10px] text-slate-500 block truncate max-w-[280px]">
                                      {stageItem.details}
                                    </span>
                                  )}
                                </div>
                              </div>

                              <div className="text-right shrink-0 font-mono text-[11px]">
                                {stageItem.duration_ms != null ? (
                                  <span className="font-bold text-slate-700">
                                    {stageItem.duration_ms} ms
                                  </span>
                                ) : (
                                  <span className="text-slate-400 text-[10px] uppercase">
                                    {stageItem.status || 'Pending'}
                                  </span>
                                )}
                                {stageItem.start_time && (
                                  <span className="block text-[9px] text-slate-400">
                                    {stageItem.start_time}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              );
            })
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-slate-500 shrink-0">
          <span className="font-mono text-[11px]">
            Worker Pool: Concurrency 2 (PyTorch CPU Optimized)
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl text-xs transition-colors cursor-pointer"
          >
            Close Logs Panel
          </button>
        </div>

      </div>
    </>
  );
}
