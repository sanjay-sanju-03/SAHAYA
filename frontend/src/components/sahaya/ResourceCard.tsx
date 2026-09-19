import Link from "next/link";
import { EvaluationReport } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { CheckCircle2, ChevronRight, CircleHelp, XCircle } from "lucide-react";

interface ResourceCardProps {
  report: EvaluationReport;
  incidentId: string;
  resourceType: string;
}

export function ResourceCard({ report, incidentId, resourceType }: ResourceCardProps) {
  const summary = report.status === "SAFE"
    ? "All applicable requirements verified"
    : report.status === "UNKNOWN"
    ? "Verification required"
    : report.status === "NOT_APPLICABLE"
    ? "This resource type is not required for the current case"
    : `${report.blocked_checks} critical conflict${report.blocked_checks === 1 ? "" : "s"}`;
  const formatConstraint = (constraint: string) =>
    constraint.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const blockedRequirement = report.checks.find((check) => check.status === "BLOCKED");
  const transportNotRequired = report.status === "NOT_APPLICABLE" && resourceType === "vehicle";

  return (
    <Link href={`/incident/${incidentId}/resources/${report.resource_id}`} className="block text-inherit no-underline">
      <div className={`card card-hover p-5 mb-4 flex items-center justify-between gap-4 ${report.status === "SAFE" ? "border-safe-300 bg-safe-50/30" : report.status === "NOT_APPLICABLE" ? "border-gray-200 bg-gray-50/50" : ""}`}>
        <div className="min-w-0">
          <p className="metric-label mb-1">{resourceType.toUpperCase()}</p>
          <h3 className="text-lg font-bold mb-2">{report.resource_name}</h3>
          {transportNotRequired && (
            <p className="mb-3 text-xs text-gray-500">Transport accessibility: Not required for this case</p>
          )}
          <div className="flex items-center gap-3 mb-3">
            <StatusBadge status={report.status} />
            <span className={`text-sm ${report.status === "BLOCKED" ? "font-semibold text-blocked-700" : "text-gray-500"}`}>{summary}</span>
          </div>
          <div className="space-y-1 text-xs">
            {report.checks.map((check) => (
              <div key={check.constraint} className="flex items-center gap-1.5 text-gray-700">
                {check.status === "SAFE" ? <CheckCircle2 className="w-3.5 h-3.5 text-safe-600" /> : check.status === "UNKNOWN" ? <CircleHelp className="w-3.5 h-3.5 text-unknown-600" /> : <XCircle className="w-3.5 h-3.5 text-blocked-600" />}
                <span>{formatConstraint(check.constraint)}</span>
              </div>
            ))}
          </div>
          {report.status === "NOT_APPLICABLE" ? (
            <p className="mt-3 text-xs font-semibold text-gray-500">No compatibility checks run</p>
          ) : (
            <p className={`mt-3 text-xs font-semibold ${report.status === "SAFE" ? "text-safe-700" : "text-gray-500"}`}>
              {report.passed_checks} / {report.total_checks} applicable requirement{report.total_checks === 1 ? "" : "s"} verified
            </p>
          )}
          {blockedRequirement && (
            <p className="mt-2 text-xs font-semibold text-blocked-700">
              {formatConstraint(blockedRequirement.constraint)} conflicts with this resource.
            </p>
          )}
        </div>
        <div className="text-teal-600 shrink-0 flex items-center gap-1 text-xs font-bold">
          <span>VIEW WHY</span>
          <ChevronRight className="w-6 h-6" />
        </div>
      </div>
    </Link>
  );
}
