import Link from "next/link";
import { RouteRecord } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

export function RouteCompatibilityPanel({ incidentId, resourceId, record }: { incidentId: string; resourceId: string; record: RouteRecord | null }) {
  const evaluation = record?.evaluation;
  const observation = record?.observation;
  const status = evaluation?.is_current ? evaluation.status : "UNKNOWN";
  const reason = evaluation?.is_current
    ? evaluation.checks.find((check) => check.status !== "SAFE")?.reason || "All current route checks passed."
    : evaluation?.outdated_reason || "No current route observation is available.";
  const routePath = "/incident/" + incidentId + "/resources/" + resourceId + "/route";

  return <section className="mt-8 rounded-2xl border border-navy-100 bg-navy-50/40 p-5">
    <p className="metric-label">ROUTE COMPATIBILITY</p>
    <div className="mt-2 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-bold">{status}</h2><p className="mt-1 text-sm text-gray-600">{reason}</p></div><StatusBadge status={status} /></div>
    {observation && <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3"><p><span className="font-semibold">Source:</span> {observation.source || "Not recorded"}</p><p><span className="font-semibold">Observed:</span> {observation.observed_at ? new Date(observation.observed_at).toLocaleString() : "Not recorded"}</p><p><span className="font-semibold">Route version:</span> {observation.route_version}</p></div>}
    {evaluation?.is_current && <div className="mt-4 space-y-1 text-sm">{evaluation.checks.filter((check) => check.constraint !== "route_freshness").map((check) => <p key={check.constraint}>{check.status === "SAFE" ? "✓" : check.status === "BLOCKED" ? "✕" : "?"} {check.requirement_label}</p>)}</div>}
    <div className="mt-5 flex flex-wrap gap-2"><Link href={routePath} className="btn-secondary">{evaluation?.is_current ? "VIEW ROUTE EVIDENCE" : "VERIFY ROUTE"}</Link>{evaluation?.is_current && <Link href={routePath} className="btn-primary">UPDATE ROUTE</Link>}</div>
  </section>;
}
