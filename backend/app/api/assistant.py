"""Read-only assistant endpoint backed by a fixed SAHAYA evidence snapshot."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ai.assistant import assistant
from app.models.assistant import AssistantEvidence, AssistantQuery, AssistantResponse
from app.store.memory import (
    get_audit, get_evaluations, get_incident, get_resource,
    get_route_evaluation, get_route_observation,
)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(body: AssistantQuery) -> AssistantResponse:
    incident = get_incident(body.incident_id)
    resource = get_resource(body.resource_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found.")

    evaluation = next((item for item in get_evaluations(incident.id) if item.resource_id == resource.id), None)
    route_observation = get_route_observation(incident.id, resource.id)
    route_evaluation = get_route_evaluation(incident.id, resource.id)
    context = {
        "case": incident.model_dump(mode="json"),
        "requirements": {"reviewed": incident.requirements_reviewed, "version": incident.requirement_version},
        "resource": {
            **resource.model_dump(mode="json"),
            "capacity": {
                "available_capacity": resource.available_capacity,
                "accessible_spaces_remaining": resource.accessible_spaces_remaining(),
                "caregiver_spaces_remaining": resource.caregiver_spaces_remaining(),
            },
        },
        "resource_evaluation": evaluation.model_dump(mode="json") if evaluation else None,
        "route_observation": route_observation.model_dump(mode="json") if route_observation else None,
        "route_evaluation": route_evaluation.model_dump(mode="json") if route_evaluation else None,
        "audit": [entry.model_dump(mode="json") for entry in get_audit(incident.id)[-12:]],
    }
    evidence = AssistantEvidence(
        requirement_version=incident.requirement_version,
        resource_version=resource.resource_version,
        route_version=route_observation.route_version if route_observation else None,
        resource_evaluation_status=evaluation.status.value if evaluation else None,
        route_evaluation_status=route_evaluation.status.value if route_evaluation else None,
        evaluated_at=evaluation.evaluated_at.isoformat() if evaluation else None,
    )
    return await assistant.answer(body.question, body.language, context, evidence)
