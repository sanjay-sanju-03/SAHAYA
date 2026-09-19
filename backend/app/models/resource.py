"""
SAHAYA — Resource data models.
Resources are shelters, vehicles, or volunteer teams.
All capability fields use Optional[bool]:
  True  = capability confirmed present
  False = capability confirmed absent
  None  = unknown / not verified
"""
from __future__ import annotations

from datetime import datetime
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
    status: ResourceStatus = ResourceStatus.available

    capacity: Optional[int] = None
    available_capacity: Optional[int] = None

    capabilities: ResourceCapabilities = Field(default_factory=ResourceCapabilities)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Demo/seed flag
    is_demo: bool = False
