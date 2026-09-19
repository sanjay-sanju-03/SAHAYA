import { EvaluationReport } from "@/lib/api";
import { CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

const COPY = {
  SAFE: ["WHY SAFE?", "All applicable requirements were verified."],
  UNKNOWN: ["WHY UNKNOWN?", "A required capability is not currently verified."],
  BLOCKED: ["WHY BLOCKED?", "A required capability conflicts with this resource."],
  NOT_APPLICABLE: ["WHY NOT APPLICABLE?", "This resource type is not required for the current case."],
} as const;

function ResultIcon({ status }: { status: "SAFE" | "UNKNOWN" | "BLOCKED" }) {
  if (status === "SAFE") return <CheckCircle2 className="w-4 h-4 text-safe-600" />;
  if (status === "UNKNOWN") return <CircleHelp className="w-4 h-4 text-unknown-600" />;
  return <XCircle className="w-4 h-4 text-blocked-600" />;
}

export function WhyDecisionPanel({ report }: { report: EvaluationReport }) {
  const [title, description] = COPY[report.status];
  const isNotApplicable = report.status === "NOT_APPLICABLE";

  return (
    <section className="mt-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="metric-label">EXPLAINABLE DECISION</p>
          <h2 className="text-xl font-bold mt-1">{title}</h2>
          <p className="text-sm text-gray-600 mt-1">{description}</p>
        </div>
        <StatusBadge status={report.status} />
      </div>

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 mb-4 text-sm grid sm:grid-cols-3 gap-3">
        <p><span className="font-semibold block">Requirement version</span>{report.requirement_version}</p>
        <p><span className="font-semibold block">Resource version</span>{report.resource_version}</p>
        <p><span className="font-semibold block">Evaluation snapshot</span>{new Date(report.evaluated_at).toLocaleString()}</p>
      </div>

      {!report.is_current && (
        <div className="rounded-xl border border-unknown-200 bg-unknown-50 p-4 mb-4 text-sm text-unknown-900">
          <p className="font-bold">⚠ EVALUATION OUTDATED</p>
          <p className="mt-1">{report.outdated_reason || "The evidence changed after this evaluation. Re-evaluate before making a decision."}</p>
        </div>
      )}

      {isNotApplicable ? (
        <div className="card p-5 text-sm text-gray-700">
          <p className="font-semibold">No compatibility checks were run.</p>
          <p className="mt-1">The vehicle was not evaluated because accessible transport is not required for this case.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {report.checks.map((check, index) => (
            <article key={`${check.constraint}-${index}`} className="card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold">{check.constraint.replaceAll("_", " ")}</h3>
                  <p className="text-sm text-gray-600 mt-1">{check.reason}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0"><ResultIcon status={check.status} /><span className="text-xs font-bold">{check.status}</span></div>
              </div>
              <div className="grid md:grid-cols-2 gap-3 mt-4 text-sm">
                <div className="rounded-lg bg-teal-50 p-3">
                  <p className="metric-label mb-1">PERSON REQUIREMENT</p>
                  <p className="font-semibold">{check.person_value || check.requirement_label}</p>
                  <p className="text-xs text-gray-600 mt-2">Source: {check.person_source || "Human-reviewed requirements"}</p>
                  <p className="text-xs text-gray-600">Version: {report.requirement_version}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="metric-label mb-1">RESOURCE CAPABILITY</p>
                  <p className="font-semibold">{check.resource_label}</p>
                  <p className="text-xs text-gray-600 mt-2">Source: {check.resource_source || check.evidence_label}</p>
                  <p className="text-xs text-gray-600">Freshness: {check.resource_freshness?.replaceAll("_", " ") || "Not applicable"}</p>
                  {check.resource_verified_at && <p className="text-xs text-gray-600">Verified: {new Date(check.resource_verified_at).toLocaleString()}</p>}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
