"""Versioned route-observation and route-evaluation endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.engine.route_engine import evaluate_route
from app.models.audit import ActorType, AuditAction, AuditLog
from app.models.route import RouteObservation, RouteObservationUpdate
from app.store.memory import (
    append_audit,
    get_incident,
    get_resource,
    get_route_evaluation,
    get_route_observation,
    invalidate_route_evaluation,
    save_route_evaluation,
    save_route_observation,
)

router = APIRouter(prefix="/api/incidents/{incident_id}/routes", tags=["routes"])


def _incident_and_resource(incident_id: str, resource_id: str):
    incident = get_incident(incident_id)
    resource = get_resource(resource_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return incident, resource


@router.get("/{resource_id}")
async def get_route_record(incident_id: str, resource_id: str):
    incident, resource = _incident_and_resource(incident_id, resource_id)
    return {
        "incident_id": incident.id,
        "resource_id": resource.id,
        "observation": get_route_observation(incident_id, resource_id),
        "evaluation": get_route_evaluation(incident_id, resource_id),
    }


@router.post("/{resource_id}/observation")
async def update_route_observation(incident_id: str, resource_id: str, body: RouteObservationUpdate):
    incident, resource = _incident_and_resource(incident_id, resource_id)
    observation = get_route_observation(incident_id, resource_id)
    if observation is None:
        observation = RouteObservation(incident_id=incident_id, resource_id=resource_id)
    observation.route_exists = body.route_exists
    observation.known_hazard_on_route = body.known_hazard_on_route
    observation.accessible_for_person = body.accessible_for_person
    observation.source = body.source
    observation.notes = body.notes
    observation.observed_by = body.coordinator_id
    observation.observed_at = datetime.utcnow()
    observation.route_version += 1
    save_route_observation(observation)

    invalidated = invalidate_route_evaluation(
        incident_id,
        resource_id,
        "Route observation changed after this route evaluation.",
    )
    append_audit(AuditLog(
        incident_id=incident_id,
        actor_type=ActorType.human,
        action=AuditAction.route_observation_updated,
        description=f"Route observation updated for {resource.name}. Route version {observation.route_version}.",
        metadata={
            "route_id": observation.route_id,
            "resource_id": resource.id,
            "route_version": observation.route_version,
            "source": body.source,
            "coordinator_id": body.coordinator_id,
        },
    ))
    if invalidated:
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.system,
            action=AuditAction.route_evaluation_invalidated,
            description=f"Previous route evaluation invalidated for {resource.name}.",
            metadata={"route_id": observation.route_id, "resource_id": resource.id, "route_version": observation.route_version},
        ))
    return {"observation": observation, "evaluation_invalidated": invalidated is not None}


@router.post("/{resource_id}/evaluate")
async def evaluate_route_for_resource(incident_id: str, resource_id: str):
    incident, resource = _incident_and_resource(incident_id, resource_id)
    if not incident.requirements_reviewed:
        raise HTTPException(status_code=409, detail="Requirements must be reviewed and confirmed before route evaluation.")
    observation = get_route_observation(incident_id, resource_id)
    if observation is None:
        observation = RouteObservation(incident_id=incident_id, resource_id=resource_id)

    append_audit(AuditLog(
        incident_id=incident_id,
        actor_type=ActorType.system,
        action=AuditAction.route_evaluation_started,
        description=f"Route evaluation started for {resource.name}.",
        metadata={"resource_id": resource.id, "route_id": observation.route_id},
    ))
    evaluation = evaluate_route(
        incident.person,
        resource,
        observation,
        requirement_version=incident.requirement_version,
    )
    save_route_evaluation(evaluation)
    append_audit(AuditLog(
        incident_id=incident_id,
        actor_type=ActorType.system,
        action=AuditAction.route_evaluated,
        description=f"Route evaluated for {resource.name}: {evaluation.status.value}.",
        metadata={
            "resource_id": resource.id,
            "route_id": observation.route_id,
            "requirement_version": evaluation.requirement_version,
            "resource_version": evaluation.resource_version,
            "route_version": evaluation.route_version,
            "result": evaluation.status.value,
        },
    ))
    return evaluation
