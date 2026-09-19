"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { evaluateResources, EvaluationReport, getResources, Resource } from "@/lib/api";
import { ResourceCard } from "@/components/sahaya/ResourceCard";
import { Loader2 } from "lucide-react";

export default function ResourcesPage() {
  const { id } = useParams() as { id: string };
  const [evaluations, setEvaluations] = useState<EvaluationReport[]>([]);
  const [resources, setResources] = useState<Record<string, Resource>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [evaluationResult, resourceList] = await Promise.all([evaluateResources(id), getResources()]);
        setEvaluations(evaluationResult.evaluations);
        setResources(Object.fromEntries(resourceList.map((resource) => [resource.id, resource])));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="page-container min-h-[50vh] flex flex-col items-center justify-center text-center">
        <Loader2 className="w-10 h-10 animate-spin text-navy-600 mb-6" />
        <h2 className="text-xl font-bold mb-2">Evaluating Resources...</h2>
        <p className="text-gray-500">Checking deterministic constraints against available resources.</p>
      </div>
    );
  }

  // Sort applicable decisions first; NOT APPLICABLE is shown last.
  const sorted = [...evaluations].sort((a, b) => {
    const priority = { "SAFE": 1, "UNKNOWN": 2, "BLOCKED": 3, "NOT_APPLICABLE": 4 };
    return priority[a.status] - priority[b.status];
  });
  const shelters = sorted.filter((report) => resources[report.resource_id]?.type === "shelter");
  const vehicles = sorted.filter((report) => resources[report.resource_id]?.type === "vehicle");
  const safeCount = sorted.filter((report) => report.status === "SAFE").length;
  const unknownCount = sorted.filter((report) => report.status === "UNKNOWN").length;
  const blockedCount = sorted.filter((report) => report.status === "BLOCKED").length;
  const notApplicableCount = sorted.filter((report) => report.status === "NOT_APPLICABLE").length;

  const renderGroup = (title: string, reports: EvaluationReport[], resourceType: string) => (
    reports.length > 0 && (
      <section className="mb-8">
        <h2 className="metric-label border-b border-gray-200 pb-3 mb-3">{title}</h2>
        <div className="space-y-2">
          {reports.map((report) => <ResourceCard key={report.resource_id} report={report} incidentId={id} resourceType={resourceType} />)}
        </div>
      </section>
    )
  );

  return (
    <div className="page-container">
      <div className="mb-8">
        <p className="metric-label mb-2">RESOURCE EVALUATION · CASE {id.slice(0,8).toUpperCase()}</p>
        <h1 className="text-h1 mb-2">Available Resources</h1>
        <p className="text-gray-500">{sorted.length} resources evaluated against applicable case requirements.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <div className="metric-card"><p className="metric-label text-safe-700">SAFE</p><p className="text-2xl font-bold">{safeCount}</p><p className="text-xs text-gray-500">Verified</p></div>
        <div className="metric-card"><p className="metric-label text-unknown-700">UNKNOWN</p><p className="text-2xl font-bold">{unknownCount}</p><p className="text-xs text-gray-500">Check first</p></div>
        <div className="metric-card"><p className="metric-label text-blocked-700">BLOCKED</p><p className="text-2xl font-bold">{blockedCount}</p><p className="text-xs text-gray-500">Conflict found</p></div>
        <div className="metric-card"><p className="metric-label text-gray-600">NOT APPLICABLE</p><p className="text-2xl font-bold">{notApplicableCount}</p><p className="text-xs text-gray-500">Not needed</p></div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-8 text-xs text-gray-600">
        <p><span className="font-semibold text-safe-700">SAFE</span><br />All applicable requirements verified</p>
        <p><span className="font-semibold text-unknown-700">UNKNOWN</span><br />Required capability not verified</p>
        <p><span className="font-semibold text-blocked-700">BLOCKED</span><br />Requirement conflicts with resource</p>
        <p><span className="font-semibold text-gray-600">NOT APPLICABLE</span><br />Resource type is not required</p>
      </div>

      {renderGroup("SHELTERS", shelters, "shelter")}
      {renderGroup("VEHICLES", vehicles, "vehicle")}
    </div>
  );
}
