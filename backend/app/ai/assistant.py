"""Evidence-grounded, read-only SAHAYA Assistant.

The assistant receives an explicit snapshot; it never queries or modifies
application state through model tools. A deterministic fallback preserves the
safety contract whenever an LLM is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI

from app.models.assistant import AssistantEvidence, AssistantResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SAHAYA's read-only evidence assistant.
Answer ONLY from the supplied JSON evidence context. Never invent missing
evidence or capability values. Preserve SAFE, UNKNOWN, BLOCKED, and
NOT_APPLICABLE exactly. Resource compatibility and route compatibility are
separate evidence layers. Never recommend, make, or confirm an assignment,
override, route change, verification, or dispatch. If asked to perform an
action, state that a coordinator must decide. Respond in the requested
language, concisely, and cite the relevant version or source when possible."""


def _value(value: Any) -> str:
    return "YES" if value is True else "NO" if value is False else "UNKNOWN"


def _check_reasons(report: dict[str, Any], status: str) -> list[str]:
    return [
        check.get("reason", "")
        for check in report.get("checks", [])
        if check.get("status") == status and check.get("reason")
    ]


class SahayaAssistant:
    def __init__(self) -> None:
        key = os.getenv("OPENAI_API_KEY")
        self._client = AsyncOpenAI(api_key=key) if key else None
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")

    async def answer(
        self, question: str, language: str, context: dict[str, Any], evidence: AssistantEvidence
    ) -> AssistantResponse:
        # Action requests receive a deterministic guardrail before any model call.
        action_words = ("assign", "confirm", "override", "dispatch", "verify", "change", "update")
        if any(word in question.lower() for word in action_words):
            answer = (
                "എനിക്ക് assignment നടത്താനോ സ്ഥിരീകരിക്കാനോ കഴിയില്ല. നിലവിലെ evidence പരിശോധിച്ച് അന്തിമ തീരുമാനം coordinator എടുക്കണം."
                if language == "ml"
                else "I cannot make or confirm assignments. The current evidence can inform a coordinator, who must make the final decision."
            )
            return AssistantResponse(answer=answer, language=language, evidence=evidence)

        # The LLM is optional presentation over the fixed snapshot. Fallback is
        # deliberately deterministic so missing API access never changes facts.
        if self._client and os.getenv("SAHAYA_ASSISTANT_USE_LLM", "true").lower() == "true":
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=0,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps({
                            "language": language, "question": question, "evidence": context
                        }, default=str)},
                    ],
                )
                text = response.choices[0].message.content
                if text:
                    return AssistantResponse(answer=text.strip(), language=language, evidence=evidence)
            except Exception as exc:  # Safe factual fallback, never a fabricated answer.
                logger.warning("Assistant LLM unavailable; using deterministic evidence answer: %s", type(exc).__name__)

        return AssistantResponse(
            answer=self._deterministic_answer(question, language, context),
            language=language,
            evidence=evidence,
        )

    def _deterministic_answer(self, question: str, language: str, context: dict[str, Any]) -> str:
        resource = context["resource"]
        evaluation = context.get("resource_evaluation") or {}
        route = context.get("route_evaluation") or {}
        observation = context.get("route_observation") or {}
        q = question.lower()
        resource_status = evaluation.get("status", "UNKNOWN")
        route_status = route.get("status", "UNKNOWN")

        if "change" in q or "after" in q:
            recent = [entry.get("description", "") for entry in context.get("audit", []) if entry.get("description")][-3:]
            detail = " ".join(recent) if recent else "No recorded change is available in the current audit history."
            return (
                f"Recent audit evidence: {detail}"
                if language == "en"
                else f"സമീപകാല audit evidence: {detail}"
            )
        if "when" in q and "verif" in q:
            verified_at = resource.get("capabilities", {}).get("last_verified_at")
            source = resource.get("capabilities", {}).get("verified_by")
            if verified_at:
                return (
                    f"The resource record was last verified at {verified_at} by {source or 'an unrecorded verifier'}."
                    if language == "en"
                    else f"Resource record അവസാനമായി {verified_at} ന് സ്ഥിരീകരിച്ചു. സ്ഥിരീകരിച്ചത്: {source or 'രേഖപ്പെടുത്തിയിട്ടില്ല'}."
                )
            return "The resource record has no verified timestamp." if language == "en" else "Resource record-ൽ verified timestamp ലഭ്യമല്ല."
        if "capacity" in q or "capacity" in question.lower():
            remaining = resource["capacity"].get("accessible_spaces_remaining")
            if remaining is None:
                return "Accessible capacity is not verified in the current resource record." if language == "en" else "നിലവിലെ resource record-ൽ accessible capacity സ്ഥിരീകരിച്ചിട്ടില്ല."
            return (
                f"{resource['name']} has {remaining} accessible space(s) remaining."
                if language == "en"
                else f"{resource['name']} ൽ {remaining} accessible space(s) ശേഷിക്കുന്നു."
            )
        if "route" in q or "hazard" in q:
            reasons = _check_reasons(route, "BLOCKED") or _check_reasons(route, "UNKNOWN")
            detail = reasons[0] if reasons else "No current route observation is available."
            if language == "ml":
                return f"Resource compatibility {resource_status} ആണ്; route compatibility {route_status} ആണ്. {detail} Route version {observation.get('route_version', 'unknown')}."
            return f"Resource compatibility is {resource_status}; route compatibility is {route_status}. {detail} Route version {observation.get('route_version', 'unknown')}."
        if resource_status == "BLOCKED":
            reasons = _check_reasons(evaluation, "BLOCKED")
            detail = " ".join(reasons) or "A required capability conflicts with this resource."
        elif resource_status == "UNKNOWN":
            reasons = _check_reasons(evaluation, "UNKNOWN")
            detail = " ".join(reasons) or "Required capability evidence is not verified."
        else:
            detail = "All applicable requirements are verified for this resource."
        if language == "ml":
            return f"{resource['name']} {resource_status} ആണ്. {detail} Resource version {resource.get('resource_version', 0)}."
        return f"{resource['name']} is {resource_status}. {detail} Resource version {resource.get('resource_version', 0)}."


assistant = SahayaAssistant()
