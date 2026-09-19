import { EvaluationReport } from "@/lib/api";
import { ConstraintCard } from "./ConstraintCard";
import { StatusBadge } from "./StatusBadge";

interface EvidencePanelProps {
  report: EvaluationReport;
}

export function EvidencePanel({ report }: EvidencePanelProps) {
  return (
    <div className="mt-8">
      <h2 className="text-xl font-bold mb-4">Evidence and rule evaluation</h2>
      <div className="grid md:grid-cols-[0.8fr_1.6fr] border border-gray-200 rounded-2xl overflow-hidden mb-5">
        <div className={`p-6 ${report.status === "SAFE" ? "bg-safe-50" : report.status === "UNKNOWN" ? "bg-unknown-50" : report.status === "NOT_APPLICABLE" ? "bg-gray-50" : "bg-blocked-50"}`}>
          <p className="metric-label mb-4">RULE ENGINE DECISION</p>
          <StatusBadge status={report.status} />
          <h3 className="text-2xl font-bold mt-4 mb-2">{report.status}</h3>
          <p className="text-sm text-gray-700 mb-5">
            {report.status === "BLOCKED" ? "A required capability conflicts with this resource." : report.status === "UNKNOWN" ? "A required capability could not be verified." : report.status === "NOT_APPLICABLE" ? "This resource type is not required for the current case." : "All required capabilities are verified for this resource."}
          </p>
          <div className="text-sm text-gray-600 space-y-1"><p>{report.passed_checks} passed</p><p>{report.unknown_checks} unknown</p><p>{report.blocked_checks} blocked</p></div>
        </div>
        <div className="overflow-x-auto bg-white">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs tracking-wider">
            <tr>
              <th className="p-3">Requirement</th>
              <th className="p-3">Person</th>
              <th className="p-3">Resource</th>
              <th className="p-3">Result</th>
            </tr>
          </thead>
          <tbody>
            {report.checks.map((check, idx) => (
              <tr key={`${check.constraint}-${idx}`} className="border-t border-gray-200">
                <td className="p-3 font-medium">{check.constraint.replaceAll("_", " ")}</td>
                <td className="p-3">{check.requirement_label}</td>
                <td className="p-3">{check.resource_label}</td>
                <td className="p-3"><StatusBadge status={check.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700">Check details</h3>
        {report.checks.map((check, idx) => (
          <ConstraintCard key={`${check.constraint}-${idx}`} check={check} />
        ))}
      </div>
    </div>
  );
}
