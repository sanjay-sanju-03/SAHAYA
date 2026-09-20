"""Grounding regression tests for the read-only SAHAYA Assistant."""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.ai.assistant import SahayaAssistant
from app.engine.constraint_engine import evaluate
from app.engine.route_engine import evaluate_route
from app.models.assistant import AssistantEvidence
from app.models.route import RouteObservation
from app.seed_data import DEMO_INCIDENT, RESOURCES_BY_ID


def context_for(resource_id: str, route_hazard: bool | None = None):
    resource = RESOURCES_BY_ID[resource_id]
    evaluation = evaluate(DEMO_INCIDENT.person, resource, DEMO_INCIDENT.id).model_dump(mode="json")
    route = None
    observation = None
    if route_hazard is not None:
        route_observation = RouteObservation(
            incident_id=DEMO_INCIDENT.id,
            resource_id=resource.id,
            route_exists=True,
            known_hazard_on_route=route_hazard,
            accessible_for_person=True,
            source="Coordinator inspection",
            observed_at=datetime.utcnow(),
            route_version=2,
        )
        observation = route_observation.model_dump(mode="json")
        route = evaluate_route(DEMO_INCIDENT.person, resource, route_observation, requirement_version=1).model_dump(mode="json")
    return {
        "resource": {
            **resource.model_dump(mode="json"),
            "capacity": {"accessible_spaces_remaining": resource.accessible_spaces_remaining()},
        },
        "resource_evaluation": evaluation,
        "route_evaluation": route,
        "route_observation": observation,
    }


@pytest.fixture
def assistant():
    return SahayaAssistant()


def test_blocked_answer_uses_actual_conflict(assistant):
    answer = assistant._deterministic_answer("Why is Hall A BLOCKED?", "en", context_for("shelter-a"))
    assert "BLOCKED" in answer
    assert "wheelchair" in answer.lower() or "stairs" in answer.lower()


def test_unknown_answer_does_not_invent_capability(assistant):
    answer = assistant._deterministic_answer("Why is Center B UNKNOWN?", "en", context_for("shelter-b"))
    assert "UNKNOWN" in answer
    assert "not verified" in answer.lower() or "unknown" in answer.lower()


def test_capacity_answer_returns_structured_value(assistant):
    expected = RESOURCES_BY_ID["shelter-c"].accessible_spaces_remaining()
    answer = assistant._deterministic_answer("How much accessible capacity remains?", "en", context_for("shelter-c"))
    assert str(expected) in answer


def test_route_and_resource_verdicts_remain_separate(assistant):
    answer = assistant._deterministic_answer(
        "Why is the route BLOCKED while the resource is SAFE?", "en", context_for("shelter-c", route_hazard=True)
    )
    assert "Resource compatibility is SAFE" in answer
    assert "route compatibility is BLOCKED" in answer
    assert "hazard" in answer.lower()


@pytest.mark.asyncio
async def test_assignment_request_is_refused(assistant):
    response = await assistant.answer(
        "Can you assign Hall C to this person?", "en", context_for("shelter-c"),
        AssistantEvidence(requirement_version=1, resource_version=0),
    )
    assert "cannot make or confirm assignments" in response.answer
