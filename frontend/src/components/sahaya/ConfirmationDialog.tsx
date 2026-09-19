"use client";

import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";

interface ConfirmationDialogProps {
  onConfirm: () => Promise<void>;
  onCancel: () => void;
  resourceName: string;
  verifiedRequirements: string[];
}

export function ConfirmationDialog({ onConfirm, onCancel, resourceName, verifiedRequirements }: ConfirmationDialogProps) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [hasReviewedEvidence, setHasReviewedEvidence] = useState(false);

  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      await onConfirm();
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-md p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-16 h-16 bg-safe-100 text-safe-600 rounded-full flex items-center justify-center mb-4">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Confirm Assignment</h2>
          <p className="text-gray-600">
            Resource: <span className="font-semibold text-gray-900">{resourceName}</span>
          </p>
        </div>

        <div className="rounded-xl bg-safe-50 border border-safe-100 p-4 mb-5 text-left">
          <p className="font-semibold text-safe-700 mb-2">Verified requirements</p>
          <ul className="text-sm text-gray-700 space-y-1">
            {verifiedRequirements.map((requirement) => <li key={requirement}>✓ {requirement}</li>)}
          </ul>
        </div>

        <label className="flex items-start gap-3 text-sm text-gray-700 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={hasReviewedEvidence}
            onChange={(event) => setHasReviewedEvidence(event.target.checked)}
            className="mt-1"
          />
          <span>I have reviewed the evidence and confirm this resource.</span>
        </label>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={onCancel}
            disabled={isConfirming}
            className="btn-secondary flex-1"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirming || !hasReviewedEvidence}
            className="btn-confirm flex-1"
          >
            {isConfirming ? (
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            ) : (
              "Confirm & Record"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
