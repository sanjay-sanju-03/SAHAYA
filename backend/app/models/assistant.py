"""Read-only request and response models for the SAHAYA Assistant."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    incident_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=800)
    language: Literal["en", "ml"] = "en"


class AssistantEvidence(BaseModel):
    requirement_version: int
    resource_version: int
    route_version: Optional[int] = None
    resource_evaluation_status: Optional[str] = None
    route_evaluation_status: Optional[str] = None
    evaluated_at: Optional[str] = None


class AssistantResponse(BaseModel):
    answer: str
    language: Literal["en", "ml"]
    evidence: AssistantEvidence
