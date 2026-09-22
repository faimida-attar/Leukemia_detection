import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';

export default function ValidationBadge({ validationState, isValidating }) {
  if (isValidating) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-xl bg-sky-50 border border-sky-200 text-sky-900 animate-pulse">
        <Loader2 className="w-6 h-6 text-sky-600 animate-spin shrink-0" />
        <div>
          <span className="font-semibold text-sm block">Checking image validity...</span>
          <span className="text-xs text-sky-700">Analyzing blood-smear microscopy features and slide stain signature</span>
        </div>
      </div>
    );
  }

  if (!validationState) return null;

  const isValid = validationState.is_valid;

  if (isValid) {
    return (
      <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 shadow-xs space-y-2">
        <div className="flex items-center gap-2.5">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="font-bold text-sm text-emerald-900">✓ Valid Blood-Smear Microscopy Image</span>
        </div>
        <p className="text-xs text-emerald-700 leading-relaxed pl-7">
          {validationState.message || 'Confirmed microscopic slide structure with characteristic stain features. Ready for reconstruction & analysis.'}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 shadow-xs space-y-2">
      <div className="flex items-center gap-2.5">
        <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
        <span className="font-bold text-sm text-rose-900">✕ Invalid Image</span>
      </div>
      <p className="text-xs text-rose-700 leading-relaxed pl-7">
        {validationState.message || 'The uploaded file is not a valid blood-smear microscopy image. (Photographs, selfies, documents, or low-resolution images cannot be analyzed.)'}
      </p>
      {validationState.details?.reason && (
        <div className="ml-7 text-xs bg-rose-100/70 p-2 rounded border border-rose-200 text-rose-800 font-mono">
          Reason: {validationState.details.reason}
        </div>
      )}
    </div>
  );
}
