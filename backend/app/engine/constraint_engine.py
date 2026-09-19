"""
SAHAYA — Deterministic Constraint Engine.

This module is the technical heart of SAHAYA.

Architecture principle:
  AI understands → Rules verify → Humans decide.

No LLM calls exist in this module. The engine is a pure Python function
that takes a PersonProfile and a Resource, applies deterministic rules,
and returns an EvaluationReport with SAFE / UNKNOWN / BLOCKED status
and a full evidence trail.

Decision priority (from spec §17):
  1. Any BLOCKED check → overall BLOCKED  (critical failure)
  2. Any UNKNOWN check → overall UNKNOWN  (unverified requirement)
  3. All checks pass   → overall SAFE

A single critical failure cannot be overridden by positive attributes.
"""
from __future__ import annotations

from app.models.evaluation import (
    CheckStatus,
    EvaluationCheck,
    EvaluationReport,
    EvaluationStatus,
)
from app.models.incident import PersonProfile
from app.models.resource import Resource


# ---------------------------------------------------------------------------
# Internal helpers — build typed check results
# ---------------------------------------------------------------------------

def _safe(constraint: str, requirement: str, resource_val: str, evidence: str, reason: str) -> EvaluationCheck:
    return EvaluationCheck(
        constraint=constraint,
        status=CheckStatus.safe,
        requirement_label=requirement,
        resource_label=resource_val,
        evidence_label=evidence,
        reason=reason,
        resource_value=resource_val,
    )


def _unknown(constraint: str, requirement: str, resource_val: str, evidence: str, reason: str) -> EvaluationCheck:
    return EvaluationCheck(
        constraint=constraint,
        status=CheckStatus.unknown,
        requirement_label=requirement,
        resource_label=resource_val,
        evidence_label=evidence,
        reason=reason,
        resource_value=resource_val,
    )


def _blocked(constraint: str, requirement: str, resource_val: str, evidence: str, reason: str) -> EvaluationCheck:
    return EvaluationCheck(
        constraint=constraint,
        status=CheckStatus.blocked,
        requirement_label=requirement,
        resource_label=resource_val,
        evidence_label=evidence,
        reason=reason,
        resource_value=resource_val,
    )


# ---------------------------------------------------------------------------
# Status label strings (spec §User Review Required)
# ---------------------------------------------------------------------------

STATUS_LABELS: dict[EvaluationStatus, str] = {
    EvaluationStatus.safe: "SAFE — All required capabilities verified",
    EvaluationStatus.unknown: "UNKNOWN — Critical information not verified",
    EvaluationStatus.blocked: "BLOCKED — One or more requirements conflict",
    EvaluationStatus.not_applicable: "NOT APPLICABLE — This resource type is not required for the current case",
}


# ---------------------------------------------------------------------------
# Core evaluate function
# ---------------------------------------------------------------------------

