"""
SAHAYA — Incident & Person data models.
These are the canonical Pydantic schemas used across the API and constraint engine.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class IncidentType(str, Enum):
    flood = "flood"
    fire = "fire"
    landslide = "landslide"
    cyclone = "cyclone"
    earthquake = "earthquake"
    medical = "medical"
    other = "other"


class Urgency(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class MobilityType(str, Enum):
    wheelchair = "wheelchair"
    walking_aid = "walking_aid"
    bedridden = "bedridden"
    ambulatory = "ambulatory"
    unknown = "unknown"


class AgeGroup(str, Enum):
    child = "child"
    adult = "adult"
    elderly = "elderly"
    unknown = "unknown"


class IncidentStatus(str, Enum):
    received = "received"
    analyzing = "analyzing"
    review_required = "review_required"
    ready_for_evaluation = "ready_for_evaluation"
    needs_clarification = "needs_clarification"
    evaluated = "evaluated"
    confirmed = "confirmed"
    manual_override_authorized = "manual_override_authorized"
    closed = "closed"


# ---------------------------------------------------------------------------
# Person profile — extracted from the incident report
# ---------------------------------------------------------------------------

class PersonProfile(BaseModel):
    """
    Structured accessibility profile for the person needing help.
    Optional booleans: True = yes, False = no, None = unknown.
    """
    age_group: AgeGroup = AgeGroup.unknown
    mobility: MobilityType = MobilityType.unknown

    # Critical mobility constraints
    wheelchair_required: Optional[bool] = None
    stairs_allowed: Optional[bool] = None     # False = cannot use stairs
    ramp_usable: Optional[bool] = None

    # Support requirements
    caregiver_required: Optional[bool] = None
    accessible_transport_required: Optional[bool] = None

    # Sensory / communication
    visual_communication_required: Optional[bool] = None
    hearing_support_required: Optional[bool] = None

    # Language / communication
    language: str = "ml"                      # ISO 639-1

    notes: Optional[str] = None

    def has_any_constraints(self) -> bool:
        """Return whether extraction found at least one actionable requirement."""
        return any(
            value is not None
            for value in (
                self.wheelchair_required,
                self.stairs_allowed,
                self.ramp_usable,
                self.caregiver_required,
                self.accessible_transport_required,
                self.visual_communication_required,
                self.hearing_support_required,
            )
        )


# ---------------------------------------------------------------------------
# Constraint — a single extracted requirement with provenance
# ---------------------------------------------------------------------------

class ConstraintSource(str, Enum):
    user = "user"
    ai = "ai"
    coordinator = "coordinator"
    system = "system"


class Constraint(BaseModel):
    constraint_type: str
    required: bool = True
    value: str                                # e.g. "prohibited", "required", "true"
    source: ConstraintSource = ConstraintSource.ai
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verified: bool = False


# ---------------------------------------------------------------------------
# Incident — the top-level case object
# ---------------------------------------------------------------------------

class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    status: IncidentStatus = IncidentStatus.received
    incident_type: Optional[IncidentType] = None
    urgency: Optional[Urgency] = None
    location_text: Optional[str] = None

    # The structured person profile
    person: PersonProfile = Field(default_factory=PersonProfile)
    # Immutable AI proposal; `person` becomes the coordinator-reviewed profile.
    ai_person: PersonProfile = Field(default_factory=PersonProfile)
    requirements_review_started: bool = False
    requirements_reviewed: bool = False
    requirement_version: int = 0
    requirements_reviewed_at: Optional[datetime] = None
    requirements_reviewed_by: Optional[str] = None
    reviewed_requirement_fields: list[str] = Field(default_factory=list)

    # Raw extracted constraints list (supplementary to person profile)
    constraints: list[Constraint] = Field(default_factory=list)

    # Original report text
    original_text: Optional[str] = None
    image_url: Optional[str] = None

    # AI extraction metadata
    extraction_confidence: Optional[float] = None
    needs_manual_review: bool = False

    # Confirmed assignment
    confirmed_resource_id: Optional[str] = None
    confirmed_by: Optional[str] = None        # coordinator user id
    confirmed_at: Optional[datetime] = None

    # A human-authorized exception. This never changes the original rule result.
    manual_override_resource_id: Optional[str] = None
    manual_override_by: Optional[str] = None
    manual_override_at: Optional[datetime] = None
    manual_override_reason: Optional[str] = None


class CasePerson(BaseModel):
    """A separately reviewed person within a multi-person incident."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    display_name: str
    original_text: Optional[str] = None
    ai_person: PersonProfile = Field(default_factory=PersonProfile)
    person: PersonProfile = Field(default_factory=PersonProfile)
    requirement_version: int = 0
    requirements_reviewed: bool = False
    reviewed_requirement_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreatePersonRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=5000)


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------

class CreateIncidentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    image_url: Optional[str] = None


class AnswerClarificationRequest(BaseModel):
    question_key: str
    answer: str                               # "yes" | "no" | "not_sure"


class ConfirmAssignmentRequest(BaseModel):
    resource_id: str
    coordinator_id: str
    notes: Optional[str] = None


class ManualOverrideRequest(BaseModel):
    resource_id: str
    coordinator_id: str
    reason: Optional[str] = None


class AuthorizeManualOverrideRequest(BaseModel):
    resource_id: str
    coordinator_id: str
    reason: str = Field(..., min_length=1, max_length=2000)


class RequirementUpdateRequest(BaseModel):
    """Tri-state coordinator decision for a reviewable requirement."""
    value: str = Field(..., pattern="^(required|not_required|unknown)$")
    coordinator_id: str = Field(..., min_length=1)


class ConfirmRequirementsRequest(BaseModel):
    coordinator_id: str = Field(..., min_length=1)


class IncidentSummaryResponse(BaseModel):
    id: str
    status: IncidentStatus
    incident_type: Optional[IncidentType]
    urgency: Optional[Urgency]
    location_text: Optional[str]
    person: PersonProfile
    ai_person: PersonProfile
    requirements_reviewed: bool
    requirement_version: int
    extraction_confidence: Optional[float]
    needs_manual_review: bool
    confirmed_resource_id: Optional[str]
    manual_override_resource_id: Optional[str]
    created_at: datetime
