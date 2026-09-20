"""Multi-person case API. Reuses the existing person-resource rule engine."""
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.ai.extractor import extractor
from app.engine.constraint_engine import evaluate
from app.models.audit import ActorType, AuditAction, AuditLog
from app.models.evaluation import CheckStatus, EvaluationStatus, GroupEvaluation, PersonEvaluation
from app.models.incident import CasePerson, ConfirmRequirementsRequest, CreatePersonRequest, RequirementUpdateRequest
from app.models.resource import resource_for_evaluation
from app.store.memory import (
    append_audit, get_group_evaluations, get_incident, get_person, get_resource,
    invalidate_group_evaluations, list_people, list_resources, remove_person,
    save_group_evaluations, save_person,
)

router = APIRouter(prefix="/api/incidents/{incident_id}/people", tags=["people"])
group_router = APIRouter(prefix="/api/incidents", tags=["group-evaluations"])

REQUIREMENTS = {
    "wheelchair_required": "Wheelchair access", "stairs_allowed": "Step-free access",
    "accessible_transport_required": "Accessible transport", "caregiver_required": "Caregiver support",
    "visual_communication_required": "Visual communication", "hearing_support_required": "Hearing support",
}


def _audit(incident_id: str, action: AuditAction, description: str, metadata: dict, actor=ActorType.human):
    append_audit(AuditLog(incident_id=incident_id, actor_type=actor, action=action, description=description, metadata=metadata))


def _to_review(field: str, value):
    if value is None: return "unknown"
    if field == "stairs_allowed": return "required" if value is False else "not_required"
    return "required" if value is True else "not_required"


def _from_review(field: str, value: str):
    if value == "unknown": return None
    if field == "stairs_allowed": return value != "required"
    return value == "required"


def _requirements(person: CasePerson):
    return [{"field": field, "label": label, "ai_value": _to_review(field, getattr(person.ai_person, field)), "final_value": _to_review(field, getattr(person.person, field)), "reviewed": field in person.reviewed_requirement_fields} for field, label in REQUIREMENTS.items()]


def _invalidate(incident_id: str, reason: str):
    if get_group_evaluations(incident_id):
        invalidate_group_evaluations(incident_id, reason)
        _audit(incident_id, AuditAction.group_evaluation_invalidated, reason, {}, ActorType.system)


@router.get("")
async def get_people(incident_id: str):
    if not get_incident(incident_id): raise HTTPException(404, "Incident not found.")
    return {"incident_id": incident_id, "people": [person.model_dump() for person in list_people(incident_id)]}


@router.post("", response_model=CasePerson)
async def add_person(incident_id: str, body: CreatePersonRequest):
    if not get_incident(incident_id): raise HTTPException(404, "Incident not found.")
    person = CasePerson(incident_id=incident_id, display_name=body.display_name, original_text=body.text)
    _audit(incident_id, AuditAction.person_added, f"{person.display_name} added to this case.", {"person_id": person.id})
    _audit(incident_id, AuditAction.person_analysis_started, f"AI analysis started for {person.display_name}.", {"person_id": person.id}, ActorType.ai)
    extraction = await extractor.extract(body.text)
    person.ai_person = extractor.to_person_profile(extraction)
    person.person = person.ai_person.model_copy(deep=True)
    person.updated_at = datetime.utcnow()
    save_person(person)
    _audit(incident_id, AuditAction.person_analysis_completed, f"AI analysis completed for {person.display_name}; coordinator review required.", {"person_id": person.id}, ActorType.ai)
    _invalidate(incident_id, "Group evaluation invalidated because a person was added.")
    return person


@router.get("/{person_id}", response_model=CasePerson)
async def get_person_by_id(incident_id: str, person_id: str):
    person = get_person(incident_id, person_id)
    if not person: raise HTTPException(404, "Person not found.")
    return person


@router.delete("/{person_id}")
async def delete_person(incident_id: str, person_id: str):
    person = remove_person(incident_id, person_id)
    if not person: raise HTTPException(404, "Person not found.")
    _audit(incident_id, AuditAction.person_removed, f"{person.display_name} removed from this case.", {"person_id": person_id})
    _invalidate(incident_id, "Group evaluation invalidated because a person was removed.")
    return {"removed": person_id}


@router.get("/{person_id}/requirements")
async def get_person_requirements(incident_id: str, person_id: str):
    person = get_person(incident_id, person_id)
    if not person: raise HTTPException(404, "Person not found.")
    return {"person_id": person_id, "reviewed": person.requirements_reviewed, "requirement_version": person.requirement_version, "requirements": _requirements(person)}


@router.patch("/{person_id}/requirements/{field}", response_model=CasePerson)
async def update_person_requirement(incident_id: str, person_id: str, field: str, body: RequirementUpdateRequest):
    person = get_person(incident_id, person_id)
    if not person: raise HTTPException(404, "Person not found.")
    if field not in REQUIREMENTS: raise HTTPException(404, "Unknown requirement field.")
    setattr(person.person, field, _from_review(field, body.value))
    person.requirements_reviewed = False
    if field not in person.reviewed_requirement_fields: person.reviewed_requirement_fields.append(field)
    person.updated_at = datetime.utcnow()
    save_person(person)
    _audit(incident_id, AuditAction.person_requirement_changed, f"{REQUIREMENTS[field]} reviewed for {person.display_name}.", {"person_id": person_id, "field": field, "value": body.value, "coordinator_id": body.coordinator_id})
    _invalidate(incident_id, "Group evaluation invalidated because a person's requirement changed.")
    return person


