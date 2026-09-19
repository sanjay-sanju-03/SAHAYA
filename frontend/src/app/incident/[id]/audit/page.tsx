"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAuditLog, getIncident, AuditLog, Incident } from "@/lib/api";
import { AuditTimeline } from "@/components/sahaya/AuditTimeline";
import { Loader2 } from "lucide-react";
import Link from "next/link";

export default function AuditPage() {
  const { id } = useParams() as { id: string };
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [inc, aud] = await Promise.all([
          getIncident(id),
          getAuditLog(id)
        ]);
        setIncident(inc);
        setLogs(aud.logs);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading || !incident) {
    return <div className="p-10 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-navy-600"/></div>;
  }

  const isManualOverride = incident.status === "manual_override_authorized";

  return (
    <div className="page-container">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <span className={`badge ${isManualOverride ? "badge-unknown" : "badge-safe"} mb-2`}>
            {isManualOverride ? "MANUAL OVERRIDE AUTHORIZED" : "CONFIRMED"}
          </span>
          <h1 className="text-display">Case #{id.slice(0,8)}</h1>
          {isManualOverride && <p className="mt-2 text-sm text-gray-600">Original rule decision remains BLOCKED; the exception is recorded below.</p>}
        </div>
        <Link href="/" className="btn-secondary">
          Start New Case
        </Link>
      </div>

      <AuditTimeline logs={logs} />
    </div>
  );
}
