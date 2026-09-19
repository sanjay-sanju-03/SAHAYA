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
