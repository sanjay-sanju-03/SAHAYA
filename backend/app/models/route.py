"""Route and hazard evidence models.

Route compatibility is deliberately separate from resource compatibility.
These records describe the current journey from an incident to one resource;
they never modify the resource decision itself.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
import os
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationCheck, EvaluationStatus


class RouteFreshness(str, Enum):
    current = "CURRENT"
    stale = "STALE"
    never_observed = "NEVER_OBSERVED"


class RouteObservation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    route_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    resource_id: str
    route_exists: Optional[bool] = None
    known_hazard_on_route: Optional[bool] = None
    accessible_for_person: Optional[bool] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    observed_by: Optional[str] = None
    observed_at: Optional[datetime] = None
    route_version: int = 0


class RouteObservationUpdate(BaseModel):
    route_exists: Optional[bool] = None
    known_hazard_on_route: Optional[bool] = None
    accessible_for_person: Optional[bool] = None
    source: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)
    coordinator_id: str = Field(..., min_length=1)


class RouteEvaluation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    resource_id: str
    resource_name: str
    status: EvaluationStatus
    checks: list[EvaluationCheck] = Field(default_factory=list)
    requirement_version: int = 0
    resource_version: int = 0
    route_version: int = 0
    route_freshness: RouteFreshness = RouteFreshness.never_observed
    is_current: bool = True
    outdated_reason: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


def route_freshness(observation: RouteObservation, now: Optional[datetime] = None) -> RouteFreshness:
    if observation.observed_at is None:
        return RouteFreshness.never_observed
    max_age = int(os.getenv("ROUTE_FRESHNESS_MINUTES", "60"))
    current_time = now or datetime.utcnow()
    if current_time - observation.observed_at > timedelta(minutes=max_age):
        return RouteFreshness.stale
    return RouteFreshness.current
