"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, CircleHelp, Loader2, XCircle } from "lucide-react";
import { EvaluationReport, getEvaluationsForIncident } from "@/lib/api";
import { StatusBadge } from "@/components/sahaya/StatusBadge";

function Mark({ status }: { status?: string }) {
  if (status === "SAFE") return <CheckCircle2 className="mx-auto w-5 h-5 text-safe-600" />;
  if (status === "UNKNOWN") return <CircleHelp className="mx-auto w-5 h-5 text-unknown-600" />;
  if (status === "BLOCKED") return <XCircle className="mx-auto w-5 h-5 text-blocked-600" />;
  return <span className="text-gray-400">—</span>;
}

export default function ResourceComparisonPage() {
  const { id } = useParams() as { id: string };
  const params = useSearchParams();
  const requested = useMemo(() => (params.get("resources") || "").split(",").filter(Boolean).slice(0, 4), [params]);
  const [reports, setReports] = useState<EvaluationReport[]>([]);

  useEffect(() => { getEvaluationsForIncident(id).then((result) => setReports(result.evaluations)).catch(console.error); }, [id]);
  if (!reports.length) return <div className="page-container min-h-[50vh] flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-navy-600" /></div>;

  const selected = reports.filter((report) => requested.includes(report.resource_id));
  const constraints = [...new Set(selected.flatMap((report) => report.checks.map((check) => check.constraint)))];

  return (
    <div className="page-container">
      <Link href={`/incident/${id}/resources`} className="inline-flex items-center text-gray-500 hover:text-navy-600 mb-6 font-medium"><ArrowLeft className="w-4 h-4 mr-1" />Back to Resources</Link>
      <p className="metric-label mb-2">EVIDENCE-BASED COMPARISON · CASE {id.slice(0, 8).toUpperCase()}</p>
      <h1 className="text-h1 mb-2">Resource Comparison</h1>
      <p className="text-gray-500 mb-8">This view compares verified evidence. It does not rank or choose a resource.</p>

      {selected.length < 2 ? <div className="card p-6">Select two to four resources from the resource list to compare their evidence.</div> : (
        <div className="overflow-x-auto card">
          <table className="min-w-full text-sm text-center">
            <thead className="bg-gray-50">
              <tr><th className="p-4 text-left min-w-48">Applicable requirement</th>{selected.map((report) => <th key={report.resource_id} className="p-4 min-w-40"><p className="font-bold">{report.resource_name}</p><div className="mt-2 flex justify-center"><StatusBadge status={report.status} /></div></th>)}</tr>
            </thead>
            <tbody>
              {constraints.map((constraint) => <tr key={constraint} className="border-t border-gray-200"><th className="p-4 text-left capitalize">{constraint.replaceAll("_", " ")}</th>{selected.map((report) => { const check = report.checks.find((item) => item.constraint === constraint); return <td key={report.resource_id} className="p-4"><Mark status={check?.status} /><p className="mt-2 text-xs text-gray-600">{check?.resource_label || "Not applicable"}</p></td>; })}</tr>)}
              <tr className="border-t-2 border-gray-300 bg-gray-50"><th className="p-4 text-left">Decision</th>{selected.map((report) => <td key={report.resource_id} className="p-4"><StatusBadge status={report.status} /><Link href={`/incident/${id}/resources/${report.resource_id}`} className="block text-xs text-teal-700 font-semibold mt-3">VIEW WHY</Link></td>)}</tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
