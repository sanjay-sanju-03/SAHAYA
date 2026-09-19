/**
 * SAHAYA — Typed API client
 * All communication with the FastAPI backend goes through this module.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types (mirror Pydantic models)
// ---------------------------------------------------------------------------

export type IncidentStatus =
  | "received"
  | "analyzing"
  | "needs_clarification"
  | "evaluated"
  | "confirmed"
  | "manual_override_authorized"
  | "closed";

export type EvaluationStatus = "SAFE" | "UNKNOWN" | "BLOCKED" | "NOT_APPLICABLE";

export interface PersonProfile {
  age_group: string;
  mobility: string;
  wheelchair_required: boolean | null;
  stairs_allowed: boolean | null;
  ramp_usable: boolean | null;
  caregiver_required: boolean | null;
  accessible_transport_required: boolean | null;
  visual_communication_required: boolean | null;
  hearing_support_required: boolean | null;
  language: string;
  notes: string | null;
}

export interface Incident {
  id: string;
  status: IncidentStatus;
  incident_type: string | null;
  urgency: string | null;
  location_text: string | null;
  person: PersonProfile;
  original_text: string | null;
  extraction_confidence: number | null;
  needs_manual_review: boolean;
  confirmed_resource_id: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  manual_override_resource_id: string | null;
  manual_override_by: string | null;
  manual_override_at: string | null;
  manual_override_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Resource {
  id: string;
  type: string;
  name: string;
  location_text: string | null;
  status: string;
  capacity: number | null;
  available_capacity: number | null;
  capabilities: {
    ground_floor: boolean | null;
    stairs_required: boolean | null;
    ramp: boolean | null;
    wheelchair_access: boolean | null;
    accessible_toilet: boolean | null;
    wheelchair_transport: boolean | null;
    caregiver_support: boolean | null;
    visual_communication_support: boolean | null;
    hearing_support: boolean | null;
    last_verified_at: string | null;
    verified_by: string | null;
  };
  is_demo: boolean;
}

export interface EvaluationCheck {
  constraint: string;
  status: "SAFE" | "UNKNOWN" | "BLOCKED";
  requirement_label: string;
  resource_label: string;
  evidence_label: string;
  reason: string;
}

export interface EvaluationReport {
  id: string;
  incident_id: string;
  resource_id: string;
  resource_name: string;
  status: EvaluationStatus;
  status_label: string;
  checks: EvaluationCheck[];
  total_checks: number;
  passed_checks: number;
  unknown_checks: number;
  blocked_checks: number;
  evaluated_at: string;
}

export interface ClarificationQuestion {
  key: string;
  question: string;
  question_ml: string;
  options: string[];
  priority: number;
}

export interface AuditLog {
  id: string;
  incident_id: string;
  actor_type: "ai" | "system" | "human";
  action: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Incidents
// ---------------------------------------------------------------------------

export async function createIncident(text: string, imageUrl?: string): Promise<Incident> {
  return api<Incident>("/api/incidents", {
    method: "POST",
    body: JSON.stringify({ text, image_url: imageUrl ?? null }),
  });
}

export async function getIncident(id: string): Promise<Incident> {
  return api<Incident>(`/api/incidents/${id}`);
}

export async function getMissingInfo(id: string): Promise<{
  complete: boolean;
  question: ClarificationQuestion | null;
}> {
  return api(`/api/incidents/${id}/missing-information`);
}

export async function answerClarification(
  id: string,
  questionKey: string,
  answer: string
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${id}/answers`, {
    method: "POST",
    body: JSON.stringify({ question_key: questionKey, answer }),
  });
}

export async function evaluateResources(id: string): Promise<{
  incident_id: string;
  evaluations: EvaluationReport[];
}> {
  return api(`/api/incidents/${id}/evaluate`, { method: "POST" });
}

export async function confirmAssignment(
  incidentId: string,
  resourceId: string,
  coordinatorId: string,
  notes?: string
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${incidentId}/confirm`, {
    method: "POST",
    body: JSON.stringify({
      resource_id: resourceId,
      coordinator_id: coordinatorId,
      notes: notes ?? null,
    }),
  });
}

export async function requestManualOverride(
  incidentId: string,
  resourceId: string,
  coordinatorId: string,
  reason?: string
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${incidentId}/override-request`, {
    method: "POST",
    body: JSON.stringify({
      resource_id: resourceId,
      coordinator_id: coordinatorId,
      reason: reason ?? null,
    }),
  });
}

export async function authorizeManualOverride(
  incidentId: string,
  resourceId: string,
  coordinatorId: string,
  reason: string,
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${incidentId}/override-authorize`, {
    method: "POST",
    body: JSON.stringify({
      resource_id: resourceId,
      coordinator_id: coordinatorId,
      reason,
    }),
  });
}

export async function getAuditLog(id: string): Promise<{
  incident_id: string;
  logs: AuditLog[];
}> {
  return api(`/api/incidents/${id}/audit`);
}

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------

export async function getResources(): Promise<Resource[]> {
  return api<Resource[]>("/api/resources");
}

export async function getResource(id: string): Promise<Resource> {
  return api<Resource>(`/api/resources/${id}`);
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

export async function getEvaluationsForIncident(incidentId: string): Promise<{
  incident_id: string;
  evaluations: EvaluationReport[];
}> {
  return api(`/api/evaluations/incident/${incidentId}`);
}

// ---------------------------------------------------------------------------
// Audio
// ---------------------------------------------------------------------------

export async function transcribeAudio(
  audioBlob: Blob
): Promise<{ success: boolean; transcript: string; message: string }> {
  const form = new FormData();
  form.append("file", audioBlob, "audio.webm");
  const res = await fetch(`${BASE}/api/audio/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    return { success: false, transcript: "", message: "Transcription service unavailable." };
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<{ status: string; ai_available: boolean }> {
  return api("/health");
}
