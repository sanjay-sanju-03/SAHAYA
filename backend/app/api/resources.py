"""SAHAYA — Resource records, verification, freshness, and provenance."""
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.audit import ActorType, AuditAction, AuditLog
from app.ai.vision import observe_resource_image
from app.models.resource import (
    CAPABILITY_FIELDS,
    CapabilityVerification,
    Resource,
    ResourceVerificationRequest,
    freshness_status,
)
from app.store.memory import (
    append_audit,
    get_resource,
    invalidate_evaluations_for_resource,
    invalidate_group_evaluations_for_resource,
    invalidate_route_evaluations_for_resource,
    list_resources,
    save_resource,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=list[Resource])
async def get_resources():
    return list_resources()


def _value_from_submission(value: str) -> bool | None:
    if value == "yes":
        return True
    if value == "no":
        return False
    if value == "unknown":
        return None
    raise HTTPException(status_code=422, detail="Capability values must be yes, no, or unknown.")


def _freshness_payload(resource: Resource) -> dict:
    return {
        field: {
            "status": freshness_status(resource, field).value,
            "verification": resource.capability_verifications.get(field).model_dump()
            if resource.capability_verifications.get(field)
            else None,
        }
        for field in CAPABILITY_FIELDS
    }


@router.get("/{resource_id}/verification")
async def get_resource_verification(resource_id: str) -> dict:
    resource = get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found.")
    return {
        "resource": resource.model_dump(),
        "resource_version": resource.resource_version,
        "freshness": _freshness_payload(resource),
    }


@router.post("/{resource_id}/image-observations")
async def get_resource_image_observations(
    resource_id: str,
    file: UploadFile = File(...),
    inspection_note: str = Form(default=""),
) -> dict:
    """Return observation-only vision output; a coordinator must still save it."""
    if not get_resource(resource_id):
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found.")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Upload a PNG, JPEG, or WebP image.")
    image_bytes = await file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB limit.")
    try:
        observations = await observe_resource_image(image_bytes, file.content_type, inspection_note)
    except Exception:
        raise HTTPException(status_code=503, detail="Image observations are unavailable. Try again or verify manually.")
    return {"source": "resource_image", "observations": observations.model_dump()}


@router.post("/{resource_id}/verify", response_model=Resource)
async def verify_resource(resource_id: str, body: ResourceVerificationRequest):
    resource = get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found.")
    if not body.capabilities and body.capacity is None:
        raise HTTPException(status_code=422, detail="Submit a capability or capacity verification.")
    # Validate and prepare a copy first: an invalid submission must never
    # partially mutate the in-memory resource record.
    resource = resource.model_copy(deep=True)

    changed: list[dict] = []
    verified_at = datetime.utcnow()
    for field, submitted_value in body.capabilities.items():
        if field not in CAPABILITY_FIELDS:
            raise HTTPException(status_code=422, detail=f"Unknown capability field: {field}")
        previous = getattr(resource.capabilities, field)
        final_value = _value_from_submission(submitted_value)
        setattr(resource.capabilities, field, final_value)
        resource.capability_verifications[field] = CapabilityVerification(
            value=final_value,
            verification_status="verified" if final_value is not None else "unverified",
            verified_at=verified_at if final_value is not None else None,
            verified_by=body.coordinator_id,
            source=body.source,
            notes=body.notes,
        )
        changed.append({"field": field, "previous": previous, "value": final_value})

    if body.capacity is not None:
        capacity_updates = body.capacity.model_dump(exclude_unset=True)
        for field, value in capacity_updates.items():
            resource_field = "capacity" if field == "total_capacity" else field
            previous = getattr(resource, resource_field)
            setattr(resource, resource_field, value)
            changed.append({"field": field, "previous": previous, "value": value})

        if resource.capacity is not None and resource.current_occupancy is not None:
            if resource.current_occupancy > resource.capacity:
                raise HTTPException(status_code=422, detail="Current occupancy cannot exceed total capacity.")
            resource.available_capacity = resource.capacity - resource.current_occupancy
        if resource.accessible_capacity is not None and resource.accessible_occupied is not None and resource.accessible_occupied > resource.accessible_capacity:
            raise HTTPException(status_code=422, detail="Accessible occupancy cannot exceed accessible capacity.")
        if resource.caregiver_capacity is not None and resource.caregiver_occupied is not None and resource.caregiver_occupied > resource.caregiver_capacity:
            raise HTTPException(status_code=422, detail="Caregiver occupancy cannot exceed caregiver capacity.")

    resource.resource_version += 1
    resource.updated_at = verified_at
    save_resource(resource)

    affected_incidents = invalidate_evaluations_for_resource(resource_id)
    group_affected = invalidate_group_evaluations_for_resource(resource_id)
    route_affected = invalidate_route_evaluations_for_resource(
        resource_id,
        "Resource capabilities changed after this route evaluation.",
    )
    for incident_id in route_affected:
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.system,
            action=AuditAction.route_evaluation_invalidated,
            description=f"Route evaluation invalidated because {resource.name} changed.",
            metadata={"resource_id": resource.id, "resource_version": resource.resource_version},
        ))
    for incident_id in group_affected:
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.system,
            action=AuditAction.group_evaluation_invalidated,
            description=f"Previous group evaluation invalidated because {resource.name} was re-verified.",
            metadata={"resource_id": resource.id, "resource_version": resource.resource_version},
        ))
    for incident_id in affected_incidents:
        if "image" in body.source.lower():
            for action, description in (
                (AuditAction.resource_image_added, f"Resource image added for {resource.name}."),
                (AuditAction.image_observations_extracted, f"Image observations extracted for {resource.name}; coordinator review required."),
                (AuditAction.resource_observation_reviewed, f"Coordinator reviewed image observations for {resource.name}."),
            ):
                append_audit(AuditLog(
                    incident_id=incident_id,
                    actor_type=ActorType.human if action != AuditAction.image_observations_extracted else ActorType.ai,
                    action=action,
                    description=description,
                    metadata={"resource_id": resource.id, "resource_name": resource.name, "source": body.source},
                ))
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.human,
            action=AuditAction.resource_verification_started,
            description=f"Coordinator started verification for {resource.name}.",
            metadata={
                "resource_id": resource.id,
                "resource_name": resource.name,
                "coordinator_id": body.coordinator_id,
                "source": body.source,
            },
        ))
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.human,
            action=AuditAction.resource_capability_changed,
            description=f"Resource verification updated for {resource.name}. Resource version {resource.resource_version}.",
            metadata={
                "resource_id": resource.id,
                "resource_name": resource.name,
                "resource_version": resource.resource_version,
                "changes": changed,
                "coordinator_id": body.coordinator_id,
                "source": body.source,
                "notes": body.notes,
            },
        ))
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.system,
            action=AuditAction.evaluation_invalidated,
            description=f"Previous resource evaluation invalidated because {resource.name} was re-verified.",
            metadata={"resource_id": resource.id, "resource_version": resource.resource_version},
        ))
        append_audit(AuditLog(
            incident_id=incident_id,
            actor_type=ActorType.human,
            action=AuditAction.resource_verified,
            description=f"{resource.name} verified by coordinator. Source: {body.source}.",
            metadata={"resource_id": resource.id, "resource_version": resource.resource_version},
        ))
    return resource


@router.get("/{resource_id}", response_model=Resource)
async def get_resource_by_id(resource_id: str):
    resource = get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found.")
    return resource
