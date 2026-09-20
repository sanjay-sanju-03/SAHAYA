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
    ConfirmRequirementsRequest,
    CreateIncidentRequest,
    Incident,
    IncidentStatus,
    ManualOverrideRequest,
    RequirementUpdateRequest,
)
from app.models.resource import freshness_status, resource_for_evaluation
from app.store.memory import (
    append_audit,
    clear_evaluations,
    get_audit,
    get_evaluations,
    get_incident,
    get_resource,
    invalidate_route_evaluations_for_incident,
    list_resources,
    save_evaluations,
    save_incident,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


REQUIREMENTS: dict[str, str] = {
    "wheelchair_required": "Wheelchair access",
    "stairs_allowed": "Step-free access",
    "accessible_transport_required": "Accessible transport",
    "caregiver_required": "Caregiver support",
    "visual_communication_required": "Visual communication",
    "hearing_support_required": "Hearing support",
}

CHECK_CAPABILITIES: dict[str, str] = {
    "wheelchair_access": "wheelchair_access",
    "stairs": "stairs_required",
    "ramp": "ramp",
    "wheelchair_transport": "wheelchair_transport",
    "caregiver_support": "caregiver_support",
    "visual_communication": "visual_communication_support",
    "hearing_support": "hearing_support",
}


def _attach_evidence_metadata(report, resource) -> None:
    """Persist the exact reviewed and verified evidence used by a report."""
    for check in report.checks:
        capability = CHECK_CAPABILITIES.get(check.constraint)
        check.capability = capability
        check.person_source = "Human-reviewed requirements"
        check.person_value = check.requirement_label
        if not capability:
            check.resource_source = "Resource record"
            continue

        verification = resource.capability_verifications.get(capability)
        check.resource_source = (
            verification.source
            if verification and verification.source
            else resource.capabilities.verified_by or "Resource record"
        )
        check.resource_verified_at = (
            verification.verified_at
            if verification else resource.capabilities.last_verified_at
        )
        check.resource_freshness = freshness_status(resource, capability).value


def _to_review_value(field: str, value: Optional[bool]) -> str:
    """Convert stored booleans into the human-facing requirement tri-state."""
    if value is None:
        return "unknown"
    # `stairs_allowed=False` means step-free access is required.
    if field == "stairs_allowed":
        return "required" if value is False else "not_required"
    return "required" if value is True else "not_required"


def _from_review_value(field: str, value: str) -> Optional[bool]:
    if value == "unknown":
        return None
    if field == "stairs_allowed":
        return value != "required"
    return value == "required"


def _requirements_payload(incident: Incident) -> list[dict]:
    return [
        {
            "field": field,
            "label": label,
            "ai_value": _to_review_value(field, getattr(incident.ai_person, field)),
            "final_value": _to_review_value(field, getattr(incident.person, field)),
            "source": (
                "human_edited"
                if getattr(incident.ai_person, field) != getattr(incident.person, field)
                else "human_confirmed"
                if field in incident.reviewed_requirement_fields
                else "ai_extraction"
            ),
            "reviewed": field in incident.reviewed_requirement_fields,
        }
        for field, label in REQUIREMENTS.items()
    ]


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
    incident.ai_person = extractor.to_person_profile(extraction)
    incident.person = incident.ai_person.model_copy(deep=True)
    incident.constraints = extractor.to_constraints(extraction)
    incident.incident_type = extraction.incident_type
    incident.urgency = extraction.urgency
    incident.location_text = extraction.location_text
    incident.extraction_confidence = extraction.confidence
    incident.needs_manual_review = extraction.needs_manual_review
    incident.requirements_review_started = False
    incident.requirements_reviewed = False
    incident.requirements_reviewed_at = None
    incident.requirements_reviewed_by = None
    incident.reviewed_requirement_fields = []



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
        incident.status = IncidentStatus.review_required
        incident.updated_at = datetime.utcnow()
        save_incident(incident)
        _audit(incident.id, ActorType.ai, AuditAction.analysis_completed,
               "AI extraction completed.",
               {"confidence": extraction.confidence,
                "needs_manual_review": extraction.needs_manual_review,
                "failure_reason": extraction.failure_reason})
        _audit(incident.id, ActorType.system, AuditAction.requirements_review_started,
               "AI-proposed requirements are ready for coordinator review.")
        if extraction.needs_manual_review:
            _audit(incident.id, ActorType.system, AuditAction.manual_review_flagged,
                   "Accessibility requirements could not be reliably identified. Coordinator review is required.")
    except Exception as e:
        incident.needs_manual_review = True
        incident.status = IncidentStatus.review_required
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
# Requirement review — preserve AI proposal, edit final coordinator profile
# ---------------------------------------------------------------------------

@router.get("/{incident_id}/requirements")
async def get_requirements(incident_id: str) -> dict:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return {
        "incident_id": incident_id,
        "reviewed": incident.requirements_reviewed,
        "requirement_version": incident.requirement_version,
        "requirements": _requirements_payload(incident),
    }


@router.patch("/{incident_id}/requirements/{field}", response_model=Incident)
async def update_requirement(incident_id: str, field: str, body: RequirementUpdateRequest):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if field not in REQUIREMENTS:
        raise HTTPException(status_code=404, detail="Unknown requirement field.")
    if incident.status in (IncidentStatus.confirmed, IncidentStatus.manual_override_authorized):
        raise HTTPException(status_code=409, detail="Requirements cannot be changed after a final human decision.")

    previous = getattr(incident.person, field)
    final_value = _from_review_value(field, body.value)
    ai_value = getattr(incident.ai_person, field)
    setattr(incident.person, field, final_value)

    # Any edit after review invalidates existing reports and demands a new
    # review confirmation before deterministic evaluation can run again.
    had_evaluations = bool(get_evaluations(incident_id))
    invalidated_routes = invalidate_route_evaluations_for_incident(
        incident_id,
        "Reviewed requirements changed after this route evaluation.",
    )
    clear_evaluations(incident_id)
    incident.requirements_review_started = True
    incident.requirements_reviewed = False
    incident.requirements_reviewed_at = None
    incident.requirements_reviewed_by = None
    if field not in incident.reviewed_requirement_fields:
        incident.reviewed_requirement_fields.append(field)
    incident.status = IncidentStatus.review_required
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    action = AuditAction.requirement_changed if final_value != ai_value else AuditAction.requirement_reviewed
    _audit(
        incident_id,
        ActorType.human,
        action,
        (
            f"{REQUIREMENTS[field]} changed from AI value "
            f"{_to_review_value(field, ai_value)} to {_to_review_value(field, final_value)}."
            if action == AuditAction.requirement_changed
            else f"{REQUIREMENTS[field]} confirmed as {_to_review_value(field, final_value)}."
        ),
        {
            "field": field,
            "label": REQUIREMENTS[field],
            "ai_value": _to_review_value(field, ai_value),
            "previous_value": _to_review_value(field, previous),
            "final_value": _to_review_value(field, final_value),
            "coordinator_id": body.coordinator_id,
        },
    )
    if had_evaluations:
        _audit(
            incident_id,
            ActorType.system,
            AuditAction.evaluation_invalidated,
            "Previous resource evaluation invalidated because a reviewed requirement changed.",
            {"field": field, "requirement_version": incident.requirement_version},
        )
    if invalidated_routes:
        _audit(
            incident_id,
            ActorType.system,
            AuditAction.route_evaluation_invalidated,
            "Previous route evaluation invalidated because a reviewed requirement changed.",
            {"field": field, "requirement_version": incident.requirement_version},
        )
    return incident


@router.post("/{incident_id}/requirements/confirm", response_model=Incident)
async def confirm_requirements(incident_id: str, body: ConfirmRequirementsRequest):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.status in (IncidentStatus.confirmed, IncidentStatus.manual_override_authorized):
        raise HTTPException(status_code=409, detail="Requirements cannot be changed after a final human decision.")
    if incident.requirements_reviewed:
        return incident

    incident.requirements_review_started = True
    incident.requirements_reviewed = True
    incident.requirement_version += 1
    incident.requirements_reviewed_at = datetime.utcnow()
    incident.requirements_reviewed_by = body.coordinator_id
    incident.reviewed_requirement_fields = list(REQUIREMENTS)
    incident.status = IncidentStatus.ready_for_evaluation
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    active = sum(item["final_value"] == "required" for item in _requirements_payload(incident))
    _audit(
        incident_id,
        ActorType.human,
        AuditAction.requirements_confirmed,
        f"Requirements confirmed by coordinator. Version {incident.requirement_version}; {active} active requirements.",
        {
            "requirement_version": incident.requirement_version,
            "active_requirements": active,
            "coordinator_id": body.coordinator_id,
        },
    )
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
    invalidate_route_evaluations_for_incident(
        incident_id,
        "Incident analysis restarted after this route evaluation.",
    )
    incident.requirements_reviewed = False
    incident.requirements_reviewed_at = None
    incident.requirements_reviewed_by = None
    save_incident(incident)
    _audit(incident_id, ActorType.ai, AuditAction.analysis_started, "Re-analysis started.")

    extraction = await extractor.extract(incident.original_text or "", incident.image_url)
    _apply_extraction(incident, extraction)
    incident.status = IncidentStatus.review_required
    incident.updated_at = datetime.utcnow()
    save_incident(incident)

    _audit(incident_id, ActorType.ai, AuditAction.analysis_completed,
           "AI re-analysis completed.",
           {"confidence": extraction.confidence,
            "needs_manual_review": extraction.needs_manual_review,
            "failure_reason": extraction.failure_reason})
    _audit(incident_id, ActorType.system, AuditAction.requirements_review_started,
           "AI-proposed requirements are ready for coordinator review.")
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
    incident.requirements_reviewed = False
    incident.requirements_reviewed_at = None
    incident.requirements_reviewed_by = None
    incident.status = IncidentStatus.review_required
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
    if not incident.requirements_reviewed:
        raise HTTPException(
            status_code=409,
            detail="Requirements must be reviewed and confirmed before resource evaluation.",
        )

    # Evaluation is idempotent for an unchanged case. Revisiting the resource
    # screen must not add another set of audit events for the same decision.
    existing_reports = get_evaluations(incident_id)
    if existing_reports and all(report.is_current for report in existing_reports):
        return {
            "incident_id": incident_id,
            "evaluations": [report.model_dump() for report in existing_reports],
        }

    resources = list_resources()
    reports = evaluate_all(
        incident.person,
        [resource_for_evaluation(resource) for resource in resources],
        incident_id,
    )
    for report, resource in zip(reports, resources):
        report.requirement_version = incident.requirement_version
        report.resource_version = resource.resource_version
        _attach_evidence_metadata(report, resource)

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

    if incident.status != IncidentStatus.evaluated:
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
    resource = get_resource(body.resource_id)
    if (
        resource is None
        or report.requirement_version != incident.requirement_version
        or report.resource_version != resource.resource_version
        or not report.is_current
    ):
        raise HTTPException(
            status_code=409,
            detail="This evaluation is stale. Re-evaluate using the current requirements and resource verification.",
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
