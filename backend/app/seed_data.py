"""
SAHAYA — Deterministic seed data for demo and testing.

Shelters are intentionally designed to produce BLOCKED / UNKNOWN / SAFE
for a wheelchair user who cannot use stairs, demonstrating all three states.

The demo-001 incident is a pre-extracted case (no AI needed) for the fallback path.
"""
from __future__ import annotations

from datetime import datetime
from app.models.incident import (
    CasePerson,
    Incident, PersonProfile, Constraint, ConstraintSource,
    IncidentType, IncidentStatus, Urgency, MobilityType, AgeGroup,
)
from app.models.resource import Resource, ResourceCapabilities, ResourceType, ResourceStatus


# ---------------------------------------------------------------------------
# RESOURCES
# ---------------------------------------------------------------------------

SEED_RESOURCES: list[Resource] = [
    # ------------------------------------------------------------------
    # Shelter A — WILL BE BLOCKED for wheelchair + no-stairs person
    # ------------------------------------------------------------------
    Resource(
        id="shelter-a",
        type=ResourceType.shelter,
        name="Community Hall A",
        location_text="Ward 4, Near Kozhikode Junction",
        status=ResourceStatus.available,
        capacity=80,
        available_capacity=45,
        current_occupancy=35,
        accessible_capacity=0,
        accessible_occupied=0,
        caregiver_capacity=4,
        caregiver_occupied=1,
        capabilities=ResourceCapabilities(
            ground_floor=False,          # upper floor
            stairs_required=True,        # must climb stairs
            ramp=False,                  # no ramp
            wheelchair_access=False,     # not accessible
            accessible_toilet=False,
            caregiver_support=True,
            visual_communication_support=False,
            hearing_support=True,
            last_verified_at=datetime(2026, 9, 15),
            verified_by="District Coordinator",
        ),
        is_demo=True,
    ),

    # ------------------------------------------------------------------
    # Shelter B — WILL BE UNKNOWN (accessibility info missing)
    # ------------------------------------------------------------------
    Resource(
        id="shelter-b",
        type=ResourceType.shelter,
        name="Community Center B",
        location_text="Block 7, Elathur Road",
        status=ResourceStatus.available,
        capacity=60,
        available_capacity=30,
        current_occupancy=30,
        accessible_capacity=None,
        accessible_occupied=None,
        caregiver_capacity=None,
        caregiver_occupied=None,
        capabilities=ResourceCapabilities(
            ground_floor=None,           # unknown
            stairs_required=None,        # unknown
            ramp=None,                   # unknown
            wheelchair_access=None,      # unknown — triggers UNKNOWN verdict
            accessible_toilet=None,
            caregiver_support=None,
            visual_communication_support=None,
            hearing_support=None,
            last_verified_at=None,       # never verified
            verified_by=None,
        ),
        is_demo=True,
    ),

    # ------------------------------------------------------------------
    # Shelter C — WILL BE SAFE (fully accessible, all verified)
    # ------------------------------------------------------------------
    Resource(
        id="shelter-c",
        type=ResourceType.shelter,
        name="Community Hall C",
        location_text="Civic Centre Road, Calicut",
        status=ResourceStatus.available,
        capacity=50,
        available_capacity=21,
        current_occupancy=29,
        accessible_capacity=8,
        accessible_occupied=5,
        caregiver_capacity=4,
        caregiver_occupied=2,
        capabilities=ResourceCapabilities(
            ground_floor=True,           # ground floor
            stairs_required=False,       # no stairs required
            ramp=True,                   # ramp available
            wheelchair_access=True,      # fully accessible
            accessible_toilet=True,
            caregiver_support=True,
            visual_communication_support=True,
            hearing_support=True,
            last_verified_at=datetime(2026, 9, 19),
            verified_by="NGO Field Team",
        ),
        is_demo=True,
    ),

    # ------------------------------------------------------------------
    # Vehicle 1 — standard ambulance (no wheelchair lift) → BLOCKED
    # ------------------------------------------------------------------
    Resource(
        id="vehicle-1",
        type=ResourceType.vehicle,
        name="Ambulance Unit 1",
        location_text="KSRTC Depot, Calicut",
        status=ResourceStatus.available,
        capacity=4,
        available_capacity=4,
        current_occupancy=0,
        capabilities=ResourceCapabilities(
            wheelchair_transport=False,  # no wheelchair lift
            caregiver_support=True,
        ),
        is_demo=True,
    ),

    # ------------------------------------------------------------------
    # Vehicle 2 — accessible van → SAFE for wheelchair transport
    # ------------------------------------------------------------------
    Resource(
        id="vehicle-2",
        type=ResourceType.vehicle,
        name="Accessible Van – Unit 2",
        location_text="Civil Station, Calicut",
        status=ResourceStatus.available,
        capacity=3,
        available_capacity=3,
        current_occupancy=0,
        capabilities=ResourceCapabilities(
            wheelchair_transport=True,   # wheelchair lift installed
            caregiver_support=True,
            last_verified_at=datetime(2026, 9, 18),
            verified_by="District Transport Officer",
        ),
        is_demo=True,
    ),
]