def evaluate(person: PersonProfile, resource: Resource, incident_id: str = "") -> EvaluationReport:
    """
    Evaluate whether a resource satisfies a person's accessibility requirements.

    Args:
        person:      Structured accessibility profile extracted from the incident.
        resource:    A candidate resource with nullable capability fields.
        incident_id: The parent incident ID (for the report record).

    Returns:
        EvaluationReport with status SAFE | UNKNOWN | BLOCKED and full evidence.
    """
    caps = resource.capabilities
    checks: list[EvaluationCheck] = []

    # Vehicles are only candidates in this MVP when accessible transport is
    # required. Do not turn unrelated shelter/communication needs into a
    # misleading vehicle UNKNOWN verdict.
    if resource.type.value == "vehicle" and person.accessible_transport_required is not True:
        return EvaluationReport(
            incident_id=incident_id,
            resource_id=resource.id,
            resource_name=resource.name,
            status=EvaluationStatus.not_applicable,
            status_label=STATUS_LABELS[EvaluationStatus.not_applicable],
        )

    # ------------------------------------------------------------------
    # Rule 1 — Wheelchair access (Shelters only)
    # ------------------------------------------------------------------
    if person.wheelchair_required is True and resource.type.value == "shelter":
        if caps.wheelchair_access is False:
            checks.append(_blocked(
                constraint="wheelchair_access",
                requirement="Person requires wheelchair-accessible facilities",
                resource_val="Wheelchair access: NO",
                evidence="Confirmed by coordinator",
                reason="The resource does not have wheelchair access. This person uses a wheelchair.",
            ))
        elif caps.wheelchair_access is None:
            checks.append(_unknown(
                constraint="wheelchair_access",
                requirement="Person requires wheelchair-accessible facilities",
                resource_val="Wheelchair access: Not verified",
                evidence="No accessibility record available",
                reason="Wheelchair accessibility for this resource has not been verified. Cannot confirm compatibility.",
            ))
        else:
            checks.append(_safe(
                constraint="wheelchair_access",
                requirement="Person requires wheelchair-accessible facilities",
                resource_val="Wheelchair access: YES",
                evidence="Verified by field team",
                reason="This resource has confirmed wheelchair access.",
            ))

    # ------------------------------------------------------------------
    # Rule 2 — Stairs (Shelters only)
    # ------------------------------------------------------------------
    if person.stairs_allowed is False and resource.type.value == "shelter":
        if caps.stairs_required is True:
            checks.append(_blocked(
                constraint="stairs",
                requirement="Person cannot use stairs",
                resource_val="Stairs required: YES",
                evidence="Confirmed by coordinator",
                reason="Access to this resource requires using stairs. The person cannot use stairs.",
            ))
        elif caps.stairs_required is None:
            checks.append(_unknown(
                constraint="stairs",
                requirement="Person cannot use stairs",
                resource_val="Stairs required: Not verified",
                evidence="No stair requirement on record",
                reason="It is unknown whether this resource requires stairs. Cannot confirm compatibility.",
            ))
        else:
            checks.append(_safe(
                constraint="stairs",
                requirement="Person cannot use stairs",
                resource_val="Stairs required: NO",
                evidence="Verified by field team",
                reason="This resource does not require using stairs.",
            ))

    # ------------------------------------------------------------------
    # Rule 3 — Ramp usability (Shelters only)
    # ------------------------------------------------------------------
    if person.ramp_usable is True and resource.type.value == "shelter":
        # Person can use a ramp — verify a ramp exists if wheelchair required
        if person.wheelchair_required is True:
            if caps.ramp is False:
                checks.append(_blocked(
                    constraint="ramp",
                    requirement="Person needs ramp access (wheelchair user)",
                    resource_val="Ramp: NO",
                    evidence="Confirmed by coordinator",
                    reason="This resource has no ramp. Person requires ramp access.",
                ))
            elif caps.ramp is None:
                checks.append(_unknown(
                    constraint="ramp",
                    requirement="Person needs ramp access (wheelchair user)",
                    resource_val="Ramp: Not verified",
                    evidence="Ramp status not on record",
                    reason="Ramp availability at this resource is unknown.",
                ))
            else:
                checks.append(_safe(
                    constraint="ramp",
                    requirement="Person needs ramp access (wheelchair user)",
                    resource_val="Ramp: YES",
                    evidence="Verified by field team",
                    reason="A ramp is available at this resource.",
                ))

    # ------------------------------------------------------------------
    # Rule 4 — Accessible transport (for vehicles)
    # ------------------------------------------------------------------
    if person.accessible_transport_required is True and resource.type.value == "vehicle":
        if caps.wheelchair_transport is False:
            checks.append(_blocked(
                constraint="wheelchair_transport",
                requirement="Person requires accessible transport (wheelchair)",
                resource_val="Wheelchair transport: NO",
                evidence="Confirmed by coordinator",
                reason="This vehicle does not have a wheelchair lift or ramp. Person cannot use it.",
            ))
        elif caps.wheelchair_transport is None:
            checks.append(_unknown(
                constraint="wheelchair_transport",
                requirement="Person requires accessible transport (wheelchair)",
                resource_val="Wheelchair transport: Not verified",
                evidence="Transport accessibility not on record",
                reason="Wheelchair transport capability of this vehicle is unknown.",
            ))
        else:
            checks.append(_safe(
                constraint="wheelchair_transport",
                requirement="Person requires accessible transport (wheelchair)",
                resource_val="Wheelchair transport: YES",
                evidence="Verified by transport officer",
                reason="This vehicle has a wheelchair lift. Person can be transported safely.",
            ))

    # ------------------------------------------------------------------
    # Rule 5 — Caregiver support
    # ------------------------------------------------------------------
    if person.caregiver_required is True and resource.type.value == "shelter":
        if caps.caregiver_support is False:
            checks.append(_blocked(
                constraint="caregiver_support",
                requirement="Person requires caregiver support",
                resource_val="Caregiver support: NO",
                evidence="Confirmed by coordinator",
                reason="This resource does not provide caregiver support. Person requires it.",
            ))
        elif caps.caregiver_support is None:
            checks.append(_unknown(
                constraint="caregiver_support",
                requirement="Person requires caregiver support",
                resource_val="Caregiver support: Not verified",
                evidence="Support capability not on record",
                reason="Caregiver support availability at this resource is unknown.",
            ))
        else:
            checks.append(_safe(
                constraint="caregiver_support",
                requirement="Person requires caregiver support",
                resource_val="Caregiver support: YES",
                evidence="Confirmed by coordinator",
                reason="Caregiver support is available at this resource.",
            ))

    # ------------------------------------------------------------------
    # Rule 6 — Visual communication
    # ------------------------------------------------------------------
    if person.visual_communication_required is True and resource.type.value == "shelter":
        if caps.visual_communication_support is False:
            checks.append(_blocked(
                constraint="visual_communication",
                requirement="Visual communication required",
                resource_val="Visual communication: NO",
                evidence="Confirmed by coordinator",
                reason="This resource does not provide visual communication. The person requires non-audio communication.",
            ))
        elif caps.visual_communication_support is None:
            checks.append(_unknown(
                constraint="visual_communication",
                requirement="Visual communication required",
                resource_val="Visual communication: Not verified",
                evidence="Support capability not on record",
                reason="Visual communication availability is unknown for this resource.",
            ))
        else:
            checks.append(_safe(
                constraint="visual_communication",
                requirement="Visual communication required",
                resource_val="Visual communication: YES",
                evidence="Confirmed by coordinator",
                reason="Visual communication is available at this resource.",
            ))

    # ------------------------------------------------------------------
    # Rule 7 — Hearing support
    # ------------------------------------------------------------------
    if person.hearing_support_required is True and resource.type.value == "shelter":
        if caps.hearing_support is False:
            checks.append(_blocked(
                constraint="hearing_support",
                requirement="Person requires hearing support",
                resource_val="Hearing support: NO",
                evidence="Confirmed by coordinator",
                reason="This resource does not provide hearing support. Person requires it.",
            ))
        elif caps.hearing_support is None:
            checks.append(_unknown(
                constraint="hearing_support",
                requirement="Person requires hearing support",
                resource_val="Hearing support: Not verified",
                evidence="Support capability not on record",
                reason="Hearing support availability is unknown for this resource.",
            ))
        else:
            checks.append(_safe(
                constraint="hearing_support",
                requirement="Person requires hearing support",
                resource_val="Hearing support: YES",
                evidence="Confirmed by coordinator",
                reason="Hearing support is available at this resource.",
            ))

    # ------------------------------------------------------------------
    # Rule 8 — Capacity check
    # ------------------------------------------------------------------
    if resource.available_capacity is not None and resource.available_capacity <= 0:
        checks.append(_blocked(
            constraint="capacity",
            requirement="Resource must have available capacity",
            resource_val=f"Available capacity: {resource.available_capacity}",
            evidence="Capacity data from resource database",
            reason="This resource is at full capacity and cannot accept additional persons.",
        ))
    elif resource.available_capacity is None:
        checks.append(_unknown(
            constraint="capacity",
            requirement="Resource must have available capacity",
            resource_val="Capacity: Not on record",
            evidence="Capacity not reported",
            reason="Available capacity for this resource is unknown.",
        ))

    # ------------------------------------------------------------------
    # If no checks were produced (person has no known constraints), return SAFE
    # but note that it's because no critical constraints were identified.
    # ------------------------------------------------------------------
    if not checks:
        checks.append(_safe(
            constraint="general",
            requirement="No critical accessibility constraints identified",
            resource_val="No specific requirements to verify",
            evidence="System check",
            reason="No critical accessibility constraints were extracted from the incident. Manual review still recommended.",
        ))

    # ------------------------------------------------------------------
    # Determine overall status — BLOCKED > UNKNOWN > SAFE
    # ------------------------------------------------------------------
    if any(c.status == CheckStatus.blocked for c in checks):
        overall = EvaluationStatus.blocked
    elif any(c.status == CheckStatus.unknown for c in checks):
        overall = EvaluationStatus.unknown
    else:
        overall = EvaluationStatus.safe

    passed = sum(1 for c in checks if c.status == CheckStatus.safe)
    unknown = sum(1 for c in checks if c.status == CheckStatus.unknown)
    blocked = sum(1 for c in checks if c.status == CheckStatus.blocked)

    return EvaluationReport(
        incident_id=incident_id,
        resource_id=resource.id,
        resource_name=resource.name,
        status=overall,
        status_label=STATUS_LABELS[overall],
        checks=checks,
        total_checks=len(checks),
        passed_checks=passed,
        unknown_checks=unknown,
        blocked_checks=blocked,
    )


# ---------------------------------------------------------------------------
# Batch evaluation helper
# ---------------------------------------------------------------------------

def evaluate_all(person: PersonProfile, resources: list[Resource], incident_id: str = "") -> list[EvaluationReport]:
    """Evaluate a person's constraints against every resource in the list."""
    return [evaluate(person, r, incident_id) for r in resources]
