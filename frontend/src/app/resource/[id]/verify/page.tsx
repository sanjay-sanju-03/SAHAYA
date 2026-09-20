"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, ImagePlus, Loader2 } from "lucide-react";
import {
  CapabilityValue,
  getResourceVerification,
  observeResourceImage,
  ResourceImageObservations,
  ResourceCapacityUpdate,
  ResourceVerificationResponse,
  verifyResource,
} from "@/lib/api";

const CAPABILITIES = [
  { field: "wheelchair_access", label: "Wheelchair access", types: ["shelter"] },
  { field: "stairs_required", label: "Step-free access", types: ["shelter"], inverse: true },
  { field: "ramp", label: "Accessible ramp", types: ["shelter"] },
  { field: "caregiver_support", label: "Caregiver support", types: ["shelter"] },
  { field: "visual_communication_support", label: "Visual communication", types: ["shelter"] },
  { field: "hearing_support", label: "Hearing support", types: ["shelter"] },
  { field: "wheelchair_transport", label: "Wheelchair transport", types: ["vehicle"] },
];

const freshnessClass: Record<string, string> = {
  CURRENT: "badge-safe",
  AGING: "badge-unknown",
  STALE: "badge-blocked",
  NEVER_VERIFIED: "badge-not-applicable",
};

const CAPACITY_FIELDS: { field: keyof ResourceCapacityUpdate; label: string }[] = [
  { field: "total_capacity", label: "Total capacity" },
  { field: "current_occupancy", label: "Current occupancy" },
  { field: "accessible_capacity", label: "Accessible spaces" },
  { field: "accessible_occupied", label: "Accessible spaces occupied" },
  { field: "caregiver_capacity", label: "Caregiver spaces" },
  { field: "caregiver_occupied", label: "Caregiver spaces occupied" },
];

function toValue(value: boolean | null | undefined, inverse = false): CapabilityValue {
  if (value === null || value === undefined) return "unknown";
  const normalized = inverse ? !value : value;
  return normalized ? "yes" : "no";
}

function toStoredValue(value: CapabilityValue, inverse = false): CapabilityValue {
  if (!inverse || value === "unknown") return value;
  return value === "yes" ? "no" : "yes";
}

