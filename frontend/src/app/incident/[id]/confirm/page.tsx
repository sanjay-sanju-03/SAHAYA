"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { confirmAssignment, getEvaluationsForIncident, getResource, Resource, EvaluationReport } from "@/lib/api";
import { ConfirmationDialog } from "@/components/sahaya/ConfirmationDialog";

export default function ConfirmPage() {
  const { id } = useParams() as { id: string };
  const searchParams = useSearchParams();
  const rid = searchParams.get("rid");
  const router = useRouter();

  const [resource, setResource] = useState<Resource | null>(null);
  const [report, setReport] = useState<EvaluationReport | null>(null);

  useEffect(() => {
    if (!rid) {
      router.push(`/incident/${id}/resources`);
      return;
    }
    Promise.all([getResource(rid), getEvaluationsForIncident(id)])
      .then(([loadedResource, evaluations]) => {
        setResource(loadedResource);
        setReport(evaluations.evaluations.find((item) => item.resource_id === rid) ?? null);
      })
      .catch(console.error);
  }, [id, rid, router]);

  const handleConfirm = async () => {
    if (!rid) return;
    // Hardcoded coordinator ID for demo purposes
    await confirmAssignment(id, rid, "coord-demo-001");
    router.push(`/incident/${id}/audit`);
  };

  const handleCancel = () => {
    router.back();
  };

  if (!resource) return null;

  const verifiedRequirements = report?.checks
    .filter((check) => check.status === "SAFE")
    .map((check) => check.requirement_label) ?? [];

  return (
    <ConfirmationDialog
      resourceName={resource.name}
      verifiedRequirements={verifiedRequirements}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  );
}
