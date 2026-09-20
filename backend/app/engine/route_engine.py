"""Deterministic route and hazard compatibility rules."""
from __future__ import annotations

from app.models.evaluation import CheckStatus, EvaluationCheck, EvaluationStatus
from app.models.incident import PersonProfile
from app.models.resource import Resource
from app.models.route import RouteEvaluation, RouteFreshness, RouteObservation, route_freshness


def _check(constraint: str, status: CheckStatus, requirement: str, resource: str, evidence: str, reason: str) -> EvaluationCheck:
    return EvaluationCheck(
        constraint=constraint,
        status=status,
        requirement_label=requirement,
        resource_label=resource,
        evidence_label=evidence,
        reason=reason,
        resource_value=resource,
        resource_source="Route observation",
    )


def evaluate_route(
    person: PersonProfile,
    resource: Resource,
    observation: RouteObservation,
    requirement_version: int = 0,
) -> RouteEvaluation:
    """Evaluate a route independently from the resource compatibility result."""
    checks: list[EvaluationCheck] = []
    freshness = route_freshness(observation)
    evidence = observation.source or "Route observation not recorded"

    if observation.route_exists is False:
        checks.append(_check("route_exists", CheckStatus.blocked, "A route to the resource is required", "Route: unavailable", evidence, "No usable route to this resource is currently available."))
    elif observation.route_exists is None:
        checks.append(_check("route_exists", CheckStatus.unknown, "A route to the resource is required", "Route: not verified", evidence, "Route availability has not been verified."))
    else:
        checks.append(_check("route_exists", CheckStatus.safe, "A route to the resource is required", "Route: available", evidence, "A route to this resource has been observed."))

    if observation.known_hazard_on_route is True:
        checks.append(_check("route_hazard", CheckStatus.blocked, "No known hazard may block the route", "Known hazard: YES", evidence, "A known hazard is reported on this route."))
    elif observation.known_hazard_on_route is None:
        checks.append(_check("route_hazard", CheckStatus.unknown, "No known hazard may block the route", "Known hazard: not verified", evidence, "Hazard exposure on this route has not been verified."))
    else:
        checks.append(_check("route_hazard", CheckStatus.safe, "No known hazard may block the route", "Known hazard: NO", evidence, "No known hazard is recorded on this route."))

    accessibility_required = person.wheelchair_required is True or person.stairs_allowed is False
    if accessibility_required:
        if observation.accessible_for_person is False:
            checks.append(_check("route_accessibility", CheckStatus.blocked, "An accessible route is required", "Accessible route: NO", evidence, "This route conflicts with the person's mobility requirements."))
        elif observation.accessible_for_person is None:
            checks.append(_check("route_accessibility", CheckStatus.unknown, "An accessible route is required", "Accessible route: not verified", evidence, "Accessibility of this route has not been verified for this person."))
        else:
            checks.append(_check("route_accessibility", CheckStatus.safe, "An accessible route is required", "Accessible route: YES", evidence, "The route is verified as accessible for this person."))

    if freshness != RouteFreshness.current:
        label = "Route observation: never recorded" if freshness == RouteFreshness.never_observed else "Route observation: stale"
        checks.append(_check("route_freshness", CheckStatus.unknown, "Current route information is required", label, evidence, "Route information must be current before it can support an operational decision."))

    status = EvaluationStatus.blocked if any(check.status == CheckStatus.blocked for check in checks) else EvaluationStatus.unknown if any(check.status == CheckStatus.unknown for check in checks) else EvaluationStatus.safe
    return RouteEvaluation(
        incident_id=observation.incident_id,
        resource_id=resource.id,
        resource_name=resource.name,
        status=status,
        checks=checks,
        requirement_version=requirement_version,
        resource_version=resource.resource_version,
        route_version=observation.route_version,
        route_freshness=freshness,
    )
