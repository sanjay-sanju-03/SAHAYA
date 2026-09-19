"""
SAHAYA — Incidents API router.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.ai.clarifier import ClarificationQuestion, apply_answer, get_next_question
from app.ai.extractor import IncidentExtraction, extractor
from app.engine.constraint_engine import evaluate_all
from app.models.audit import ActorType, AuditAction, AuditLog
from app.models.incident import (
    AnswerClarificationRequest,
    AuthorizeManualOverrideRequest,
    ConfirmAssignmentRequest,
    CreateIncidentRequest,
    Incident,
    IncidentStatus,
    ManualOverrideRequest,
)
from app.store.memory import (
    append_audit,
    clear_evaluations,
    get_audit,
    get_evaluations,
    get_incident,
    list_resources,
    save_evaluations,
    save_incident,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _audit(incident_id: str, actor: ActorType, action: AuditAction, description: str, meta: dict = {}) -> None:
    append_audit(AuditLog(
        incident_id=incident_id,
        actor_type=actor,
        action=action,
        description=description,
        metadata=meta,
    ))


def _apply_extraction(incident: Incident, extraction: IncidentExtraction) -> None:
    """Map validated AI output to the incident without logging report details."""
    incident.person = extractor.to_person_profile(extraction)
    incident.constraints = extractor.to_constraints(extraction)
    incident.incident_type = extraction.incident_type
    incident.urgency = extraction.urgency
    incident.location_text = extraction.location_text
    incident.extraction_confidence = extraction.confidence
    incident.needs_manual_review = extraction.needs_manual_review



# ---------------------------------------------------------------------------
# POST /api/incidents — Create a new incident
# ---------------------------------------------------------------------------

@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED)
async def create_incident(body: CreateIncidentRequest):
    incident = Incident(
        original_text=body.text,
        image_url=body.image_url,
        status=IncidentStatus.analyzing,
    )
    save_incident(incident)
    _audit(incident.id, ActorType.system, AuditAction.incident_created,
           "Incident report received.")

    # Trigger async AI extraction
    try:
        _audit(incident.id, ActorType.ai, AuditAction.analysis_started,
               "AI analysis started.")
        extraction = await extractor.extract(body.text, body.image_url)
        _apply_extraction(incident, extraction)
        incident.status = IncidentStatus.needs_clarification
        incident.updated_at = datetime.utcnow()
        save_incident(incident)
        _audit(incident.id, ActorType.ai, AuditAction.analysis_completed,
               "AI extraction completed.",
               {"confidence": extraction.confidence,
                "needs_manual_review": extraction.needs_manual_review,
                "failure_reason": extraction.failure_reason})
        if extraction.needs_manual_review:
            _audit(incident.id, ActorType.system, AuditAction.manual_review_flagged,
                   "Accessibility requirements could not be reliably identified. Coordinator review is required.")
    except Exception as e:
        incident.needs_manual_review = True
        incident.status = IncidentStatus.needs_clarification
        save_incident(incident)
        _audit(incident.id, ActorType.ai, AuditAction.analysis_failed,
               f"AI analysis failed: {str(e)}")

    return incident


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}
# ---------------------------------------------------------------------------

@router.get("/{incident_id}", response_model=Incident)
async def get_incident_by_id(incident_id: str):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found.")
    return incident


# ---------------------------------------------------------------------------
# POST /api/incidents/{id}/analyze — Re-run AI extraction
# ---------------------------------------------------------------------------

@router.post("/{incident_id}/analyze", response_model=Incident)
async def analyze_incident(incident_id: str):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    incident.status = IncidentStatus.analyzing
    incident.updated_at = datetime.utcnow()
    clear_evaluations(incident_id)
    save_incident(incident)
    _audit(incident_id, ActorType.ai, AuditAction.analysis_started, "Re-analysis started.")

    extraction = await extractor.extract(incident.original_text or "", incident.image_url)
    _apply_extraction(incident, extraction)
    incident.status = IncidentStatus.needs_clarification
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    _audit(incident_id, ActorType.ai, AuditAction.analysis_completed,
           "AI re-analysis completed.",
           {"confidence": extraction.confidence,
            "needs_manual_review": extraction.needs_manual_review,
            "failure_reason": extraction.failure_reason})
    if extraction.needs_manual_review:
        _audit(incident_id, ActorType.system, AuditAction.manual_review_flagged,
               "Accessibility requirements could not be reliably identified. Coordinator review is required.")
    return incident


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}/missing-information
# ---------------------------------------------------------------------------

@router.get("/{incident_id}/missing-information")
async def missing_information(incident_id: str) -> dict:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # A coordinator may answer NOT_SURE. Keep that field null so evaluation
    # remains conservative, but do not trap the coordinator on the same prompt.
    answered_keys = {
        log.metadata.get("key")
        for log in get_audit(incident_id)
        if log.action == AuditAction.clarification_answered and log.metadata.get("key")
    }
    question = get_next_question(incident.person, incident.location_text, answered_keys)
    if question is None:
        return {"complete": True, "question": None}
    return {"complete": False, "question": question.model_dump()}


# ---------------------------------------------------------------------------
# POST /api/incidents/{id}/answers — Submit a clarification answer
# ---------------------------------------------------------------------------

@router.post("/{incident_id}/answers", response_model=Incident)
async def answer_clarification(incident_id: str, body: AnswerClarificationRequest):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # Special case: location is stored on incident, not on person
    if body.question_key == "location_text":
        incident.location_text = body.answer
    else:
        incident.person = apply_answer(incident.person, body.question_key, body.answer)

    incident.updated_at = datetime.utcnow()
    clear_evaluations(incident_id)
    save_incident(incident)

    _audit(incident_id, ActorType.human, AuditAction.clarification_answered,
           f"Clarification answered: {body.question_key} = {body.answer}",
           {"key": body.question_key, "answer": body.answer})
    return incident


# ---------------------------------------------------------------------------
# POST /api/incidents/{id}/evaluate — Run constraint engine against all resources
# ---------------------------------------------------------------------------

@router.post("/{incident_id}/evaluate")
async def evaluate_resources(incident_id: str) -> dict:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # Evaluation is idempotent for an unchanged case. Revisiting the resource
    # screen must not add another set of audit events for the same decision.
    existing_reports = get_evaluations(incident_id)
    if existing_reports:
        return {
            "incident_id": incident_id,
            "evaluations": [report.model_dump() for report in existing_reports],
        }

    resources = list_resources()
    reports = evaluate_all(incident.person, resources, incident_id)

    save_evaluations(incident_id, reports)
    incident.status = IncidentStatus.evaluated
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    _audit(incident_id, ActorType.system, AuditAction.resources_evaluated,
           f"Constraint engine evaluated {len(resources)} resources.",
            {"total": len(resources),
            "safe": sum(1 for r in reports if r.status.value == "SAFE"),
            "unknown": sum(1 for r in reports if r.status.value == "UNKNOWN"),
            "blocked": sum(1 for r in reports if r.status.value == "BLOCKED"),
            "not_applicable": sum(1 for r in reports if r.status.value == "NOT_APPLICABLE")})
    for report in reports:
        _audit(
            incident_id,
            ActorType.system,
            AuditAction.resource_evaluated,
            f"{report.resource_name} evaluated. Result: {report.status.value}",
            {"resource_id": report.resource_id, "resource_name": report.resource_name, "result": report.status.value},
        )

    return {"incident_id": incident_id, "evaluations": [r.model_dump() for r in reports]}


# ---------------------------------------------------------------------------
# POST /api/incidents/{id}/confirm — Human confirmation
# ---------------------------------------------------------------------------

@router.post("/{incident_id}/confirm", response_model=Incident)
async def confirm_assignment(incident_id: str, body: ConfirmAssignmentRequest):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    if incident.status not in (IncidentStatus.evaluated, IncidentStatus.needs_clarification):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm incident in status {incident.status!r}. Must be evaluated first.",
        )

    report = next(
        (item for item in get_evaluations(incident_id) if item.resource_id == body.resource_id),
        None,
    )
    if report is None or report.status.value != "SAFE":
        raise HTTPException(
            status_code=400,
            detail="Only a SAFE resource with a completed evaluation can be confirmed.",
        )

    incident.confirmed_resource_id = body.resource_id
    incident.confirmed_by = body.coordinator_id
    incident.confirmed_at = datetime.utcnow()
    incident.status = IncidentStatus.confirmed
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    _audit(incident_id, ActorType.human, AuditAction.assignment_confirmed,
           f"Assignment confirmed by coordinator. Resource: {body.resource_id}",
           {"resource_id": body.resource_id, "coordinator_id": body.coordinator_id,
            "notes": body.notes})
    return incident


@router.post("/{incident_id}/override-request", response_model=Incident)
async def request_manual_override(incident_id: str, body: ManualOverrideRequest):
    """Record a coordinator request; it never confirms a blocked assignment."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    report = next(
        (item for item in get_evaluations(incident_id) if item.resource_id == body.resource_id),
        None,
    )
    if report is None or report.status.value != "BLOCKED":
        raise HTTPException(status_code=400, detail="Manual override requests apply only to BLOCKED resources.")

    _audit(
        incident_id,
        ActorType.human,
        AuditAction.manual_override_requested,
        f"Manual override requested for {report.resource_name}. Assignment remains blocked pending authorization.",
        {"resource_id": body.resource_id, "coordinator_id": body.coordinator_id, "reason": body.reason},
    )
    return incident


