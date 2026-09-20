"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2, MapPinned } from "lucide-react";
import { evaluateResources, EvaluationReport, getIncident, getResources, Incident, Resource } from "@/lib/api";
import { OperationsMap } from "@/components/sahaya/OperationsMap";
import { StatusBadge } from "@/components/sahaya/StatusBadge";

const statusCopy: Record<EvaluationReport["status"], string> = {
  SAFE: "Verified compatible",
  UNKNOWN: "Verification required",
  BLOCKED: "Conflict found",
  NOT_APPLICABLE: "Not required for this case",
};

export default function OperationsMapPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [reports, setReports] = useState<EvaluationReport[]>([]);
  const [resources, setResources] = useState<Record<string, Resource>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getIncident(id), evaluateResources(id), getResources()])
      .then(([caseData, evaluationData, resourceData]) => {
        setIncident(caseData);
        setReports(evaluationData.evaluations);
        setResources(Object.fromEntries(resourceData.map((resource) => [resource.id, resource])));
      })
      .catch((err) => {
        if (err instanceof Error && err.message.startsWith("API 409:")) {
          router.replace("/incident/" + id + "/review");
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to load the operations map.");
      });
  }, [id, router]);

  const selectResource = useCallback((resourceId: string) => setSelected(resourceId), []);
  const markers = useMemo(() => reports.flatMap((report) => {
    const resource = resources[report.resource_id];
    return resource?.latitude !== null && resource?.longitude !== null && resource?.latitude !== undefined && resource?.longitude !== undefined
      ? [{ id: resource.id, name: resource.name, latitude: resource.latitude, longitude: resource.longitude, status: report.status }]
      : [];
  }), [reports, resources]);
  const selectedReport = reports.find((report) => report.resource_id === selected) ?? null;

  if (error) return <div className="page-container py-12"><p className="text-blocked-700">{error}</p></div>;
  if (!incident) return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600" /></div>;
  const hasIncidentPoint = incident.latitude !== null && incident.longitude !== null;

  return <main className="page-container">
    <Link href={"/incident/" + id + "/resources"} className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to Resource Evaluation</Link>
    <div className="mt-5 mb-6">
      <p className="metric-label mb-2">OPERATIONS MAP · CASE {id.slice(0, 8).toUpperCase()}</p>
      <h1 className="text-display">Current resource state</h1>
      <p className="mt-2 text-gray-600">A visual view of current resource compatibility. It does not calculate routes or dispatch decisions.</p>
    </div>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-5">
      {Object.entries(statusCopy).map(([status, label]) => <div key={status} className="rounded-xl border border-gray-200 bg-white p-3"><StatusBadge status={status as EvaluationReport["status"]} /><p className="mt-2 text-xs text-gray-500">{label}</p></div>)}
    </div>
    {!hasIncidentPoint && <div className="mb-5 flex items-start gap-2 rounded-xl border border-unknown-200 bg-unknown-50 p-4 text-sm text-unknown-800"><AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />Incident location has not been geocoded. Resource positions are still shown.</div>}
    <OperationsMap
      incident={hasIncidentPoint ? { latitude: incident.latitude!, longitude: incident.longitude!, label: incident.location_text || "Incident location" } : undefined}
      resources={markers}
      onSelect={selectResource}
    />
    <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_360px]">
      <section className="card p-5"><div className="flex items-center gap-2"><MapPinned className="h-5 w-5 text-teal-700" /><h2 className="font-bold">Resource markers</h2></div><p className="mt-2 text-sm text-gray-600">Select a marker to inspect its deterministic evidence or its live Resource Passport.</p></section>
      {selectedReport ? <aside className="card p-5"><p className="metric-label">SELECTED RESOURCE</p><h2 className="mt-1 text-lg font-bold">{selectedReport.resource_name}</h2><div className="mt-3"><StatusBadge status={selectedReport.status} /></div><p className="mt-3 text-sm text-gray-600">{statusCopy[selectedReport.status]}</p><div className="mt-5 flex flex-col gap-2"><Link className="btn-primary text-center" href={"/incident/" + id + "/resources/" + selectedReport.resource_id}>VIEW EVIDENCE</Link><Link className="btn-secondary text-center" href={"/resource/" + selectedReport.resource_id}>RESOURCE PASSPORT</Link></div></aside> : <aside className="card p-5 text-sm text-gray-500">Select any resource marker to open its existing evidence and passport.</aside>}
    </div>
  </main>;
}