@router.post("/{person_id}/requirements/confirm", response_model=CasePerson)
async def confirm_person_requirements(incident_id: str, person_id: str, body: ConfirmRequirementsRequest):
    person = get_person(incident_id, person_id)
    if not person: raise HTTPException(404, "Person not found.")
    if not person.requirements_reviewed:
        person.requirements_reviewed = True
        person.requirement_version += 1
        person.reviewed_requirement_fields = list(REQUIREMENTS)
        person.updated_at = datetime.utcnow()
        save_person(person)
        _audit(incident_id, AuditAction.person_requirements_confirmed, f"Requirements confirmed for {person.display_name}, version {person.requirement_version}.", {"person_id": person_id, "coordinator_id": body.coordinator_id})
        _invalidate(incident_id, "Group evaluation invalidated because a person's requirements were confirmed.")
    return person


@group_router.post("/{incident_id}/group-evaluate")
async def group_evaluate(incident_id: str):
    return await build_group_evaluations(incident_id)


@group_router.get("/{incident_id}/group-evaluations")
async def get_group_results(incident_id: str):
    return {"incident_id": incident_id, "evaluations": [item.model_dump() for item in get_group_evaluations(incident_id)]}


async def build_group_evaluations(incident_id: str):
    people = list_people(incident_id)
    if not people: raise HTTPException(409, "Add at least two people before group evaluation.")
    if any(not person.requirements_reviewed for person in people): raise HTTPException(409, "Every person must have confirmed requirements before group evaluation.")
    existing = get_group_evaluations(incident_id)
    if existing and all(report.is_current for report in existing): return {"incident_id": incident_id, "evaluations": [item.model_dump() for item in existing]}
    _audit(incident_id, AuditAction.group_evaluation_started, f"Group evaluation started for {len(people)} people.", {"people": len(people)}, ActorType.system)
    groups=[]
    for resource in list_resources():
        person_results=[]
        for person in people:
            result=evaluate(person.person, resource_for_evaluation(resource), incident_id)
            result.requirement_version=person.requirement_version
            result.resource_version=resource.resource_version
            person_results.append(PersonEvaluation(person_id=person.id, display_name=person.display_name, requirement_version=person.requirement_version, result=result))
        statuses=[item.result.status for item in person_results if item.result.status != EvaluationStatus.not_applicable]
        group_status=EvaluationStatus.blocked if EvaluationStatus.blocked in statuses else EvaluationStatus.unknown if EvaluationStatus.unknown in statuses else EvaluationStatus.safe if statuses else EvaluationStatus.not_applicable
        capacity=resource.available_capacity
        is_shelter = resource.type.value == "shelter"
        accessible_required=sum(person.person.wheelchair_required is True for person in people) if is_shelter else 0
        caregiver_required=sum(person.person.caregiver_required is True for person in people) if is_shelter else 0
        accessible_available=resource.accessible_spaces_remaining() if is_shelter else None
        caregiver_available=resource.caregiver_spaces_remaining() if is_shelter else None
        capacity_checks = [CheckStatus.safe if capacity is not None and capacity >= len(people) else CheckStatus.blocked if capacity is not None else CheckStatus.unknown]
        if is_shelter:
            capacity_checks.extend([
                CheckStatus.safe if accessible_required == 0 else CheckStatus.safe if accessible_available is not None and accessible_available >= accessible_required else CheckStatus.blocked if accessible_available is not None else CheckStatus.unknown,
                CheckStatus.safe if caregiver_required == 0 else CheckStatus.safe if caregiver_available is not None and caregiver_available >= caregiver_required else CheckStatus.blocked if caregiver_available is not None else CheckStatus.unknown,
            ])
        capacity_status=CheckStatus.blocked if CheckStatus.blocked in capacity_checks else CheckStatus.unknown if CheckStatus.unknown in capacity_checks else CheckStatus.safe
        if group_status != EvaluationStatus.not_applicable:
            if capacity_status == CheckStatus.blocked: group_status=EvaluationStatus.blocked
            elif capacity_status == CheckStatus.unknown and group_status == EvaluationStatus.safe: group_status=EvaluationStatus.unknown
        group=GroupEvaluation(incident_id=incident_id, resource_id=resource.id, resource_name=resource.name, resource_version=resource.resource_version, people=person_results, group_status=group_status, capacity_status=capacity_status, capacity_required=len(people), capacity_available=capacity, accessible_spaces_required=accessible_required, accessible_spaces_available=accessible_available, caregiver_spaces_required=caregiver_required, caregiver_spaces_available=caregiver_available)
        groups.append(group)
        _audit(incident_id, AuditAction.group_resource_evaluated, f"{resource.name} evaluated for {len(people)} people: {group_status.value}.", {"resource_id": resource.id, "result": group_status.value}, ActorType.system)
        _audit(incident_id, AuditAction.group_capacity_checked, f"Capacity checked for {resource.name}: {capacity_status.value}.", {"resource_id": resource.id, "required": len(people), "available": capacity, "accessible_required": accessible_required, "accessible_available": accessible_available, "caregiver_required": caregiver_required, "caregiver_available": caregiver_available}, ActorType.system)
    save_group_evaluations(incident_id, groups)
    return {"incident_id": incident_id, "evaluations": [item.model_dump() for item in groups]}