@router.post("/{incident_id}/override-authorize", response_model=Incident)
async def authorize_manual_override(incident_id: str, body: AuthorizeManualOverrideRequest):
    """Authorize a documented exception while retaining the BLOCKED rule verdict."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")

    report = next(
        (item for item in get_evaluations(incident_id) if item.resource_id == body.resource_id),
        None,
    )
    if report is None or report.status.value != "BLOCKED":
        raise HTTPException(status_code=400, detail="Manual overrides can only authorize a completed BLOCKED evaluation.")

    if (
        incident.status == IncidentStatus.manual_override_authorized
        and incident.manual_override_resource_id == body.resource_id
    ):
        return incident

    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="An override reason is required.")

    blocked_requirements = [
        {
            "constraint": check.constraint,
            "requirement_label": check.requirement_label,
            "resource_label": check.resource_label,
            "reason": check.reason,
        }
        for check in report.checks
        if check.status.value == "BLOCKED"
    ]
    metadata = {
        "resource_id": report.resource_id,
        "resource_name": report.resource_name,
        "original_decision": "BLOCKED",
        "blocking_requirements": blocked_requirements,
        "override_reason": reason,
        "coordinator_id": body.coordinator_id,
    }

    _audit(
        incident_id,
        ActorType.human,
        AuditAction.manual_override_requested,
        f"Manual override requested for {report.resource_name}. Original rule decision remains BLOCKED.",
        metadata,
    )

    incident.manual_override_resource_id = report.resource_id
    incident.manual_override_by = body.coordinator_id
    incident.manual_override_at = datetime.utcnow()
    incident.manual_override_reason = reason
    incident.status = IncidentStatus.manual_override_authorized
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    _audit(
        incident_id,
        ActorType.human,
        AuditAction.manual_override_authorized,
        (
            "Manual override authorized by coordinator.\n"
            f"Resource: {report.resource_name}\n"
            "Original decision: BLOCKED\n"
            f"Reason: {reason}\n"
            "The deterministic evaluation remains BLOCKED."
        ),
        metadata,
    )
    return incident


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}/audit
# ---------------------------------------------------------------------------

@router.get("/{incident_id}/audit")
async def get_audit_log(incident_id: str) -> dict:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    logs = get_audit(incident_id)
    return {"incident_id": incident_id, "logs": [l.model_dump() for l in logs]}
