"""
SAHAYA — Constraint Engine Unit Tests.

These tests verify that the deterministic constraint engine correctly produces
BLOCKED / UNKNOWN / SAFE for every relevant combination.

Run with: cd backend && pytest tests/test_constraint_engine.py -v
"""
import sys
import os

# Ensure backend/app is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError

from app.engine.constraint_engine import evaluate
from app.ai.extractor import IncidentExtraction
from app.ai.clarifier import get_next_question
from app.models.evaluation import EvaluationStatus, CheckStatus
from app.models.incident import PersonProfile, MobilityType, AgeGroup
from app.models.resource import Resource, ResourceCapabilities, ResourceType, ResourceStatus


# ---------------------------------------------------------------------------
# Fixtures — person profiles
# ---------------------------------------------------------------------------

def wheelchair_person(stairs_allowed: bool = False, ramp_usable=None, caregiver=True, transport=True) -> PersonProfile:
    return PersonProfile(
        age_group=AgeGroup.elderly,
        mobility=MobilityType.wheelchair,
        wheelchair_required=True,
        stairs_allowed=stairs_allowed,
        ramp_usable=ramp_usable,
        caregiver_required=caregiver,
        accessible_transport_required=transport,
    )


def ambulatory_person() -> PersonProfile:
    return PersonProfile(
        age_group=AgeGroup.adult,
        mobility=MobilityType.ambulatory,
        wheelchair_required=False,
        stairs_allowed=True,
    )


def bedridden_person() -> PersonProfile:
    return PersonProfile(
        age_group=AgeGroup.elderly,
        mobility=MobilityType.bedridden,
        wheelchair_required=True,
        stairs_allowed=False,
        caregiver_required=True,
        accessible_transport_required=True,
    )


def shelter(
    wheelchair_access=None,
    stairs_required=None,
    ramp=None,
    caregiver_support=None,
    available_capacity=20,
) -> Resource:
    return Resource(
        id="test-shelter",
        type=ResourceType.shelter,
        name="Test Shelter",
        status=ResourceStatus.available,
        available_capacity=available_capacity,
        capabilities=ResourceCapabilities(
            wheelchair_access=wheelchair_access,
            stairs_required=stairs_required,
            ramp=ramp,
            caregiver_support=caregiver_support,
        ),
    )


def vehicle(wheelchair_transport=None, available_capacity=3) -> Resource:
    return Resource(
        id="test-vehicle",
        type=ResourceType.vehicle,
        name="Test Vehicle",
        status=ResourceStatus.available,
        available_capacity=available_capacity,
        capabilities=ResourceCapabilities(wheelchair_transport=wheelchair_transport),
    )


# ---------------------------------------------------------------------------
# Tests — Wheelchair access
# ---------------------------------------------------------------------------

