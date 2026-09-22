import React, { useState } from 'react';
import { Eye, Layers, ZoomIn, Info, CheckCircle2, Sliders, ArrowRight } from 'lucide-react';

export default function ImageComparison({ originalUrl, compressedUrl, reconstructedUrl, info, compression, metrics }) {
  const [activeView, setActiveView] = useState('all');

  const origRes = compression?.original_resolution || info?.dimensions || '2048 × 1536 pixels';
  const compRes = compression?.compressed_resolution || info?.dimensions || '2048 × 1536 pixels';
  const origSize = compression?.original_size_formatted || info?.file_size_formatted || 'N/A';
  const compSize = compression?.compressed_size_formatted || 'N/A';
  const quality = compression?.quality_percentage || 50;
  const reduction = compression?.size_reduction_percent || '0';
  const ratio = compression?.compression_ratio || '1:1';
  const resNote = compression?.resolution_note || `Resolution unchanged: ${origRes} → ${compRes}`;

  return (
    <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-600" />
            <span>3-Stage Image Comparison: Original vs Compressed vs Reconstructed</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect raw microscopy slide vs JPEG compression artifacts vs GAN + CBAM restored output
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
            3-Card View
          </button>
          <button
            onClick={() => setActiveView('comparison')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeView === 'comparison'
                ? 'bg-white text-sky-700 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Original vs Reconstructed
          </button>
        </div>
      </div>

      {/* Resolution status banner */}
      <div className="bg-sky-50 border border-sky-200 rounded-xl p-3 text-xs text-sky-900 flex items-center justify-between">
        <span className="font-bold flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-600" />
          <span>Spatial Resolution Status:</span>
        </span>
        <span className="font-mono bg-white px-2.5 py-1 rounded border border-sky-200 font-semibold text-sky-800">
          {resNote}
        </span>
      </div>

      {activeView === 'all' ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
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
                <img src={originalUrl} alt="Original Microscopy" className="max-h-48 w-auto object-contain rounded-lg border border-slate-200 shadow-xs" />
              ) : (
                <span className="text-xs text-slate-400">No image loaded</span>
              )}
            </div>
            <div className="bg-white p-3 border-t border-slate-200 text-xs space-y-1">
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">Resolution:</span> <span className="font-bold">{origRes}</span></div>
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">File Size:</span> <span className="font-bold">{origSize}</span></div>
            </div>
          </div>

          {/* Card 2: Compressed */}
          <div className="border border-amber-200 rounded-2xl overflow-hidden bg-amber-50/40 flex flex-col justify-between shadow-2xs">
            <div className="bg-white px-4 py-3 border-b border-amber-200 flex items-center justify-between">
              <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">2. COMPRESSED IMAGE</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                JPEG {quality}%
              </span>
            </div>
            <div className="p-4 flex items-center justify-center min-h-[200px]">
              {compressedUrl || originalUrl ? (
                <img src={compressedUrl || originalUrl} alt="Compressed" className="max-h-48 w-auto object-contain rounded-lg border border-amber-200 shadow-xs filter blur-[0.3px]" />
              ) : (
                <span className="text-xs text-amber-600">No image loaded</span>
              )}
            </div>
            <div className="bg-white p-3 border-t border-amber-200 text-xs space-y-1">
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">Resolution:</span> <span className="font-bold">{compRes}</span></div>
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">Compressed Size:</span> <span className="font-bold">{compSize}</span></div>
              <div className="flex justify-between text-amber-800 font-semibold"><span className="text-slate-400">Size Reduction:</span> <span className="font-extrabold">-{reduction}%</span></div>
            </div>
          </div>

          {/* Card 3: Reconstructed */}
          <div className="border border-sky-300 rounded-2xl overflow-hidden bg-sky-50/50 flex flex-col justify-between shadow-2xs">
            <div className="bg-sky-600 px-4 py-3 text-white flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                3. RECONSTRUCTED
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/20 text-white">
                GAN + CBAM
              </span>
            </div>
            <div className="p-4 flex items-center justify-center min-h-[200px]">
              {reconstructedUrl || originalUrl ? (
                <img src={reconstructedUrl || originalUrl} alt="Reconstructed" className="max-h-48 w-auto object-contain rounded-lg border border-sky-300 shadow-xs" />
              ) : (
                <span className="text-xs text-sky-600">No image loaded</span>
              )}
            </div>
            <div className="bg-white p-3 border-t border-sky-200 text-xs space-y-1">
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">Resolution:</span> <span className="font-bold">{origRes}</span></div>
              <div className="flex justify-between text-slate-600"><span className="text-slate-400">Output Mode:</span> <span className="font-bold text-sky-700">Restored Feature Map</span></div>
            </div>
          </div>

        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-slate-200 rounded-2xl p-4 bg-slate-50 text-center space-y-2">
            <h4 className="text-xs font-bold text-slate-700">Original Uncompressed Slide</h4>
            <img src={originalUrl} alt="Original" className="max-h-64 mx-auto rounded-lg border border-slate-200" />
            <div className="text-xs font-semibold text-slate-600">{origRes} • {origSize}</div>
          </div>
          <div className="border border-sky-300 rounded-2xl p-4 bg-sky-50/50 text-center space-y-2">
            <h4 className="text-xs font-bold text-sky-900">GAN + CBAM Reconstructed Output</h4>
            <img src={reconstructedUrl || originalUrl} alt="Reconstructed" className="max-h-64 mx-auto rounded-lg border border-sky-300" />
            <div className="text-xs font-bold text-sky-800">{origRes} • Restored Chromatin Details</div>
          </div>
        </div>
      )}

      {/* Detailed Compression Impact Matrix */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Exact Compression Impact Metrics
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Original Resolution</span>
            <span className="font-bold text-slate-800 font-mono">{origRes}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Compressed Resolution</span>
            <span className="font-bold text-slate-800 font-mono">{compRes}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Original File Size</span>
            <span className="font-bold text-slate-800">{origSize}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Compressed File Size</span>
            <span className="font-bold text-amber-800">{compSize}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">JPEG Quality Level</span>
            <span className="font-bold text-sky-700 font-mono">{quality}%</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">File Size Reduction</span>
            <span className="font-extrabold text-emerald-600">-{reduction}%</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Compression Ratio</span>
            <span className="font-bold text-indigo-700 font-mono">{ratio}</span>
          </div>
          <div className="bg-white p-3 rounded-xl border border-slate-200">
            <span className="text-slate-400 block text-[11px]">Spatial Dimensions</span>
            <span className="font-bold text-emerald-700">Preserved</span>
          </div>
        </div>
      </div>

    </div>
  );
}
