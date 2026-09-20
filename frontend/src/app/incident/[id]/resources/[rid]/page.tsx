"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authorizeManualOverride, getEvaluationsForIncident, getRouteRecord, EvaluationReport, RouteRecord } from "@/lib/api";
import { EvidencePanel } from "@/components/sahaya/EvidencePanel";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ManualOverrideDialog } from "@/components/sahaya/ManualOverrideDialog";
import { RouteCompatibilityPanel } from "@/components/sahaya/RouteCompatibilityPanel";

export default function ResourceDetailPage() {
  const { id, rid } = useParams() as { id: string; rid: string };
  const router = useRouter();
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [routeRecord, setRouteRecord] = useState<RouteRecord | null>(null);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideAuthorized, setOverrideAuthorized] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [res, route] = await Promise.all([getEvaluationsForIncident(id), getRouteRecord(id, rid)]);
        const match = res.evaluations.find(e => e.resource_id === rid);
        if (match) setReport(match);
        setRouteRecord(route);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, [id, rid]);

  if (!report) {
    return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600"/></div>;
  }

  const isSafe = report.status === "SAFE";
  const isUnknown = report.status === "UNKNOWN";
  const isNotApplicable = report.status === "NOT_APPLICABLE";
  const authorizeOverride = async (reason: string) => {
    await authorizeManualOverride(id, rid, "coord-demo-001", reason);
    setOverrideReason(reason);
    setOverrideAuthorized(true);
    setOverrideOpen(false);
  };
  const blockingChecks = report.checks.filter((check) => check.status === "BLOCKED");

  return (
    <div className="page-container">
      <Link href={`/incident/${id}/resources`} className="inline-flex items-center text-gray-500 hover:text-navy-600 mb-6 font-medium">
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back to Resources
      </Link>

      <div className="card p-6 md:p-8">
        <h1 className="text-display mb-2">{report.resource_name}</h1>

        <EvidencePanel report={report} />
        <RouteCompatibilityPanel incidentId={id} resourceId={rid} record={routeRecord} />

        <div className="mt-10 pt-8 border-t flex flex-col sm:flex-row gap-4 items-center justify-between">
          {isSafe ? (
            <>
              <div className="text-sm">
                <p className="font-semibold text-safe-700">Human decision: Pending coordinator confirmation</p>
                <p className="text-gray-500">AI interpreted the report; deterministic rules verified the requirements.</p>
              </div>
              <button
                onClick={() => router.push(`/incident/${id}/confirm?rid=${rid}`)}
                className="btn-confirm w-full sm:w-auto"
              >
                CONFIRM ASSIGNMENT
              </button>
            </>
          ) : isUnknown ? (
            <>
              <div>
                <p className="text-unknown-700 text-sm font-medium">UNKNOWN — We do not have enough verified information yet.</p>
                <p className="text-sm text-gray-500 mt-1">Verify the resource record or resolve missing case information before assigning it.</p>
              </div>
              <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                <Link href={`/resource/${rid}`} className="btn-secondary w-full sm:w-auto">RESOURCE PASSPORT</Link>
                <Link href={`/resource/${rid}/verify`} className="btn-primary w-full sm:w-auto">VERIFY RESOURCE</Link>
                <Link href={`/incident/${id}/clarify`} className="btn-secondary w-full sm:w-auto">RESOLVE CASE INFO</Link>
              </div>
            </>
          ) : isNotApplicable ? (
            <p className="w-full text-sm font-medium text-gray-600">NOT APPLICABLE — This resource type is not required for the current case, so no compatibility decision was made.</p>
          ) : overrideAuthorized ? (
            <div className="w-full rounded-xl border border-unknown-200 bg-unknown-50 p-5">
              <p className="font-bold text-unknown-800">⚠ MANUAL OVERRIDE AUTHORIZED</p>
              <p className="mt-2 text-sm text-gray-700"><span className="font-semibold">{report.resource_name}</span> · Original rule decision: BLOCKED</p>
              <p className="mt-2 text-sm text-gray-700"><span className="font-semibold">Reason:</span> {overrideReason}</p>
              <p className="mt-2 text-sm text-gray-600">Override authorized by coordinator. The deterministic evaluation remains BLOCKED.</p>
              <div className="mt-4 flex flex-col sm:flex-row gap-3">
                <Link href={`/incident/${id}/audit`} className="btn-primary">VIEW AUDIT LOG</Link>
                <Link href={`/incident/${id}/resources`} className="btn-secondary">BACK TO RESOURCES</Link>
              </div>
            </div>
          ) : (
            <>
              <div>
                <p className="text-blocked-700 text-sm font-medium">BLOCKED — We know this resource conflicts with a critical requirement.</p>
              </div>
              <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                <button disabled className="btn-primary">ASSIGNMENT BLOCKED</button>
                <button onClick={() => setOverrideOpen(true)} className="btn-secondary">REQUEST MANUAL OVERRIDE</button>
              </div>
            </>
          )}
        </div>
      </div>
      {overrideOpen && (
        <ManualOverrideDialog
          resourceName={report.resource_name}
          blockingChecks={blockingChecks}
          onAuthorize={authorizeOverride}
          onCancel={() => setOverrideOpen(false)}
        />
      )}
    </div>
  );
}
