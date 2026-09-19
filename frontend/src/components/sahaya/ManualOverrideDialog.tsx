"use client";

import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { EvaluationCheck } from "@/lib/api";

interface ManualOverrideDialogProps {
  resourceName: string;
  blockingChecks: EvaluationCheck[];
  onAuthorize: (reason: string) => Promise<void>;
  onCancel: () => void;
}

export function ManualOverrideDialog({ resourceName, blockingChecks, onAuthorize, onCancel }: ManualOverrideDialogProps) {
  const [reason, setReason] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [isAuthorizing, setIsAuthorizing] = useState(false);
  const [error, setError] = useState("");
  const canAuthorize = reason.trim().length > 0 && acknowledged && !isAuthorizing;

  const handleAuthorize = async () => {
    if (!canAuthorize) return;
    setIsAuthorizing(true);
    setError("");
    try {
      await onAuthorize(reason.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to authorize the override.");
      setIsAuthorizing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="override-title">
      <div className="card w-full max-w-lg p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 shrink-0 bg-unknown-100 text-unknown-700 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="metric-label mb-1">MANUAL OVERRIDE</p>
            <h2 id="override-title" className="text-2xl font-bold text-gray-900">Authorize exception</h2>
            <p className="text-sm text-gray-600 mt-1">Resource: <span className="font-semibold text-gray-900">{resourceName}</span></p>
          </div>
        </div>

        <div className="rounded-xl bg-blocked-50 border border-blocked-100 p-4 mb-5">
          <p className="font-semibold text-blocked-700 text-sm mb-2">Original decision: BLOCKED</p>
          <p className="text-xs text-gray-600 mb-2">Blocking requirements</p>
          <ul className="space-y-2 text-sm text-gray-800">
            {blockingChecks.map((check) => (
              <li key={check.constraint}>✕ {check.requirement_label}: BLOCKED</li>
            ))}
          </ul>
        </div>

        <label className="block text-sm font-semibold text-gray-800 mb-2" htmlFor="override-reason">Override reason</label>
        <textarea
          id="override-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Explain why this exception is being authorized..."
          rows={4}
          className="w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
        />

        <label className="flex items-start gap-3 text-sm text-gray-700 my-5 cursor-pointer">
          <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} className="mt-1" />
          <span>I have reviewed the blocking evidence and understand that this resource conflicts with a required capability.</span>
        </label>

        {error && <p className="text-sm text-blocked-700 mb-4">{error}</p>}

        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={onCancel} disabled={isAuthorizing} className="btn-secondary flex-1">Cancel</button>
          <button onClick={handleAuthorize} disabled={!canAuthorize} className="btn-primary flex-1">
            {isAuthorizing ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Authorize Override"}
          </button>
        </div>
      </div>
    </div>
  );
}
