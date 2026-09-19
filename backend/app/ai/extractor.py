"""
SAHAYA — AI Extraction Layer.

Abstraction over gpt-4o that converts incident text (and optional image)
into a validated PersonProfile + incident metadata.

Architecture:
  LLM → raw JSON → Pydantic validation → normalized IncidentExtraction
  On failure: retry once → fallback to needs_manual_review = True

No constraint decisions are made here.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.incident import (
    AgeGroup,
    Constraint,
    ConstraintSource,
    IncidentType,
    MobilityType,
    PersonProfile,
    Urgency,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI output schema — strict Pydantic model for the LLM to fill
# ---------------------------------------------------------------------------

class ConstraintSet(BaseModel):
    """Safety-critical requirements extracted from an incident report."""

    wheelchair_required: Optional[bool] = None
    stairs_allowed: Optional[bool] = None
    accessible_transport_required: Optional[bool] = None
    caregiver_required: Optional[bool] = None


class IncidentExtraction(ConstraintSet):
    """
    Structured output from the AI extraction step.
    All fields optional to handle partial extractions gracefully.
    """
    # Reject renamed or misspelled model keys instead of silently converting an
    # invalid response into an empty profile.
    model_config = ConfigDict(extra="forbid")

    incident_type: Optional[IncidentType] = None
    urgency: Optional[Urgency] = None
    location_text: Optional[str] = None

    # Person
    age_group: Optional[AgeGroup] = AgeGroup.unknown
    mobility: Optional[MobilityType] = MobilityType.unknown
    ramp_usable: Optional[bool] = None
    visual_communication_required: Optional[bool] = None
    hearing_support_required: Optional[bool] = None
    language: str = "ml"

    notes: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    needs_manual_review: bool = False
    # Internal diagnostic only. This value is never sourced from the model.
    failure_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# System prompt — enforces JSON output and safety rules
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """You are an emergency intake assistant for SAHAYA, an inclusive emergency decision support system.

Your task: Convert an emergency report into a structured JSON object.

IMPORTANT RULES:
1. You MUST return ONLY valid JSON. No explanatory text before or after.
2. Use null for any field you are uncertain about. NEVER assume or invent information.
3. You MUST NOT make assumptions about resource attributes — only extract from the person's report.
4. If the report is in Malayalam or another language, translate and understand it completely before extracting fields.
5. Extract only information explicitly stated or strongly implied by the report. Never infer that a capability exists.
6. For boolean accessibility fields, return false when the report explicitly states the opposite condition. Return null only when the report genuinely provides no information.
7. wheelchair_required: true when the person uses or requires a wheelchair. Set false for statements such as "does not use a wheelchair", "can walk without assistance", or "does not require wheelchair support".
8. stairs_allowed: false when the report says the person cannot use stairs. Set true for statements such as "can use stairs" or "stairs are not a problem".
9. accessible_transport_required: true when wheelchair-accessible transportation is requested or required. Set false only when the report explicitly says accessible transport is unnecessary.
10. caregiver_required: true only when caregiver assistance is explicitly required; false only when explicitly unnecessary; otherwise null.
11. hearing_support_required: true when the person has difficulty hearing spoken instructions or explicitly requires hearing assistance.
12. visual_communication_required: true when the person explicitly needs visual communication, visual alerts, visual instructions, or non-audio communication. Do NOT interpret hearing difficulty as visual impairment.
13. confidence: your confidence in the extraction (0.0 to 1.0).

