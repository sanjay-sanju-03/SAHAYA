"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { CheckCircle2, ClipboardCheck, Clock3, Loader2, MapPin, ShieldCheck } from "lucide-react";
import { getResourceVerification, ResourceVerificationResponse } from "@/lib/api";

const freshnessClass: Record<string, string> = {
  CURRENT: "badge-safe",
  AGING: "badge-unknown",
  STALE: "badge-blocked",
  NEVER_VERIFIED: "badge-not-applicable",
};

function capabilityLabel(field: string) {
  return field.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function ResourcePassportPage() {
  const { id } = useParams() as { id: string };
  const [data, setData] = useState<ResourceVerificationResponse | null>(null);
  const [error, setError] = useState("");
  const passportUrl = `${process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"}/resource/${id}`;

  useEffect(() => {
    getResourceVerification(id)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load this resource."));
  }, [id]);

  if (!data) return <div className="p-10 text-center">{error || <Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600" />}</div>;

  const resource = data.resource;
  const recordedCapabilities = Object.entries(resource.capabilities).filter(([field]) => !["last_verified_at", "verified_by"].includes(field));
  const capacityRows = resource.type === "shelter" ? [
    ["Total places", resource.capacity, resource.current_occupancy, "occupied"],
    ["Accessible spaces", resource.accessible_capacity, resource.accessible_occupied, "occupied"],
    ["Caregiver spaces", resource.caregiver_capacity, resource.caregiver_occupied, "occupied"],
  ] : [["Available places", resource.capacity, resource.current_occupancy, "occupied"]];

  return <main className="page-container max-w-4xl">
    <Link href="/" className="text-sm font-medium text-gray-500 hover:text-navy-600">← Back to SAHAYA</Link>
    <section className="card mt-5 overflow-hidden">
      <div className="bg-navy-900 px-6 py-5 text-white"><p className="metric-label text-teal-200">SAHAYA RESOURCE PASSPORT</p><h1 className="text-3xl font-bold mt-1">{resource.name}</h1><p className="mt-2 text-sm text-navy-100 capitalize">{resource.type} · Resource ID: {resource.id}</p></div>
      <div className="grid gap-6 p-6 md:grid-cols-[1fr_auto]">
        <div className="space-y-3"><p className="flex items-center gap-2 text-sm text-gray-600"><MapPin className="h-4 w-4" />{resource.location_text || "Location not recorded"}</p><p className="flex items-center gap-2 text-sm text-gray-600"><ShieldCheck className="h-4 w-4" />Resource version {data.resource_version} · Live verification record</p><Link href={`/resource/${id}/verify`} className="btn-primary mt-2 inline-flex"><ClipboardCheck className="h-4 w-4" />VERIFY THIS RESOURCE</Link></div>
        <div className="rounded-xl border border-gray-200 bg-white p-3 text-center"><QRCodeSVG value={passportUrl} size={136} level="M" includeMargin /><p className="mt-2 text-xs font-semibold text-gray-600">SCAN FOR LIVE PASSPORT</p></div>
      </div>
    </section>

    <section className="card mt-5 p-6"><p className="metric-label">CURRENT CAPACITY</p><div className="mt-4 grid gap-3 sm:grid-cols-3">{capacityRows.map(([label, total, occupied, suffix]) => <div key={label as string} className="rounded-xl bg-gray-50 p-4"><p className="text-xs font-semibold text-gray-500">{label}</p><p className="mt-1 text-xl font-bold">{total ?? "Unknown"}</p><p className="text-sm text-gray-600">{occupied ?? "Unknown"} {suffix as string}</p></div>)}</div><p className="mt-4 flex gap-2 text-sm text-gray-600"><Clock3 className="h-4 w-4 shrink-0" />General capacity does not substitute for accessible or caregiver capacity.</p></section>

    <section className="card mt-5 p-6"><p className="metric-label">VERIFICATION STATUS</p><div className="mt-4 divide-y divide-gray-100">{recordedCapabilities.map(([field, value]) => { const state = data.freshness[field]?.status ?? "NEVER_VERIFIED"; const record = data.freshness[field]?.verification; return <div key={field} className="flex items-center justify-between gap-4 py-3"><div><p className="font-semibold">{capabilityLabel(field)}</p><p className="text-xs text-gray-500 mt-1">{record?.verified_at ? `Verified by ${record.verified_by || "Coordinator"} · ${new Date(record.verified_at).toLocaleString()}` : "No verified record"}</p></div><div className="text-right"><p className="text-sm font-semibold">{value === true ? "YES" : value === false ? "NO" : "UNKNOWN"}</p><span className={`badge mt-1 ${freshnessClass[state]}`}>{state.replaceAll("_", " ")}</span></div></div>; })}</div></section>

    <p className="mt-5 flex items-center gap-2 text-sm text-gray-500"><CheckCircle2 className="h-4 w-4 text-teal-600" />This passport reads the current resource record. It does not store a duplicate snapshot in the QR code.</p>
  </main>;
}
