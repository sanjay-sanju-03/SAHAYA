"""
SAHAYA — Audit log data models.
Every significant action is recorded for transparency.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ActorType(str, Enum):
    ai = "ai"
    system = "system"
    human = "human"


class AuditAction(str, Enum):
    incident_created = "incident_created"
    analysis_started = "analysis_started"
    analysis_completed = "analysis_completed"
    analysis_failed = "analysis_failed"
    clarification_asked = "clarification_asked"
    clarification_answered = "clarification_answered"
    resources_evaluated = "resources_evaluated"
    resource_evaluated = "resource_evaluated"
    assignment_confirmed = "assignment_confirmed"
    manual_override_requested = "manual_override_requested"
    manual_override_authorized = "manual_override_authorized"
    requirements_review_started = "requirements_review_started"
    requirement_reviewed = "requirement_reviewed"
    requirement_changed = "requirement_changed"
    requirements_confirmed = "requirements_confirmed"
    evaluation_invalidated = "evaluation_invalidated"
    resource_verification_started = "resource_verification_started"
    resource_image_added = "resource_image_added"
    image_observations_extracted = "image_observations_extracted"
    resource_observation_reviewed = "resource_observation_reviewed"
    resource_capability_changed = "resource_capability_changed"
    resource_verified = "resource_verified"
    person_added = "person_added"
    person_removed = "person_removed"
    person_analysis_started = "person_analysis_started"
    person_analysis_completed = "person_analysis_completed"
    person_requirements_confirmed = "person_requirements_confirmed"
    person_requirement_changed = "person_requirement_changed"
    group_evaluation_started = "group_evaluation_started"
    group_resource_evaluated = "group_resource_evaluated"
    group_capacity_checked = "group_capacity_checked"
    group_evaluation_invalidated = "group_evaluation_invalidated"
    route_observation_updated = "route_observation_updated"
    route_evaluation_started = "route_evaluation_started"
    route_evaluated = "route_evaluated"
    route_evaluation_invalidated = "route_evaluation_invalidated"
    manual_review_flagged = "manual_review_flagged"


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    actor_type: ActorType
    action: AuditAction
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Human-readable description for the timeline UI
    description: str = ""


class AuditTimelineResponse(BaseModel):
    incident_id: str
    logs: list[AuditLog]
