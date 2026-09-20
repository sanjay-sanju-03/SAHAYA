"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { evaluateRoute, getRouteRecord, RouteObservation, RouteRecord, saveRouteObservation } from "@/lib/api";
import { StatusBadge } from "@/components/sahaya/StatusBadge";

type Choice = "yes" | "no" | "unknown";

function choice(value: boolean | null | undefined): Choice {
  return value === true ? "yes" : value === false ? "no" : "unknown";
}
function bool(value: Choice): boolean | null {
  return value === "yes" ? true : value === "no" ? false : null;
}

const fields: { key: keyof Pick<RouteObservation, "route_exists" | "known_hazard_on_route" | "accessible_for_person">; label: string; yes: string; no: string }[] = [
  { key: "route_exists", label: "Route exists", yes: "YES", no: "NO" },
  { key: "known_hazard_on_route", label: "Known hazard on route", yes: "YES", no: "NO" },
  { key: "accessible_for_person", label: "Accessible for this person", yes: "YES", no: "NO" },
];

export default function RouteVerificationPage() {
  const { id, rid } = useParams() as { id: string; rid: string };
  const router = useRouter();
  const [draft, setDraft] = useState<Record<string, Choice>>({});
  const [source, setSource] = useState("Field inspection");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [record, setRecord] = useState<RouteRecord | null>(null);

  useEffect(() => {
    getRouteRecord(id, rid).then((record) => {
      setRecord(record);
      const observation = record.observation;
      setDraft({
        route_exists: choice(observation?.route_exists),
        known_hazard_on_route: choice(observation?.known_hazard_on_route),
        accessible_for_person: choice(observation?.accessible_for_person),
      });
      setSource(observation?.source || "Field inspection");
      setNotes(observation?.notes || "");
    }).catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load route evidence."));
  }, [id, rid]);

  const save = async () => {
    setSaving(true);
    setMessage("");
    try {
      await saveRouteObservation(id, rid, {
        route_exists: bool(draft.route_exists),
        known_hazard_on_route: bool(draft.known_hazard_on_route),
        accessible_for_person: bool(draft.accessible_for_person),
      }, source, notes);
      await evaluateRoute(id, rid);
      router.replace("/incident/" + id + "/resources/" + rid);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save route evidence.");
    } finally {
      setSaving(false);
    }
  };

  return <main className="page-container max-w-3xl">
    <Link href={"/incident/" + id + "/resources/" + rid} className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to resource evidence</Link>
    <div className="mt-5 mb-7"><p className="metric-label mb-2">ROUTE VERIFICATION</p><h1 className="text-display">Record route evidence</h1><p className="mt-2 text-gray-600">This affects route compatibility only. It never changes the resource compatibility result.</p></div>
    {record?.observation && <section className="card mb-6 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="metric-label">CURRENT ROUTE EVIDENCE</p><h2 className="mt-1 text-xl font-bold">{record.evaluation?.is_current ? "Route evaluation snapshot" : "Route evaluation outdated"}</h2></div>{record.evaluation && <StatusBadge status={record.evaluation.is_current ? record.evaluation.status : "UNKNOWN"} />}</div>
      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <p><span className="font-semibold">Source:</span> {record.observation.source || "Not recorded"}</p>
        <p><span className="font-semibold">Observed:</span> {record.observation.observed_at ? new Date(record.observation.observed_at).toLocaleString() : "Not recorded"}</p>
        <p><span className="font-semibold">Route version:</span> {record.observation.route_version}</p>
        <p><span className="font-semibold">Freshness:</span> {record.evaluation?.route_freshness || "Not evaluated"}</p>
        <p><span className="font-semibold">Requirement version:</span> {record.evaluation?.requirement_version ?? "Not evaluated"}</p>
        <p><span className="font-semibold">Resource version:</span> {record.evaluation?.resource_version ?? "Not evaluated"}</p>
      </div>
      {record.evaluation?.checks && <div className="mt-4 space-y-2 border-t border-gray-100 pt-4 text-sm">{record.evaluation.checks.map((check) => <p key={check.constraint}>{check.status === "SAFE" ? "✓" : check.status === "BLOCKED" ? "✕" : "?"} <span className="font-medium">{check.requirement_label}</span> — {check.reason}</p>)}</div>}
      {record.observation.notes && <p className="mt-4 rounded-lg bg-navy-50 p-3 text-sm text-gray-700"><span className="font-semibold">Observation note:</span> {record.observation.notes}</p>}
    </section>}
    <div className="space-y-4">{fields.map((field) => <section key={field.key} className="card p-5"><h2 className="font-bold">{field.label}</h2><div className="mt-4 grid grid-cols-3 gap-2">{(["yes", "no", "unknown"] as Choice[]).map((value) => <button key={value} type="button" onClick={() => setDraft((current) => ({ ...current, [field.key]: value }))} className={"rounded-lg border px-3 py-2 text-xs font-semibold " + (draft[field.key] === value ? "border-teal-600 bg-teal-50 text-teal-800" : "border-gray-200 text-gray-600")}>{value === "yes" ? field.yes : value === "no" ? field.no : "UNKNOWN"}</button>)}</div></section>)}</div>
    <section className="card p-5 mt-6"><label className="block text-sm font-semibold mb-2">Observation source</label><select value={source} onChange={(event) => setSource(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm"><option>Field inspection</option><option>Coordinator report</option><option>Hazard bulletin</option><option>Other</option></select><label className="block text-sm font-semibold mt-5 mb-2">Notes</label><textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder="Describe the route, hazard, or accessibility evidence..." className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm" /></section>
    {message && <p className="mt-4 text-sm text-blocked-700">{message}</p>}
    <button type="button" onClick={save} disabled={saving} className="btn-primary mt-6">{saving ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />}SAVE ROUTE EVIDENCE</button>
  </main>;
}
