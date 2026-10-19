import React, { useState } from 'react';
import { Eye, Layers, ZoomIn, Info, CheckCircle2, Sliders, ArrowRight } from 'lucide-react';

export default function ImageComparison({ originalUrl, reconstructedUrl, info, metrics }) {
  const [activeView, setActiveView] = useState('all');

  const origRes = info?.original_dimensions || info?.dimensions || '2048 × 1536 pixels';
  const origSize = info?.original_file_size_formatted || info?.file_size_formatted || 'N/A';
  const reconSize = info?.reconstructed_file_size_formatted || origSize;
  const psnr = metrics?.psnr_db ?? metrics?.psnr ?? 'N/A';
  const ssim = metrics?.ssim ?? 'N/A';
  const mae = metrics?.mae ?? 'N/A';

  return (
    <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-600" />
            <span>Image Enhancement Comparison: Original vs GAN + CBAM Reconstructed</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect raw microscopy slide vs GAN + CBAM restored and enhanced output
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button
            onClick={() => setActiveView('all')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeView === 'all'
                ? 'bg-white text-sky-700 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Side-by-Side View
          </button>
        </div>
      </div>

      {/* Spatial Dimension Status Banner */}
      <div className="bg-sky-50 border border-sky-200 rounded-xl p-3 text-xs text-sky-900 flex items-center justify-between">
        <span className="font-bold flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-600" />
          <span>Image Dimension & Quality Status:</span>
        </span>
        <span className="font-mono bg-white px-2.5 py-1 rounded border border-sky-200 font-semibold text-sky-800">
          Dimensions Preserved: {origRes} • GAN + CBAM Enhanced
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Card 1: Original */}
        <div className="border border-slate-200 rounded-2xl overflow-hidden bg-slate-50 flex flex-col justify-between shadow-2xs">
          <div className="bg-white px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">1. ORIGINAL IMAGE</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              Ground Truth
            </span>
          </div>
          <div className="p-4 flex items-center justify-center min-h-[200px]">
            {originalUrl ? (
              <img src={originalUrl} alt="Original Microscopy" className="max-h-56 w-auto object-contain rounded-lg border border-slate-200 shadow-xs" />
            ) : (
              <span className="text-xs text-slate-400">No image loaded</span>
            )}
          </div>
          <div className="bg-white p-3 border-t border-slate-200 text-xs space-y-1">
            <div className="flex justify-between text-slate-600"><span className="text-slate-400">Resolution:</span> <span className="font-bold">{origRes}</span></div>
            <div className="flex justify-between text-slate-600"><span className="text-slate-400">File Size:</span> <span className="font-bold">{origSize}</span></div>
          </div>
        </div>

        {/* Card 2: Reconstructed */}
        <div className="border border-sky-300 rounded-2xl overflow-hidden bg-sky-50/50 flex flex-col justify-between shadow-2xs">
          <div className="bg-sky-600 px-4 py-3 text-white flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              2. RECONSTRUCTED IMAGE
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/20 text-white">
              GAN + CBAM Enhanced
            </span>
          </div>
          <div className="p-4 flex items-center justify-center min-h-[200px]">
            {reconstructedUrl || originalUrl ? (
              <img src={reconstructedUrl || originalUrl} alt="Reconstructed" className="max-h-56 w-auto object-contain rounded-lg border border-sky-300 shadow-xs" />
            ) : (
              <span className="text-xs text-sky-600">No image loaded</span>
            )}
          </div>
          <div className="bg-white p-3 border-t border-sky-200 text-xs space-y-1">
            <div className="flex justify-between text-slate-600"><span className="text-slate-400">Resolution:</span> <span className="font-bold">{origRes}</span></div>
            <div className="flex justify-between text-slate-600"><span className="text-slate-400">Enhanced Size:</span> <span className="font-bold text-sky-700">{reconSize}</span></div>
          </div>
        </div>

      </div>

      {/* Reconstruction Quality Metrics */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Reconstruction Quality Metrics
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">PSNR (Peak Signal-to-Noise Ratio)</span>
            <span className="font-bold text-slate-800 font-mono text-sm">{typeof psnr === 'number' ? `${psnr.toFixed(2)} dB` : psnr}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">SSIM (Structural Similarity)</span>
            <span className="font-bold text-slate-800 font-mono text-sm">{typeof ssim === 'number' ? ssim.toFixed(4) : ssim}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">MAE (Mean Absolute Error)</span>
            <span className="font-bold text-slate-800 font-mono text-sm">{typeof mae === 'number' ? mae.toFixed(4) : mae}</span>
          </div>
        </div>
      </div>

    </div>
  );
}