class TestWheelchairAccess:
    def test_wheelchair_user_inaccessible_shelter_is_blocked(self):
        person = wheelchair_person()
        resource = shelter(wheelchair_access=False, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.blocked, "Should be BLOCKED"
        blocked = [c for c in report.checks if c.constraint == "wheelchair_access"]
        assert len(blocked) == 1
        assert blocked[0].status == CheckStatus.blocked

    def test_wheelchair_user_unknown_accessibility_is_unknown(self):
        person = wheelchair_person()
        resource = shelter(wheelchair_access=None, stairs_required=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.unknown, "Should be UNKNOWN"

    def test_wheelchair_user_accessible_shelter_is_safe(self):
        person = wheelchair_person(stairs_allowed=True)
        resource = shelter(
            wheelchair_access=True,
            stairs_required=False,
            ramp=True,
            caregiver_support=True,
        )
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe, "Should be SAFE"

    def test_non_wheelchair_user_inaccessible_shelter_is_safe(self):
        person = ambulatory_person()
        resource = shelter(wheelchair_access=False, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        # Ambulatory person with no wheelchair req — should not fail on wheelchair_access
        assert report.status == EvaluationStatus.safe


# ---------------------------------------------------------------------------
# Tests — Stairs
# ---------------------------------------------------------------------------

class TestStairs:
    def test_no_stairs_person_stairs_required_shelter_is_blocked(self):
        """Core demo scenario: wheelchair user + stairs required = BLOCKED."""
        person = wheelchair_person(stairs_allowed=False)
        resource = shelter(wheelchair_access=False, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.blocked
        stairs_checks = [c for c in report.checks if c.constraint == "stairs"]
        assert any(c.status == CheckStatus.blocked for c in stairs_checks)

    def test_no_stairs_person_unknown_stairs_is_unknown(self):
        person = wheelchair_person(stairs_allowed=False)
        resource = shelter(wheelchair_access=True, stairs_required=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.unknown

    def test_no_stairs_person_no_stairs_required_is_safe(self):
        person = wheelchair_person(stairs_allowed=False, caregiver=True, transport=False)
        resource = shelter(
            wheelchair_access=True,
            stairs_required=False,
            caregiver_support=True,
            available_capacity=10,
        )
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe


# ---------------------------------------------------------------------------
# Tests — Transport
# ---------------------------------------------------------------------------

class TestTransport:
    def test_wheelchair_transport_required_no_lift_is_blocked(self):
        person = wheelchair_person(transport=True)
        resource = vehicle(wheelchair_transport=False)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.blocked

    def test_wheelchair_transport_required_unknown_lift_is_unknown(self):
        person = wheelchair_person(transport=True)
        resource = vehicle(wheelchair_transport=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.unknown

    def test_wheelchair_transport_available_is_safe(self):
        person = PersonProfile(
            wheelchair_required=True,
            accessible_transport_required=True,
            stairs_allowed=True,
        )
        resource = vehicle(wheelchair_transport=True)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe

    def test_vehicle_is_not_applicable_without_transport_requirement(self):
        """Shelter-only needs must not make a vehicle UNKNOWN."""
        person = PersonProfile(
            hearing_support_required=True,
            accessible_transport_required=False,
        )
        report = evaluate(person, vehicle(wheelchair_transport=None), "test-incident")
        assert report.status == EvaluationStatus.not_applicable
        assert report.total_checks == 0

    def test_mixed_wheelchair_and_hearing_case_scopes_requirements_by_resource_type(self):
        """A vehicle is not assessed for shelter-only communication needs."""
        person = PersonProfile(
            wheelchair_required=True,
            hearing_support_required=True,
            accessible_transport_required=False,
            caregiver_required=False,
        )
        hearing_accessible_shelter = Resource(
            id="mixed-shelter",
            type=ResourceType.shelter,
            name="Mixed Needs Shelter",
            status=ResourceStatus.available,
            available_capacity=20,
            capabilities=ResourceCapabilities(
                wheelchair_access=True,
                hearing_support=True,
            ),
        )

        shelter_report = evaluate(person, hearing_accessible_shelter, "test-incident")
        vehicle_report = evaluate(person, vehicle(wheelchair_transport=None), "test-incident")

        assert shelter_report.status == EvaluationStatus.safe
        assert {check.constraint for check in shelter_report.checks} == {"wheelchair_access", "hearing_support"}
        assert vehicle_report.status == EvaluationStatus.not_applicable


# ---------------------------------------------------------------------------
# Tests — Priority logic (BLOCKED overrides UNKNOWN)
# ---------------------------------------------------------------------------

class TestPriority:
    def test_blocked_overrides_unknown(self):
        """A BLOCKED check must prevent UNKNOWN from becoming the status."""
        person = wheelchair_person(stairs_allowed=False)
        # stairs_required is BLOCKED (True), wheelchair_access is UNKNOWN (None)
        resource = shelter(wheelchair_access=None, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.blocked, \
            "BLOCKED must override UNKNOWN — critical failure takes priority"

    def test_unknown_overrides_safe(self):
        """If one check is UNKNOWN and none are BLOCKED, result is UNKNOWN."""
        person = wheelchair_person(stairs_allowed=False, caregiver=False, transport=False)
        # stairs_required unknown → UNKNOWN; wheelchair_access known OK
        resource = shelter(wheelchair_access=True, stairs_required=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.unknown

    def test_all_safe_checks_produce_safe(self):
        person = PersonProfile(
            wheelchair_required=True,
            stairs_allowed=False,
            caregiver_required=True,
            accessible_transport_required=False,
        )
        resource = shelter(
            wheelchair_access=True,
            stairs_required=False,
            caregiver_support=True,
        )
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe


# ---------------------------------------------------------------------------
# Tests — Capacity
# ---------------------------------------------------------------------------

class TestCapacity:
    def test_zero_capacity_is_blocked(self):
        person = ambulatory_person()
        resource = shelter(available_capacity=0)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.blocked

    def test_unknown_capacity_is_unknown(self):
        person = ambulatory_person()
        resource = shelter(available_capacity=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.unknown

    def test_positive_capacity_passes(self):
        person = ambulatory_person()
        resource = shelter(available_capacity=10)
        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe


# ---------------------------------------------------------------------------
# Tests — Evidence trail
# ---------------------------------------------------------------------------

class TestEvidenceTrail:
    def test_report_contains_checks(self):
        person = wheelchair_person()
        resource = shelter(wheelchair_access=False, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        assert len(report.checks) > 0

    def test_blocked_report_has_blocked_checks(self):
        person = wheelchair_person()
        resource = shelter(wheelchair_access=False, stairs_required=True)
        report = evaluate(person, resource, "test-incident")
        assert report.blocked_checks > 0
        assert report.status_label == "BLOCKED — One or more requirements conflict"

    def test_safe_report_label(self):
        person = PersonProfile(
            wheelchair_required=True,
            stairs_allowed=True,
            caregiver_required=False,
            accessible_transport_required=False,
        )
        resource = shelter(wheelchair_access=True, stairs_required=False, available_capacity=10)
        report = evaluate(person, resource, "test-incident")
        assert report.status_label == "SAFE — All required capabilities verified"

    def test_unknown_report_label(self):
        person = wheelchair_person(caregiver=False, transport=False)
        resource = shelter(wheelchair_access=None, stairs_required=None)
        report = evaluate(person, resource, "test-incident")
        assert report.status_label == "UNKNOWN — Critical information not verified"


class TestPersonProfileConstraints:
    def test_empty_profile_has_no_constraints(self):
        assert PersonProfile().has_any_constraints() is False

    def test_profile_with_transport_requirement_has_constraints(self):
        assert PersonProfile(accessible_transport_required=True).has_any_constraints() is True


class TestExtractionContract:
    def test_explicit_accessibility_requirements_are_preserved(self):
        extraction = IncidentExtraction(
            wheelchair_required=True,
            stairs_allowed=False,
            accessible_transport_required=True,
            caregiver_required=None,
        )
        assert extraction.wheelchair_required is True
        assert extraction.stairs_allowed is False
        assert extraction.accessible_transport_required is True

    def test_unknown_model_key_is_rejected(self):
        with pytest.raises(ValidationError):
            IncidentExtraction(needs_wheelchair=True)

    def test_explicit_non_wheelchair_statements_are_preserved(self):
        extraction = IncidentExtraction(
            wheelchair_required=False,
            stairs_allowed=True,
            accessible_transport_required=False,
            caregiver_required=True,
        )
        assert extraction.wheelchair_required is False
        assert extraction.stairs_allowed is True
        assert extraction.accessible_transport_required is False
        assert extraction.caregiver_required is True


class TestClarificationFlow:
    def test_not_sure_answer_advances_without_marking_requirement_false(self):
        person = PersonProfile(wheelchair_required=None)
        question = get_next_question(
            person,
            location_text="Ward 4",
            answered_keys={"wheelchair_required"},
        )
        assert person.wheelchair_required is None
        assert question is not None
        assert question.key == "caregiver_required"

    def test_optional_sensory_fields_do_not_create_mvp_questions(self):
        question = get_next_question(
            PersonProfile(
                wheelchair_required=False,
                stairs_allowed=True,
                caregiver_required=False,
            ),
            location_text="Ward 4",
        )
        assert question is None


class TestActiveConstraintEvaluation:
    def _caregiver_only_person(self) -> PersonProfile:
        return PersonProfile(
            wheelchair_required=False,
            stairs_allowed=True,
            accessible_transport_required=False,
            caregiver_required=True,
        )

    def test_only_required_caregiver_capability_is_evaluated(self):
        report = evaluate(
            self._caregiver_only_person(),
            shelter(
                wheelchair_access=None,
                stairs_required=None,
                caregiver_support=True,
                available_capacity=20,
            ),
            "test-incident",
        )
        assert report.status == EvaluationStatus.safe
        assert len(report.checks) == 1
        assert report.checks[0].constraint == "caregiver_support"
        assert report.checks[0].status == CheckStatus.safe

    def test_unknown_required_caregiver_support_is_unknown(self):
        report = evaluate(
            self._caregiver_only_person(),
            shelter(caregiver_support=None, available_capacity=20),
            "test-incident",
        )
        assert report.status == EvaluationStatus.unknown

    def test_missing_required_caregiver_support_is_blocked(self):
        report = evaluate(
            self._caregiver_only_person(),
            shelter(caregiver_support=False, available_capacity=20),
            "test-incident",
        )
        assert report.status == EvaluationStatus.blocked


class TestAssistiveCommunication:
    def test_seeded_shelters_distinguish_communication_support(self):
        from app.seed_data import RESOURCES_BY_ID

        person = PersonProfile(
            visual_communication_required=True,
            hearing_support_required=True,
        )

        assert evaluate(person, RESOURCES_BY_ID["shelter-a"]).status == EvaluationStatus.blocked
        assert evaluate(person, RESOURCES_BY_ID["shelter-b"]).status == EvaluationStatus.unknown
        assert evaluate(person, RESOURCES_BY_ID["shelter-c"]).status == EvaluationStatus.safe

    def test_hearing_only_requirement_does_not_activate_visual_communication(self):
        person = PersonProfile(hearing_support_required=True)
        resource = Resource(
            id="hearing-only-shelter",
            type=ResourceType.shelter,
            name="Hearing Support Shelter",
            status=ResourceStatus.available,
            available_capacity=20,
            capabilities=ResourceCapabilities(
                hearing_support=True,
                visual_communication_support=False,
            ),
        )

        report = evaluate(person, resource, "test-incident")
        assert report.status == EvaluationStatus.safe
        assert len(report.checks) == 1
        assert report.checks[0].constraint == "hearing_support"

    def test_clarifier_skips_explicit_false_values(self):
        question = get_next_question(
            PersonProfile(
                wheelchair_required=False,
                stairs_allowed=True,
                accessible_transport_required=False,
                caregiver_required=True,
            ),
            location_text="Ward 4",
        )
        assert question is None


# ---------------------------------------------------------------------------
# Integration — Demo scenario (spec §27)
# ---------------------------------------------------------------------------

class TestDemoScenario:
    """Reproduce the exact 3-minute judge demo from the spec."""

    def _demo_person(self) -> PersonProfile:
        """
        From Malayalam: Mother is wheelchair user, cannot use stairs.
        After clarification: can use ramp.
        """
        return PersonProfile(
            age_group=AgeGroup.elderly,
            mobility=MobilityType.wheelchair,
            wheelchair_required=True,
            stairs_allowed=False,
            ramp_usable=True,
            caregiver_required=True,
            accessible_transport_required=True,
        )

    def test_shelter_a_is_blocked(self):
        """Community Hall A — stairs required, no wheelchair access → BLOCKED."""
        person = self._demo_person()
        from app.seed_data import RESOURCES_BY_ID
        shelter_a = RESOURCES_BY_ID["shelter-a"]
        report = evaluate(person, shelter_a, "demo-001")
        assert report.status == EvaluationStatus.blocked, \
            f"Shelter A should be BLOCKED, got {report.status}"

    def test_shelter_b_is_unknown(self):
        """Community Center B — all capabilities unknown → UNKNOWN."""
        person = self._demo_person()
        from app.seed_data import RESOURCES_BY_ID
        shelter_b = RESOURCES_BY_ID["shelter-b"]
        report = evaluate(person, shelter_b, "demo-001")
        assert report.status == EvaluationStatus.unknown, \
            f"Shelter B should be UNKNOWN, got {report.status}"

    def test_shelter_c_is_safe(self):
        """Community Hall C — fully accessible, all verified → SAFE."""
        person = self._demo_person()
        from app.seed_data import RESOURCES_BY_ID
        shelter_c = RESOURCES_BY_ID["shelter-c"]
        report = evaluate(person, shelter_c, "demo-001")
        assert report.status == EvaluationStatus.safe, \
            f"Shelter C should be SAFE, got {report.status}"

    def test_demo_produces_all_three_statuses(self):
        """The demo must produce BLOCKED, UNKNOWN, and SAFE for distinct shelters."""
        person = self._demo_person()
        from app.seed_data import RESOURCES_BY_ID, SEED_RESOURCES
        shelters = [r for r in SEED_RESOURCES if r.type.value == "shelter"]
        statuses = {evaluate(person, s, "demo-001").status for s in shelters}
        assert EvaluationStatus.blocked in statuses, "Must have a BLOCKED shelter"
        assert EvaluationStatus.unknown in statuses, "Must have an UNKNOWN shelter"
        assert EvaluationStatus.safe in statuses, "Must have a SAFE shelter"
