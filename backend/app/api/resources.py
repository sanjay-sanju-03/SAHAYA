"""
SAHAYA — Resources API router.
"""
from fastapi import APIRouter, HTTPException
from app.models.resource import Resource
from app.store.memory import get_resource, list_resources

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=list[Resource])
async def get_resources():
    return list_resources()


@router.get("/{resource_id}", response_model=Resource)
async def get_resource_by_id(resource_id: str):
    resource = get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found.")
    return resource
