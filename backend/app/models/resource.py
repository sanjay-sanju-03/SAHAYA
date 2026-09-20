"""
SAHAYA — Resource data models.
Resources are shelters, vehicles, or volunteer teams.
All capability fields use Optional[bool]:
  True  = capability confirmed present
  False = capability confirmed absent
  None  = unknown / not verified
"""
from __future__ import annotations

from datetime import datetime, timedelta
import os
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    shelter = "shelter"
    vehicle = "vehicle"
    volunteer = "volunteer"


class ResourceStatus(str, Enum):
    available = "available"
    full = "full"
    unavailable = "unavailable"
    unknown = "unknown"


class FreshnessStatus(str, Enum):
    current = "CURRENT"
    aging = "AGING"
    stale = "STALE"
    never_verified = "NEVER_VERIFIED"


class CapabilityVerification(BaseModel):
    """Provenance for one resource capability value."""
    value: Optional[bool] = None
    verification_status: str = "unverified"
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Capabilities — every field is nullable (True / False / None)
# ---------------------------------------------------------------------------

class ResourceCapabilities(BaseModel):
    """
    Physical and support capabilities of a resource.
    None means the attribute has not been verified.
    The constraint engine treats None as UNKNOWN, never as True.
    """
    # Shelter / venue capabilities
    ground_floor: Optional[bool] = None
    stairs_required: Optional[bool] = None   # True = must use stairs to enter
    ramp: Optional[bool] = None
    wheelchair_access: Optional[bool] = None
    accessible_toilet: Optional[bool] = None

    # Vehicle capabilities
    wheelchair_transport: Optional[bool] = None  # has wheelchair lift/ramp

    # Support capabilities
    caregiver_support: Optional[bool] = None
    visual_communication_support: Optional[bool] = None
    hearing_support: Optional[bool] = None

    # Verified timestamp
    last_verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Resource — the top-level resource object
# ---------------------------------------------------------------------------

class Resource(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceType
    name: str
    location_text: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    status: ResourceStatus = ResourceStatus.available

    capacity: Optional[int] = None
    available_capacity: Optional[int] = None
    current_occupancy: Optional[int] = None
    accessible_capacity: Optional[int] = None
    accessible_occupied: Optional[int] = None
    caregiver_capacity: Optional[int] = None
    caregiver_occupied: Optional[int] = None

    def accessible_spaces_remaining(self) -> Optional[int]:
        if self.accessible_capacity is None or self.accessible_occupied is None:
            return None
        return self.accessible_capacity - self.accessible_occupied

    def caregiver_spaces_remaining(self) -> Optional[int]:
        if self.caregiver_capacity is None or self.caregiver_occupied is None:
            return None
        return self.caregiver_capacity - self.caregiver_occupied

    capabilities: ResourceCapabilities = Field(default_factory=ResourceCapabilities)
    capability_verifications: dict[str, CapabilityVerification] = Field(default_factory=dict)
    resource_version: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Demo/seed flag
    is_demo: bool = False


class ResourceCapacityUpdate(BaseModel):
    """Coordinator-supplied capacity figures kept separate from capabilities."""
    total_capacity: Optional[int] = Field(default=None, ge=0)
    current_occupancy: Optional[int] = Field(default=None, ge=0)
    accessible_capacity: Optional[int] = Field(default=None, ge=0)
    accessible_occupied: Optional[int] = Field(default=None, ge=0)
    caregiver_capacity: Optional[int] = Field(default=None, ge=0)
    caregiver_occupied: Optional[int] = Field(default=None, ge=0)


class ResourceVerificationRequest(BaseModel):
    """Coordinator verification submission for capabilities and/or capacity."""
    capabilities: dict[str, str] = Field(default_factory=dict)
    capacity: Optional[ResourceCapacityUpdate] = None
    coordinator_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


CAPABILITY_FIELDS = (
    "ground_floor",
    "stairs_required",
    "ramp",
    "wheelchair_access",
    "accessible_toilet",
    "wheelchair_transport",
    "caregiver_support",
    "visual_communication_support",
    "hearing_support",
)


def freshness_status(resource: Resource, capability: str, now: Optional[datetime] = None) -> FreshnessStatus:
    """Return configurable freshness for a capability's supporting record."""
    value = getattr(resource.capabilities, capability)
    if value is None:
        return FreshnessStatus.never_verified

    verification = resource.capability_verifications.get(capability)
    verified_at = verification.verified_at if verification else resource.capabilities.last_verified_at
    if verified_at is None:
        return FreshnessStatus.never_verified

    current_time = now or datetime.utcnow()
    age = current_time - verified_at
    aging_days = int(os.getenv("RESOURCE_FRESHNESS_AGING_DAYS", "7"))
    stale_days = int(os.getenv("RESOURCE_FRESHNESS_STALE_DAYS", "14"))
    if age >= timedelta(days=stale_days):
        return FreshnessStatus.stale
    if age >= timedelta(days=aging_days):
        return FreshnessStatus.aging
    return FreshnessStatus.current


def resource_for_evaluation(resource: Resource, now: Optional[datetime] = None) -> Resource:
    """Create a conservative resource view without changing the rule engine.

    A stale or never-verified positive capability becomes UNKNOWN. Explicit
    negatives remain FALSE, preserving evidence of a known conflict.
    """
    evaluated_resource = resource.model_copy(deep=True)
    for field in CAPABILITY_FIELDS:
        value = getattr(evaluated_resource.capabilities, field)
        if value is True and freshness_status(resource, field, now) in (
            FreshnessStatus.stale,
            FreshnessStatus.never_verified,
        ):
            setattr(evaluated_resource.capabilities, field, None)
    return evaluated_resource