JSON Schema to return:
{
  "incident_type": "flood" | "fire" | "landslide" | "cyclone" | "earthquake" | "medical" | "other" | null,
  "urgency": "critical" | "high" | "medium" | "low" | null,
  "location_text": string | null,
  "age_group": "child" | "adult" | "elderly" | "unknown",
  "mobility": "wheelchair" | "walking_aid" | "bedridden" | "ambulatory" | "unknown",
  "wheelchair_required": true | false | null,
  "stairs_allowed": true | false | null,
  "ramp_usable": true | false | null,
  "caregiver_required": true | false | null,
  "accessible_transport_required": true | false | null,
  "visual_communication_required": true | false | null,
  "hearing_support_required": true | false | null,
  "language": "ml" | "en" | string,
  "notes": string | null,
  "confidence": number between 0.0 and 1.0,
  "needs_manual_review": true | false
}"""


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class AIExtractor:
    """
    Abstraction layer over OpenAI. Swap the _client or model to change provider.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — AI extraction will fail gracefully.")
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None
        self._model = model

    async def extract(
        self,
        text: str,
        image_url: Optional[str] = None,
    ) -> IncidentExtraction:
        """
        Extract structured incident data from free-form text (and optional image).
        Returns IncidentExtraction with needs_manual_review=True on failure.
        """
        if self._client is None:
            logger.warning("AI client not available — returning manual review fallback.")
            return IncidentExtraction(
                needs_manual_review=True,
                confidence=0.0,
                failure_reason="AI client is unavailable",
            )

        for attempt in range(2):
            try:
                result = await self._call_api(text, image_url)
                return result
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"AI extraction attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    logger.error("Both AI extraction attempts failed — flagging for manual review.")
                    return IncidentExtraction(
                        needs_manual_review=True,
                        confidence=0.0,
                        failure_reason=type(e).__name__,
                    )
            except Exception as e:
                logger.error(f"AI extraction unexpected error: {e}")
                return IncidentExtraction(
                    needs_manual_review=True,
                    confidence=0.0,
                    failure_reason=type(e).__name__,
                )

        return IncidentExtraction(
            needs_manual_review=True,
            confidence=0.0,
            failure_reason="Extraction retry limit reached",
        )

    async def _call_api(self, text: str, image_url: Optional[str]) -> IncidentExtraction:
        messages_content: list = [{"type": "text", "text": text}]

        if image_url:
            messages_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "low",
                },
            })
            # Add explicit image warning per spec §AI Reliability Rules Rule 4
            messages_content.append({
                "type": "text",
                "text": (
                    "An image has been provided. You may note visual observations "
                    "about the scene. Do NOT assert accessibility attributes of resources "
                    "from the image alone — mark them null and set needs_manual_review: true "
                    "if the image shows potential accessibility concerns."
                ),
            })

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": messages_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # low temperature for consistent structured output
            max_tokens=512,
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)
        extraction = IncidentExtraction(**data)
        logger.info("Structured extraction completed successfully.")

        # An empty result means requirements are unknown, not absent.  Flag it
        # so the case is routed to a coordinator instead of implying it is safe.
        if not self.to_person_profile(extraction).has_any_constraints():
            extraction.needs_manual_review = True
            logger.warning("AI extraction returned no accessibility constraints.")

        return extraction

    def to_person_profile(self, extraction: IncidentExtraction) -> PersonProfile:
        """Convert an IncidentExtraction into a PersonProfile."""
        return PersonProfile(
            age_group=extraction.age_group or AgeGroup.unknown,
            mobility=extraction.mobility or MobilityType.unknown,
            wheelchair_required=extraction.wheelchair_required,
            stairs_allowed=extraction.stairs_allowed,
            ramp_usable=extraction.ramp_usable,
            caregiver_required=extraction.caregiver_required,
            accessible_transport_required=extraction.accessible_transport_required,
            visual_communication_required=extraction.visual_communication_required,
            hearing_support_required=extraction.hearing_support_required,
            language=extraction.language,
            notes=extraction.notes,
        )

    def to_constraints(self, extraction: IncidentExtraction) -> list[Constraint]:
        """Create an auditable record for every extracted requirement."""
        field_labels = {
            "wheelchair_required": "wheelchair_required",
            "stairs_allowed": "stairs_allowed",
            "ramp_usable": "ramp_usable",
            "caregiver_required": "caregiver_required",
            "accessible_transport_required": "accessible_transport_required",
            "visual_communication_required": "visual_communication_required",
            "hearing_support_required": "hearing_support_required",
        }
        return [
            Constraint(
                constraint_type=label,
                value=str(value).lower(),
                source=ConstraintSource.ai,
                confidence=extraction.confidence,
            )
            for field, label in field_labels.items()
            if (value := getattr(extraction, field)) is not None
        ]


# Module-level singleton
extractor = AIExtractor()
