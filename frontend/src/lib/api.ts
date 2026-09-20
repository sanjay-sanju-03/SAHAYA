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
  | "review_required"
  | "ready_for_evaluation"
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
  latitude: number | null;
  longitude: number | null;
  person: PersonProfile;
  ai_person: PersonProfile;
  requirements_review_started: boolean;
  requirements_reviewed: boolean;
  requirement_version: number;
  requirements_reviewed_at: string | null;
  requirements_reviewed_by: string | null;
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
  latitude: number | null;
  longitude: number | null;
  status: string;
  capacity: number | null;
  available_capacity: number | null;
  current_occupancy: number | null;
  accessible_capacity: number | null;
  accessible_occupied: number | null;
  caregiver_capacity: number | null;
  caregiver_occupied: number | null;
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
  capability_verifications: Record<string, {
    value: boolean | null;
    verification_status: string;
    verified_at: string | null;
    verified_by: string | null;
    source: string | null;
    notes: string | null;
  }>;
  resource_version: number;
  is_demo: boolean;
}

export interface EvaluationCheck {
  constraint: string;
  status: "SAFE" | "UNKNOWN" | "BLOCKED";
  requirement_label: string;
  resource_label: string;
  evidence_label: string;
  reason: string;
  required_value: string | null;
  resource_value: string | null;
  capability: string | null;
  required: boolean;
  person_source: string | null;
  person_value: string | null;
  resource_source: string | null;
  resource_verified_at: string | null;
  resource_freshness: "CURRENT" | "AGING" | "STALE" | "NEVER_VERIFIED" | null;
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
  requirement_version: number;
  resource_version: number;
  is_current: boolean;
  outdated_reason: string | null;
  evaluated_at: string;
}

export interface ClarificationQuestion {
  key: string;
  question: string;
  question_ml: string;
  options: string[];
  priority: number;
}

export type RequirementValue = "required" | "not_required" | "unknown";

export interface RequirementReviewItem {
  field: string;
  label: string;
  ai_value: RequirementValue;
  final_value: RequirementValue;
  source: "ai_extraction" | "human_confirmed" | "human_edited";
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

export type CapabilityValue = "yes" | "no" | "unknown";

export interface ResourceCapacityUpdate {
  total_capacity?: number | null;
  current_occupancy?: number | null;
  accessible_capacity?: number | null;
  accessible_occupied?: number | null;
  caregiver_capacity?: number | null;
  caregiver_occupied?: number | null;
}

export interface ResourceVerificationResponse {
  resource: Resource;
  resource_version: number;
  freshness: Record<string, {
    status: "CURRENT" | "AGING" | "STALE" | "NEVER_VERIFIED";
    verification: Resource["capability_verifications"][string] | null;
  }>;
}

export interface ResourceImageObservations {
  stairs_visible: boolean | null;
  ramp_visible: boolean | null;
  step_free_access_visible: boolean | null;
  wheelchair_accessibility_verified: boolean | null;
  evidence: string[];
}

export interface CasePerson {
  id: string;
  incident_id: string;
  display_name: string;
  original_text: string | null;
  ai_person: PersonProfile;
  person: PersonProfile;
  requirement_version: number;
  requirements_reviewed: boolean;
  reviewed_requirement_fields: string[];
}

export interface GroupEvaluation {
  resource_id: string;
  resource_name: string;
  resource_version: number;
  group_status: EvaluationStatus;
  capacity_status: "SAFE" | "UNKNOWN" | "BLOCKED";
  capacity_required: number;
  capacity_available: number | null;
  accessible_spaces_required: number;
  accessible_spaces_available: number | null;
  caregiver_spaces_required: number;
  caregiver_spaces_available: number | null;
  is_current: boolean;
  outdated_reason: string | null;
  people: { person_id: string; display_name: string; requirement_version: number; result: EvaluationReport }[];
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

export async function getRequirements(id: string): Promise<{
  incident_id: string;
  reviewed: boolean;
  requirement_version: number;
  requirements: RequirementReviewItem[];
}> {
  return api(`/api/incidents/${id}/requirements`);
}

export async function updateRequirement(
  incidentId: string,
  field: string,
  value: RequirementValue,
  coordinatorId = "coord-demo-001",
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${incidentId}/requirements/${field}`, {
    method: "PATCH",
    body: JSON.stringify({ value, coordinator_id: coordinatorId }),
  });
}

export async function confirmRequirements(
  incidentId: string,
  coordinatorId = "coord-demo-001",
): Promise<Incident> {
  return api<Incident>(`/api/incidents/${incidentId}/requirements/confirm`, {
    method: "POST",
    body: JSON.stringify({ coordinator_id: coordinatorId }),
  });
}

export async function getPeople(incidentId: string): Promise<{ people: CasePerson[] }> {
  return api(`/api/incidents/${incidentId}/people`);
}

export async function getPerson(incidentId: string, personId: string): Promise<CasePerson> {
  return api(`/api/incidents/${incidentId}/people/${personId}`);
}

export async function addPerson(incidentId: string, displayName: string, text: string): Promise<CasePerson> {
  return api(`/api/incidents/${incidentId}/people`, { method: "POST", body: JSON.stringify({ display_name: displayName, text }) });
}

export async function evaluateGroup(incidentId: string): Promise<{ evaluations: GroupEvaluation[] }> {
  return api(`/api/incidents/${incidentId}/group-evaluate`, { method: "POST" });
}

export async function getPersonRequirements(incidentId: string, personId: string): Promise<{ reviewed: boolean; requirement_version: number; requirements: RequirementReviewItem[] }> {
  return api(`/api/incidents/${incidentId}/people/${personId}/requirements`);
}

export async function updatePersonRequirement(incidentId: string, personId: string, field: string, value: RequirementValue): Promise<CasePerson> {
  return api(`/api/incidents/${incidentId}/people/${personId}/requirements/${field}`, { method: "PATCH", body: JSON.stringify({ value, coordinator_id: "coord-demo-001" }) });
}

export async function confirmPersonRequirements(incidentId: string, personId: string): Promise<CasePerson> {
  return api(`/api/incidents/${incidentId}/people/${personId}/requirements/confirm`, { method: "POST", body: JSON.stringify({ coordinator_id: "coord-demo-001" }) });
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

export async function getResourceVerification(id: string): Promise<ResourceVerificationResponse> {
  return api(`/api/resources/${id}/verification`);
}

export async function verifyResource(
  id: string,
  capabilities: Record<string, CapabilityValue>,
  source: string,
  notes: string,
  capacity?: ResourceCapacityUpdate,
  coordinatorId = "coord-demo-001",
): Promise<Resource> {
  return api<Resource>(`/api/resources/${id}/verify`, {
    method: "POST",
    body: JSON.stringify({
      capabilities,
      capacity,
      coordinator_id: coordinatorId,
      source,
      notes: notes || null,
    }),
  });
}

export async function observeResourceImage(id: string, file: File, inspectionNote: string): Promise<ResourceImageObservations> {
  const form = new FormData();
  form.append("file", file);
  form.append("inspection_note", inspectionNote);
  const res = await fetch(`${BASE}/api/resources/${id}/image-observations`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail || "Image observations are unavailable.");
  }
  const body = await res.json() as { observations: ResourceImageObservations };
  return body.observations;
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
    const detail = await res.json().catch(() => null) as { detail?: string } | null;
    return {
      success: false,
      transcript: "",
      message: detail?.detail || "Voice transcription is unavailable. Please type your report or check the backend connection.",
    };
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<{ status: string; ai_available: boolean }> {
  return api("/health");
}