export default function ResourceVerificationPage() {
  const { id } = useParams() as { id: string };
  const [data, setData] = useState<ResourceVerificationResponse | null>(null);
  const [draft, setDraft] = useState<Record<string, CapabilityValue>>({});
  const [capacityDraft, setCapacityDraft] = useState<Record<string, string>>({});
  const [source, setSource] = useState("Coordinator inspection");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [observations, setObservations] = useState<ResourceImageObservations | null>(null);
  const [observing, setObserving] = useState(false);
  const [inspectionNote, setInspectionNote] = useState("Inspect this resource entrance for visible accessibility features. Identify stairs, ramps, handrails, and step-free access. Report only what is visibly observable. Do not assume wheelchair accessibility from the image.");
  const imageInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getResourceVerification(id)
      .then((response) => {
        setData(response);
        setDraft(Object.fromEntries(CAPABILITIES.map((capability) => [
          capability.field,
          toValue(response.resource.capabilities[capability.field as keyof typeof response.resource.capabilities] as boolean | null, capability.inverse),
        ])));
        setCapacityDraft({
          total_capacity: response.resource.capacity?.toString() ?? "",
          current_occupancy: response.resource.current_occupancy?.toString() ?? "",
          accessible_capacity: response.resource.accessible_capacity?.toString() ?? "",
          accessible_occupied: response.resource.accessible_occupied?.toString() ?? "",
          caregiver_capacity: response.resource.caregiver_capacity?.toString() ?? "",
          caregiver_occupied: response.resource.caregiver_occupied?.toString() ?? "",
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load the resource."));
  }, [id]);

  if (!data) {
    return <div className="p-10 text-center">{error || <Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600" />}</div>;
  }

  const visibleCapabilities = CAPABILITIES.filter((capability) => capability.types.includes(data.resource.type));
  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updates = Object.fromEntries(visibleCapabilities.map((capability) => [
        capability.field,
        toStoredValue(draft[capability.field], capability.inverse),
      ]));
      const capacity: ResourceCapacityUpdate | undefined = data.resource.type === "shelter" ? Object.fromEntries(
        CAPACITY_FIELDS.map(({ field }) => [field, capacityDraft[field] === "" ? null : Number(capacityDraft[field])]),
      ) : undefined;
      const resource = await verifyResource(id, updates, source, notes, capacity);
      const refreshed = await getResourceVerification(id);
      setData(refreshed);
      setSaved(true);
      setDraft(Object.fromEntries(visibleCapabilities.map((capability) => [
        capability.field,
        toValue(resource.capabilities[capability.field as keyof typeof resource.capabilities] as boolean | null, capability.inverse),
      ])));
      setCapacityDraft({
        total_capacity: resource.capacity?.toString() ?? "",
        current_occupancy: resource.current_occupancy?.toString() ?? "",
        accessible_capacity: resource.accessible_capacity?.toString() ?? "",
        accessible_occupied: resource.accessible_occupied?.toString() ?? "",
        caregiver_capacity: resource.caregiver_capacity?.toString() ?? "",
        caregiver_occupied: resource.caregiver_occupied?.toString() ?? "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save verification.");
    } finally {
      setSaving(false);
    }
  };

  const observeImage = async (event: ChangeEvent<HTMLInputElement>) => {
    const image = event.target.files?.[0];
    if (!image) return;
    setObserving(true);
    setError("");
    try {
      setObservations(await observeResourceImage(id, image, inspectionNote));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image observations are unavailable.");
    } finally {
      setObserving(false);
      event.target.value = "";
    }
  };

  const applyObservations = () => {
    if (!observations) return;
    setDraft((current) => ({
      ...current,
      ...(observations.stairs_visible === true ? { stairs_required: "yes" } : {}),
      ...(observations.step_free_access_visible === true ? { stairs_required: "no" } : {}),
      ...(observations.ramp_visible === true ? { ramp: "yes" } : {}),
      ...(observations.wheelchair_accessibility_verified === true ? { wheelchair_access: "yes" } : {}),
    }));
    setSource("Image review");
    setSaved(false);
  };

  return (
    <div className="page-container max-w-3xl">
      <Link href={`/resource/${id}`} className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to Resource Passport</Link>
      <div className="mt-5 mb-8">
        <p className="metric-label mb-2">RESOURCE VERIFICATION</p>
        <h1 className="text-display mb-2">{data.resource.name}</h1>
        <p className="text-gray-600 capitalize">{data.resource.type} · Resource version {data.resource_version}</p>
      </div>

      <div className="space-y-4">
        {visibleCapabilities.map((capability) => {
          const status = data.freshness[capability.field]?.status ?? "NEVER_VERIFIED";
          const verification = data.freshness[capability.field]?.verification;
          return (
            <section key={capability.field} className="card p-5">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <h2 className="font-bold">{capability.label}</h2>
                  <span className={`badge ${freshnessClass[status]} mt-2`}>{status.replaceAll("_", " ")}</span>
                  {verification?.verified_at ? (
                    <div className="text-xs text-gray-500 mt-2 space-y-1">
                      <p>Last verified {new Date(verification.verified_at).toLocaleString()} · {verification.verified_by}</p>
                      <p>Source: {verification.source || "Not recorded"}</p>
                    </div>
                  ) : <p className="text-xs text-gray-500 mt-2">No verified record yet</p>}
                </div>
                <div className="grid grid-cols-3 gap-2 w-full sm:w-auto">
                  {(["yes", "no", "unknown"] as CapabilityValue[]).map((value) => (
                    <button key={value} type="button" onClick={() => { setDraft((current) => ({ ...current, [capability.field]: value })); setSaved(false); }} className={`rounded-lg border px-3 py-2 text-xs font-semibold ${draft[capability.field] === value ? "border-teal-600 bg-teal-50 text-teal-800" : "border-gray-200 text-gray-600 hover:border-gray-400"}`}>{value.toUpperCase()}</button>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {data.resource.type === "shelter" && <section className="card p-5 mt-6">
        <p className="metric-label mb-1">ACCESSIBILITY CAPACITY</p>
        <h2 className="font-bold">Capacity by support need</h2>
        <p className="text-sm text-gray-600 mt-1">General capacity never substitutes for an accessible or caregiver space.</p>
        <div className="grid sm:grid-cols-2 gap-4 mt-5">
          {CAPACITY_FIELDS.map(({ field, label }) => <label key={field} className="text-sm font-semibold text-gray-700">{label}
            <input min="0" type="number" value={capacityDraft[field] ?? ""} onChange={(event) => { setCapacityDraft((current) => ({ ...current, [field]: event.target.value })); setSaved(false); }} placeholder="Unknown" className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white p-3 text-sm font-normal" />
          </label>)}
        </div>
      </section>}

      <section className="card p-5 mt-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div><p className="metric-label mb-1">RESOURCE IMAGE</p><h2 className="font-bold">Add resource image</h2><p className="text-sm text-gray-600 mt-1">Images create observations for review; they never create a decision directly.</p></div>
          <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={observeImage} />
          <button type="button" onClick={() => imageInput.current?.click()} disabled={observing} className="btn-secondary">{observing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImagePlus className="w-4 h-4" />}{observing ? "OBSERVING..." : "ADD RESOURCE IMAGE"}</button>
        </div>
        <label className="block text-sm font-semibold mt-4 mb-2">Inspection focus</label>
        <textarea value={inspectionNote} onChange={(event) => setInspectionNote(event.target.value)} rows={3} className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm" />
        {observations && (
          <div className="mt-5 rounded-xl border border-gray-200 p-4 bg-gray-50">
            <p className="metric-label mb-3">IMAGE EVIDENCE · REVIEW REQUIRED</p>
            <div className="space-y-2 text-sm">
              <p>{observations.stairs_visible === true ? "✓ Stairs visible" : observations.stairs_visible === false ? "✓ No stairs visible" : "? Stairs not verified"}</p>
              <p>{observations.ramp_visible === true ? "✓ Accessible ramp visible" : "? Accessible ramp not verified"}</p>
              <p>{observations.step_free_access_visible === true ? "✓ Step-free entrance visible" : "? Step-free access not verified"}</p>
              <p>{observations.wheelchair_accessibility_verified === true ? "✓ Wheelchair accessibility visibly verified" : "? Wheelchair accessibility cannot be confirmed from this image"}</p>
            </div>
            {observations.evidence.length > 0 && <p className="text-xs text-gray-600 mt-3">Evidence: {observations.evidence.join(" · ")}</p>}
            <div className="mt-4 flex flex-wrap gap-2"><button type="button" onClick={applyObservations} className="btn-primary">APPLY TO VERIFICATION FORM</button><button type="button" onClick={() => setObservations(null)} className="btn-secondary">MARK UNKNOWN</button></div>
          </div>
        )}
      </section>

      <section className="card p-5 mt-6">
        <label className="block text-sm font-semibold mb-2">Verification source</label>
        <select value={source} onChange={(event) => setSource(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm">
          <option>Coordinator inspection</option>
          <option>Resource manager</option>
          <option>Field inspection</option>
          <option>Image review</option>
          <option>Other</option>
        </select>
        <label className="block text-sm font-semibold mt-5 mb-2">Notes</label>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder="Add verification context or limitations..." className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm" />
      </section>

      {error && <p className="mt-4 text-sm text-blocked-700">{error}</p>}
      {saved && <p className="mt-4 text-sm font-semibold text-safe-700"><CheckCircle2 className="inline w-4 h-4 mr-1" />Verification saved. Affected evaluations must be re-run.</p>}
      <button onClick={save} disabled={saving} className="btn-primary mt-6 w-full sm:w-auto">{saving ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Save Verification"}</button>
    </div>
  );
}