# ---------------------------------------------------------------------------
# DEMO INCIDENT — pre-extracted, no AI call needed
# Simulates: "വീട്ടിൽ വെള്ളം കയറുന്നു. അമ്മ വീൽചെയറിലാണ്. അവൾക്ക് പടികൾ ഇറങ്ങാൻ കഴിയില്ല."
# (Flood at home. Mother is in a wheelchair. She cannot use stairs.)
# ---------------------------------------------------------------------------

DEMO_PERSON = PersonProfile(
    age_group=AgeGroup.elderly,
    mobility=MobilityType.wheelchair,
    wheelchair_required=True,
    stairs_allowed=False,
    ramp_usable=None,
    caregiver_required=True,
    accessible_transport_required=True,
    language="ml",
)

DEMO_INCIDENT = Incident(
    id="demo-001",
    created_at=datetime(2026, 9, 19, 22, 0, 0),
    updated_at=datetime(2026, 9, 19, 22, 5, 0),
    status=IncidentStatus.review_required,
    incident_type=IncidentType.flood,
    urgency=Urgency.high,
    location_text="Unknown — clarification needed",
    original_text=(
        "വീട്ടിൽ വെള്ളം കയറുന്നു. അമ്മ വീൽചെയറിലാണ്. "
        "അവൾക്ക് പടികൾ ഇറങ്ങാൻ കഴിയില്ല."
    ),
    person=DEMO_PERSON.model_copy(deep=True),
    ai_person=DEMO_PERSON.model_copy(deep=True),
    constraints=[
        Constraint(
            constraint_type="mobility",
            value="wheelchair",
            source=ConstraintSource.ai,
            confidence=0.97,
            verified=True,
        ),
        Constraint(
            constraint_type="stairs",
            value="prohibited",
            source=ConstraintSource.ai,
            confidence=0.95,
            verified=True,
        ),
        Constraint(
            constraint_type="location",
            value="unknown",
            source=ConstraintSource.system,
            confidence=1.0,
            verified=False,
        ),
    ],
    extraction_confidence=0.94,
    needs_manual_review=False,
)

DEMO_GROUP_INCIDENT = Incident(
    id="demo-group-001",
    status=IncidentStatus.ready_for_evaluation,
    incident_type=IncidentType.flood,
    urgency=Urgency.high,
    location_text="Kozhikode",
    original_text="Seeded multi-person emergency demonstration.",
)

DEMO_GROUP_PEOPLE = [
    CasePerson(id="demo-group-person-1", incident_id="demo-group-001", display_name="Person 1", ai_person=PersonProfile(wheelchair_required=True, stairs_allowed=False, hearing_support_required=True), person=PersonProfile(wheelchair_required=True, stairs_allowed=False, hearing_support_required=True), requirements_reviewed=True, requirement_version=1),
    CasePerson(id="demo-group-person-2", incident_id="demo-group-001", display_name="Person 2", ai_person=PersonProfile(caregiver_required=True), person=PersonProfile(caregiver_required=True), requirements_reviewed=True, requirement_version=1),
    CasePerson(id="demo-group-person-3", incident_id="demo-group-001", display_name="Person 3", ai_person=PersonProfile(), person=PersonProfile(), requirements_reviewed=True, requirement_version=1),
]

# ---------------------------------------------------------------------------
# Helper: resource lookup by ID
# ---------------------------------------------------------------------------

RESOURCES_BY_ID: dict[str, Resource] = {r.id: r for r in SEED_RESOURCES}
