"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import {
  confirmRequirements,
  getRequirements,
  RequirementReviewItem,
  RequirementValue,
  updateRequirement,
} from "@/lib/api";

const REVIEW_OPTIONS: { value: RequirementValue; label: string }[] = [
  { value: "required", label: "Required" },
  { value: "not_required", label: "Not Required" },
  { value: "unknown", label: "Unknown" },
];

const valueBadgeClass: Record<RequirementValue, string> = {
  required: "badge-safe",
  not_required: "badge-not-applicable",
  unknown: "badge-unknown",
};

export default function RequirementReviewPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [requirements, setRequirements] = useState<RequirementReviewItem[]>([]);
  const [version, setVersion] = useState(0);
  const [reviewed, setReviewed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingField, setSavingField] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getRequirements(id)
      .then((response) => {
        setRequirements(response.requirements);
        setVersion(response.requirement_version);
        setReviewed(response.reviewed);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load requirements."))
      .finally(() => setLoading(false));
  }, [id]);

  const activeRequirements = useMemo(
    () => requirements.filter((requirement) => requirement.final_value === "required"),
    [requirements],
  );

  const updateValue = async (field: string, value: RequirementValue) => {
    const current = requirements.find((requirement) => requirement.field === field);
    if (!current || current.final_value === value) return;
    setSavingField(field);
    setError("");
    try {
      await updateRequirement(id, field, value);
      setReviewed(false);
      setRequirements((items) => items.map((item) => item.field === field
        ? { ...item, final_value: value, source: item.ai_value === value ? "ai_extraction" : "human_edited" }
        : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update this requirement.");
    } finally {
      setSavingField(null);
    }
  };

  const confirm = async () => {
    if (reviewed) {
      router.push(`/incident/${id}/resources`);
      return;
    }
    setConfirming(true);
    setError("");
    try {
      await confirmRequirements(id);
      router.push(`/incident/${id}/resources`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to confirm requirements.");
      setConfirming(false);
    }
  };

  if (loading) {
    return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600" /></div>;
  }

  return (
    <div className="page-container">
      <Link href={`/incident/${id}`} className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to case</Link>

      <div className="mt-5 mb-8">
        <p className="metric-label mb-2">02 · REVIEW REQUIREMENTS</p>
        <h1 className="text-display mb-2">Review case requirements</h1>
        <p className="text-gray-600 max-w-2xl">AI extracted these accessibility requirements from the report. Review and confirm them before evaluating resources.</p>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="metric-card"><p className="metric-label">ACTIVE REQUIREMENTS</p><p className="text-2xl font-bold">{activeRequirements.length}</p></div>
        <div className="metric-card"><p className="metric-label">AI EXTRACTED</p><p className="text-2xl font-bold">{requirements.length} fields</p></div>
        <div className="metric-card"><p className="metric-label">VERSION</p><p className="text-2xl font-bold">{reviewed ? version : version + 1}</p><p className="text-xs text-gray-500">{reviewed ? "Confirmed" : "Pending confirmation"}</p></div>
      </div>

      <div className="card p-5 mb-6 bg-navy-50 border-navy-100">
        <p className="text-sm text-navy-700"><span className="font-semibold">Review gate:</span> the deterministic engine will use the confirmed values below, not the raw AI proposal.</p>
      </div>

      <div className="space-y-4">
        {requirements.map((requirement) => (
          <section key={requirement.field} className="card p-5">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">{requirement.label}</h2>
                <div className="flex flex-wrap gap-2 mt-2 text-xs font-semibold">
                  <span className={`badge ${valueBadgeClass[requirement.final_value]}`}>{requirement.final_value.replaceAll("_", " ").toUpperCase()}</span>
                  <span className="rounded-full bg-gray-100 text-gray-600 px-2.5 py-1">
                    {requirement.source.replaceAll("_", " ").toUpperCase()}
                  </span>
                </div>
                {requirement.source === "human_edited" && (
                  <p className="text-xs text-gray-500 mt-3">Originally extracted as: {requirement.ai_value.replaceAll("_", " ")}</p>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 w-full sm:w-auto">
                {REVIEW_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => updateValue(requirement.field, option.value)}
                    disabled={savingField === requirement.field}
                    className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${requirement.final_value === option.value ? "border-teal-600 bg-teal-50 text-teal-800" : "border-gray-200 text-gray-600 hover:border-gray-400"}`}
                  >
                    {savingField === requirement.field ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : option.label}
                  </button>
                ))}
              </div>
            </div>
          </section>
        ))}
      </div>

      {error && <p className="mt-5 text-sm text-blocked-700">{error}</p>}

      <div className="mt-8 card p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-gray-900">Ready to use the reviewed requirement set?</p>
          <p className="text-sm text-gray-600">{reviewed ? `Requirements confirmed at version ${version}. Edit any field to create a new version.` : `This records the coordinator review and creates requirement version ${version + 1}.`}</p>
        </div>
        <button onClick={confirm} disabled={confirming} className="btn-primary w-full sm:w-auto">
          {confirming ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : <><CheckCircle2 className="w-5 h-5" /> {reviewed ? "Continue to Resource Evaluation" : "Confirm Requirements & Continue"}</>}
        </button>
      </div>

      <p className="mt-5 text-xs text-gray-500"><AlertTriangle className="inline w-3.5 h-3.5 mr-1" />Changing any requirement after evaluation invalidates the previous evaluation.</p>
    </div>
  );
}
