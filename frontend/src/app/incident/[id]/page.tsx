"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getIncident, getMissingInfo, Incident } from "@/lib/api";
import { Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function CaseSummaryPage() {
  const { id } = useParams() as { id: string };
  const [incident, setIncident] = useState<Incident | null>(null);
  const [missing, setMissing] = useState<boolean>(false);
  const [caseNotFound, setCaseNotFound] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const inc = await getIncident(id);
        setIncident(inc);

        // Also check if there's missing information
        const info = await getMissingInfo(id);
        if (!info.complete) {
          setMissing(true);
        }
      } catch (err) {
        if (err instanceof Error && err.message.startsWith("API 404:")) {
          setCaseNotFound(true);
        } else {
          console.error(err);
        }
      }
    }
    load();
  }, [id]);

  if (caseNotFound) {
    return (
      <div className="page-container flex items-center justify-center min-h-[60vh]">
        <div className="card p-8 w-full max-w-lg text-center">
          <AlertTriangle className="w-10 h-10 text-unknown-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-3">This case is no longer available</h1>
          <p className="text-gray-600 mb-6">
            Cases are currently stored only while the backend is running. Create a new case, or use the demo scenario.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/" className="btn-primary">Create New Case</Link>
            <Link href="/incident/demo-001/clarify" className="btn-secondary">Try Demo Scenario</Link>
          </div>
        </div>
      </div>
    );
  }

  if (!incident) {
    return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600"/></div>;
  }

  const p = incident.person;
  // A known "false" is useful case information, but it is not a capability
  // the resource must provide. Keep this list aligned with the rule engine.
  const activeRequirements = [
    p.wheelchair_required === true && { person: "Wheelchair access required", capability: "Wheelchair access" },
    p.stairs_allowed === false && { person: "Step-free access required", capability: "Step-free access" },
    p.accessible_transport_required === true && { person: "Accessible transport required", capability: "Accessible transport" },
    p.caregiver_required === true && { person: "Caregiver support required", capability: "Caregiver support" },
    p.visual_communication_required === true && { person: "Visual communication required", capability: "Visual communication" },
    p.hearing_support_required === true && { person: "Hearing support required", capability: "Hearing support" },
  ].filter((requirement): requirement is { person: string; capability: string } => Boolean(requirement));

  return (
    <div className="page-container">
      <div className="card p-6 sm:p-8 mb-6 border-l-4 border-l-teal-500">
        <div className="flex justify-between items-start gap-4">
          <div>
            <span className="badge badge-high mb-3">HIGH PRIORITY</span>
            <h1 className="text-display capitalize">{incident.incident_type || "Emergency Report"}</h1>
            <p className="text-gray-500 mt-1">Emergency accessibility assessment</p>
          </div>
          <p className="metric-label shrink-0">CASE {incident.id.slice(0, 8).toUpperCase()}</p>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-6">
          <div className="metric-card"><p className="metric-label">ACTIVE REQUIREMENTS</p><p className="text-2xl font-bold">{activeRequirements.length}</p></div>
          <div className="metric-card"><p className="metric-label">RESOURCES</p><p className="text-2xl font-bold">5</p></div>
          <div className="metric-card"><p className="metric-label">STATUS</p><p className="text-sm font-bold text-teal-700">{missing ? "REVIEW" : "READY"}</p></div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h2 className="text-xl font-bold mb-4 uppercase tracking-wider text-gray-500 text-sm">Person</h2>
          <ul className="space-y-3">
            {p.mobility === "wheelchair" && <li className="flex gap-2 items-center"><span className="text-xl">♿</span> Wheelchair user</li>}
            {activeRequirements.filter((requirement) => !(requirement.person === "Wheelchair access required" && p.mobility === "wheelchair")).map((requirement) => (
              <li key={requirement.person} className="flex gap-2 items-center"><CheckCircle2 className="w-5 h-5 text-safe-600 shrink-0" />{requirement.person}</li>
            ))}
            {activeRequirements.length === 0 && <li className="text-gray-500">No active accessibility requirements identified yet.</li>}
          </ul>
        </div>

        <div className="card p-6">
          <h2 className="text-xl font-bold mb-4 uppercase tracking-wider text-gray-500 text-sm">Required Capabilities</h2>
          <ul className="space-y-3">
            {activeRequirements.map((requirement) => (
              <li key={requirement.capability} className="flex gap-2 items-start">
                <CheckCircle2 className="w-5 h-5 text-safe-600 shrink-0 mt-0.5" />
                <span>{requirement.capability}</span>
              </li>
            ))}
            {activeRequirements.length === 0 && (
              <li className="flex gap-2 items-start">
                <span className="text-gray-500">No resource capabilities are required from this report.</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {incident.needs_manual_review && (
        <div className="card p-6 border-unknown-400 bg-unknown-50 mb-8">
          <div className="flex items-center gap-2 text-unknown-700 font-bold mb-2">
            <AlertTriangle className="w-5 h-5" />
            ACCESSIBILITY REQUIREMENTS NOT CONFIRMED
          </div>
          <p className="text-unknown-700">
            We couldn&apos;t reliably identify accessibility requirements from this report. Please review and clarify them before evaluating resources.
          </p>
        </div>
      )}

      {missing ? (
        <div className="card p-6 border-unknown-400 bg-unknown-50">
          <div className="flex items-center gap-2 text-unknown-700 font-bold mb-2">
            <AlertTriangle className="w-5 h-5" />
            CRITICAL INFORMATION MISSING
          </div>
          <p className="mb-4 text-unknown-700">We need more information before evaluating resources safely.</p>
          <Link href={`/incident/${id}/clarify`} className="btn-primary w-full sm:w-auto">
            Provide Clarification
          </Link>
        </div>
      ) : (
        <div className="text-center">
          <Link href={`/incident/${id}/resources`} className="btn-primary w-full sm:w-auto text-lg py-4 px-8">
            Evaluate Resources
          </Link>
        </div>
      )}
    </div>
  );
}
