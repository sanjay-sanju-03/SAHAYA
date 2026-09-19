"""
SAHAYA — Clarification Question Generator.

Determines what critical information is still missing from an incident
and returns the single most important question to ask.

Priority order (from spec §3.1 Feature 3):
  1. Location (needed for any dispatch)
  2. Mobility / wheelchair status (critical constraint)
  3. Stairs (if mobility known)
  4. Ramp usability (if wheelchair + stairs blocked)
  5. Accessible transport
  6. Caregiver requirement
  7. Visual/hearing support
"""
from __future__ import annotations

from typing import Optional, Set
from pydantic import BaseModel

from app.models.incident import PersonProfile


# Ask only for information required by the core shelter/transport decision.
# Visual and hearing support remain supported by the constraint engine when
# explicitly extracted, but should not create extra questions in the MVP flow.
MVP_CRITICAL_FIELDS = (
    "location_text",
    "wheelchair_required",
    "stairs_allowed",
    "accessible_transport_required",
    "caregiver_required",
)


class ClarificationQuestion(BaseModel):
    key: str                      # field name to update on answer
    question: str                 # human-readable question text
    question_ml: str              # Malayalam translation for demo
    options: list[str]            # ["YES", "NO", "NOT_SURE"]
    priority: int                 # lower = higher priority


def get_next_question(
    person: PersonProfile,
    location_text: Optional[str],
    answered_keys: Optional[Set[str]] = None,
) -> Optional[ClarificationQuestion]:
    """
    Returns the single highest-priority missing question, or None if complete.
    """
    questions: list[ClarificationQuestion] = []
    answered_keys = answered_keys or set()

    # Priority 1 — Location
    if (
        "location_text" not in answered_keys
        and (not location_text or location_text.strip().lower() in ("unknown", "", "unknown — clarification needed"))
    ):
        questions.append(ClarificationQuestion(
            key="location_text",
            question="What is the exact location of the person needing help?",
            question_ml="സഹായം ആവശ്യമുള്ള വ്യക്തിയുടെ കൃത്യമായ സ്ഥലം എവിടെ?",
            options=["(Free text — enter address or landmark)"],
            priority=1,
        ))

    # Priority 2 — Wheelchair / mobility status
    if person.wheelchair_required is None and "wheelchair_required" not in answered_keys:
        questions.append(ClarificationQuestion(
            key="wheelchair_required",
            question="Does the person use a wheelchair?",
            question_ml="ആ വ്യക്തി വീൽചെയർ ഉപയോഗിക്കുന്നുണ്ടോ?",
            options=["YES", "NO", "NOT_SURE"],
            priority=2,
        ))

    # Priority 3 — Stairs (only if mobility is known)
    if (
        person.wheelchair_required is not None
        and person.stairs_allowed is None
        and "stairs_allowed" not in answered_keys
    ):
        questions.append(ClarificationQuestion(
            key="stairs_allowed",
            question="Can the person use stairs?",
            question_ml="ആ വ്യക്തിക്ക് പടികൾ ഉപയോഗിക്കാൻ കഴിയുമോ?",
            options=["YES", "NO", "NOT_SURE"],
            priority=3,
        ))

    # Priority 4 — Ramp (if wheelchair + stairs not allowed)
    if (
        person.wheelchair_required is True
        and person.stairs_allowed is False
        and person.ramp_usable is None
        and "ramp_usable" not in answered_keys
    ):
        questions.append(ClarificationQuestion(
            key="ramp_usable",
            question="Can the person use a ramp?",
            question_ml="ആ വ്യക്തിക്ക് റാമ്പ് ഉപയോഗിക്കാൻ കഴിയുമോ?",
            options=["YES", "NO", "NOT_SURE"],
            priority=4,
        ))

    # Priority 5 — Accessible transport
    if (
        person.wheelchair_required is True
        and person.accessible_transport_required is None
        and "accessible_transport_required" not in answered_keys
    ):
        questions.append(ClarificationQuestion(
            key="accessible_transport_required",
            question="Does the person need wheelchair-accessible transport?",
            question_ml="വ്യക്തിക്ക് വീൽചെയർ ആക്സസ് ഉള്ള വാഹനം ആവശ്യമുണ്ടോ?",
            options=["YES", "NO", "NOT_SURE"],
            priority=5,
        ))

    # Priority 6 — Caregiver
    if person.caregiver_required is None and "caregiver_required" not in answered_keys:
        questions.append(ClarificationQuestion(
            key="caregiver_required",
            question="Does the person require a caregiver or personal assistant?",
            question_ml="വ്യക്തിക്ക് ഒരു പരിചരണക്കാരൻ ആവശ്യമുണ്ടോ?",
            options=["YES", "NO", "NOT_SURE"],
            priority=6,
        ))

    # Enforce the MVP scope even if optional question definitions are added later.
    questions = [question for question in questions if question.key in MVP_CRITICAL_FIELDS]

    if not questions:
        return None

    # Return only the highest-priority question
    questions.sort(key=lambda q: q.priority)
    return questions[0]


def apply_answer(person: PersonProfile, key: str, answer: str) -> PersonProfile:
    """
    Apply a clarification answer to the person profile and return the updated profile.
    answer: "YES" | "NO" | "NOT_SURE" | free text (for location)
    """
    data = person.model_dump()

    def to_bool(a: str) -> Optional[bool]:
        a = a.upper()
        if a == "YES":
            return True
        if a == "NO":
            return False
        return None  # NOT_SURE → remains unknown

    if key == "location_text":
        # location is stored on incident, not person — caller handles this
        return person

    bool_keys = {
        "wheelchair_required",
        "stairs_allowed",
        "ramp_usable",
        "caregiver_required",
        "accessible_transport_required",
        "visual_communication_required",
        "hearing_support_required",
    }

    if key in bool_keys:
        data[key] = to_bool(answer)

    return PersonProfile(**data)
