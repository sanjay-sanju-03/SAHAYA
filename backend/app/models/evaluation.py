"""
SAHAYA — Evaluation data models.
The constraint engine produces EvaluationReports composed of EvaluationChecks.
Status follows strict priority: BLOCKED > UNKNOWN > SAFE.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    safe = "SAFE"
    unknown = "UNKNOWN"
    blocked = "BLOCKED"


class EvaluationStatus(str, Enum):
    safe = "SAFE"
    unknown = "UNKNOWN"
    blocked = "BLOCKED"
    not_applicable = "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# Single constraint check result
# ---------------------------------------------------------------------------

class EvaluationCheck(BaseModel):
    """
    Result of evaluating one constraint against one resource attribute.
    """
    constraint: str                           # e.g. "wheelchair_access"
    status: CheckStatus

    # Human-readable labels for the UI evidence panel
    requirement_label: str                    # "Person requires wheelchair access"
    resource_label: str                       # "Wheelchair access: YES / NO / Unknown"
    evidence_label: str                       # "Verified by coordinator" / "Not on record"
    reason: str                               # Full explanation sentence

    # Raw values for debugging / audit
    required_value: Optional[str] = None
    resource_value: Optional[str] = None

    # Structured evidence used by the WHY and comparison interfaces.
    capability: Optional[str] = None
    required: bool = True
    person_source: Optional[str] = None
    person_value: Optional[str] = None
    resource_source: Optional[str] = None
    resource_verified_at: Optional[datetime] = None
    resource_freshness: Optional[str] = None


# ---------------------------------------------------------------------------
# Full evaluation report for one (incident, resource) pair
# ---------------------------------------------------------------------------

class EvaluationReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    resource_id: str
    resource_name: str
    requirement_version: int = 0
    resource_version: int = 0
    is_current: bool = True
    outdated_reason: Optional[str] = None

    # The overall status — determined by priority logic or resource applicability.
    status: EvaluationStatus
    # Richer status labels as per spec
    status_label: str                         # "SAFE — All required capabilities verified" etc.

    checks: list[EvaluationCheck] = Field(default_factory=list)

    # Counts for the UI summary
    total_checks: int = 0
    passed_checks: int = 0
    unknown_checks: int = 0
    blocked_checks: int = 0

    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Batch evaluation — all resources for one incident
# ---------------------------------------------------------------------------

class BatchEvaluationResponse(BaseModel):
    incident_id: str
    evaluations: list[EvaluationReport]
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PersonEvaluation(BaseModel):
    person_id: str
    display_name: str
    requirement_version: int
    result: EvaluationReport


class GroupEvaluation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    resource_id: str
    resource_name: str
    resource_version: int
    people: list[PersonEvaluation] = Field(default_factory=list)
    group_status: EvaluationStatus
    capacity_status: CheckStatus
    capacity_required: int
    capacity_available: Optional[int] = None
    accessible_spaces_required: int = 0
    accessible_spaces_available: Optional[int] = None
    caregiver_spaces_required: int = 0
    caregiver_spaces_available: Optional[int] = None
    is_current: bool = True
    outdated_reason: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
