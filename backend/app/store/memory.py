"""SAHAYA state repository.

Local development uses deterministic in-memory state. Production can select
Supabase persistence with STORE_BACKEND=supabase while retaining this small,
synchronous repository API for the rest of the application.
"""
from __future__ import annotations

from typing import Any, Optional

from app.models.incident import CasePerson, Incident
from app.models.resource import Resource
from app.models.evaluation import EvaluationReport, GroupEvaluation
from app.models.audit import AuditLog
from app.models.route import RouteEvaluation, RouteObservation
from app.seed_data import DEMO_GROUP_INCIDENT, DEMO_GROUP_PEOPLE, SEED_RESOURCES, DEMO_INCIDENT
from app.store.supabase_store import SupabaseStateStore, configured_store

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_incidents: dict[str, Incident] = {
    DEMO_INCIDENT.id: DEMO_INCIDENT,
    DEMO_GROUP_INCIDENT.id: DEMO_GROUP_INCIDENT,
}

_resources: dict[str, Resource] = {r.id: r for r in SEED_RESOURCES}

# evaluations[incident_id] = list of EvaluationReports
_evaluations: dict[str, list[EvaluationReport]] = {}

# audit[incident_id] = list of AuditLogs
_audit: dict[str, list[AuditLog]] = {}
_people: dict[str, dict[str, CasePerson]] = {
    DEMO_GROUP_INCIDENT.id: {person.id: person for person in DEMO_GROUP_PEOPLE},
}
_group_evaluations: dict[str, list[GroupEvaluation]] = {}
_route_observations: dict[tuple[str, str], RouteObservation] = {}
_route_evaluations: dict[tuple[str, str], RouteEvaluation] = {}

# The same store API supports local demo mode and persistent Render mode.
# Persisted rows are JSONB Pydantic snapshots; models are reconstructed on
# startup before any request is served.
_persistence: SupabaseStateStore | None = configured_store()


def _json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


def _write(table: str, key: str, value: Any) -> None:
    if _persistence:
        _persistence.upsert(table, key, _json(value))


def _delete(table: str, key: str) -> None:
    if _persistence:
        _persistence.delete(table, key)


def _route_key(incident_id: str, resource_id: str) -> str:
    return f"{incident_id}:{resource_id}"


def _hydrate_or_seed() -> None:
    """Load persistent records or write the deterministic demo seed once."""
    global _incidents, _resources, _people, _evaluations, _group_evaluations
    global _route_observations, _route_evaluations, _audit
    if not _persistence:
        return

    incidents = _persistence.load_all("incidents")
    resources = _persistence.load_all("resources")
    if not incidents and not resources:
        for incident in _incidents.values():
            _write("incidents", incident.id, incident)
        for resource in _resources.values():
            _write("resources", resource.id, resource)
        for people in _people.values():
            for person in people.values():
                _write("people", person.id, person)
        return

    # Seed either independently if a deployment was interrupted after only one
    # collection had been written. Existing live records are never overwritten.
    if incidents:
        _incidents = {key: Incident(**data) for key, data in incidents.items()}
    else:
        for incident in _incidents.values():
            _write("incidents", incident.id, incident)

    if resources:
        _resources = {key: Resource(**data) for key, data in resources.items()}
    else:
        for resource in _resources.values():
            _write("resources", resource.id, resource)
    _people = {}
    for _, data in _persistence.load_all("people").items():
        person = CasePerson(**data)
        _people.setdefault(person.incident_id, {})[person.id] = person
    _evaluations = {
        key: [EvaluationReport(**report) for report in data]
        for key, data in _persistence.load_all("evaluation_batches").items()
    }
    _group_evaluations = {
        key: [GroupEvaluation(**report) for report in data]
        for key, data in _persistence.load_all("group_evaluation_batches").items()
    }
    _route_observations = {}
    for _, data in _persistence.load_all("route_observations").items():
        observation = RouteObservation(**data)
        _route_observations[(observation.incident_id, observation.resource_id)] = observation
    _route_evaluations = {}
    for _, data in _persistence.load_all("route_evaluations").items():
        evaluation = RouteEvaluation(**data)
        _route_evaluations[(evaluation.incident_id, evaluation.resource_id)] = evaluation
    _audit = {}
    for _, data in _persistence.load_all("audit_logs").items():
        log = AuditLog(**data)
        _audit.setdefault(log.incident_id, []).append(log)
    for logs in _audit.values():
        logs.sort(key=lambda log: log.created_at)


_hydrate_or_seed()


# ---------------------------------------------------------------------------
# Incident store
# ---------------------------------------------------------------------------

def save_incident(incident: Incident) -> Incident:
    _incidents[incident.id] = incident
    _write("incidents", incident.id, incident)
    return incident


def get_incident(incident_id: str) -> Optional[Incident]:
    return _incidents.get(incident_id)


def list_incidents() -> list[Incident]:
    return list(_incidents.values())


def save_person(person: CasePerson) -> CasePerson:
    _people.setdefault(person.incident_id, {})[person.id] = person
    _write("people", person.id, person)
    return person


def get_person(incident_id: str, person_id: str) -> Optional[CasePerson]:
    return _people.get(incident_id, {}).get(person_id)


def list_people(incident_id: str) -> list[CasePerson]:
    return list(_people.get(incident_id, {}).values())


def remove_person(incident_id: str, person_id: str) -> Optional[CasePerson]:
    person = _people.get(incident_id, {}).pop(person_id, None)
    if person:
        _delete("people", person_id)
    return person


# ---------------------------------------------------------------------------
# Resource store
# ---------------------------------------------------------------------------

def get_resource(resource_id: str) -> Optional[Resource]:
    return _resources.get(resource_id)


def list_resources() -> list[Resource]:
    return list(_resources.values())


def save_resource(resource: Resource) -> Resource:
    _resources[resource.id] = resource
    _write("resources", resource.id, resource)
    return resource


# ---------------------------------------------------------------------------
# Evaluation store
# ---------------------------------------------------------------------------

def save_evaluations(incident_id: str, reports: list[EvaluationReport]) -> None:
    _evaluations[incident_id] = reports
    _write("evaluation_batches", incident_id, reports)


def get_evaluations(incident_id: str) -> list[EvaluationReport]:
    return _evaluations.get(incident_id, [])


def clear_evaluations(incident_id: str) -> None:
    """Discard stale reports after the incident requirements change."""
    _evaluations.pop(incident_id, None)
    _delete("evaluation_batches", incident_id)


def invalidate_evaluations_for_resource(resource_id: str) -> list[str]:
    """Mark every affected report stale without discarding its audit evidence."""
    affected_incidents = [
        incident_id
        for incident_id, reports in _evaluations.items()
        if any(report.resource_id == resource_id for report in reports)
    ]
    for incident_id in affected_incidents:
        for report in _evaluations[incident_id]:
            report.is_current = False
            report.outdated_reason = "Resource capabilities changed after this evaluation."
        _write("evaluation_batches", incident_id, _evaluations[incident_id])
    return affected_incidents


def get_evaluation(evaluation_id: str) -> Optional[EvaluationReport]:
    for reports in _evaluations.values():
        for r in reports:
            if r.id == evaluation_id:
                return r
    return None


def save_group_evaluations(incident_id: str, reports: list[GroupEvaluation]) -> None:
    _group_evaluations[incident_id] = reports
    _write("group_evaluation_batches", incident_id, reports)


def get_group_evaluations(incident_id: str) -> list[GroupEvaluation]:
    return _group_evaluations.get(incident_id, [])


def invalidate_group_evaluations(incident_id: str, reason: str) -> None:
    for report in _group_evaluations.get(incident_id, []):
        report.is_current = False
        report.outdated_reason = reason
    _write("group_evaluation_batches", incident_id, _group_evaluations.get(incident_id, []))


def invalidate_group_evaluations_for_resource(resource_id: str) -> list[str]:
    affected = [incident_id for incident_id, reports in _group_evaluations.items() if any(report.resource_id == resource_id for report in reports)]
    for incident_id in affected:
        invalidate_group_evaluations(incident_id, "Resource capabilities changed after this group evaluation.")
    return affected


# ---------------------------------------------------------------------------
# Route observations and evaluations
# ---------------------------------------------------------------------------

def get_route_observation(incident_id: str, resource_id: str) -> Optional[RouteObservation]:
    return _route_observations.get((incident_id, resource_id))


def save_route_observation(observation: RouteObservation) -> RouteObservation:
    _route_observations[(observation.incident_id, observation.resource_id)] = observation
    _write("route_observations", _route_key(observation.incident_id, observation.resource_id), observation)
    return observation


def get_route_evaluation(incident_id: str, resource_id: str) -> Optional[RouteEvaluation]:
    return _route_evaluations.get((incident_id, resource_id))


def save_route_evaluation(evaluation: RouteEvaluation) -> RouteEvaluation:
    _route_evaluations[(evaluation.incident_id, evaluation.resource_id)] = evaluation
    _write("route_evaluations", _route_key(evaluation.incident_id, evaluation.resource_id), evaluation)
    return evaluation


def invalidate_route_evaluation(incident_id: str, resource_id: str, reason: str) -> Optional[RouteEvaluation]:
    evaluation = get_route_evaluation(incident_id, resource_id)
    if evaluation:
        evaluation.is_current = False
        evaluation.outdated_reason = reason
        _write("route_evaluations", _route_key(incident_id, resource_id), evaluation)
    return evaluation


def invalidate_route_evaluations_for_incident(incident_id: str, reason: str) -> int:
    affected = 0
    for (stored_incident_id, _), evaluation in _route_evaluations.items():
        if stored_incident_id == incident_id and evaluation.is_current:
            evaluation.is_current = False
            evaluation.outdated_reason = reason
            _write("route_evaluations", _route_key(stored_incident_id, evaluation.resource_id), evaluation)
            affected += 1
    return affected


def invalidate_route_evaluations_for_resource(resource_id: str, reason: str) -> list[str]:
    incidents: list[str] = []
    for (incident_id, stored_resource_id), evaluation in _route_evaluations.items():
        if stored_resource_id == resource_id and evaluation.is_current:
            evaluation.is_current = False
            evaluation.outdated_reason = reason
            _write("route_evaluations", _route_key(incident_id, stored_resource_id), evaluation)
            incidents.append(incident_id)
    return incidents


# ---------------------------------------------------------------------------
# Audit store
# ---------------------------------------------------------------------------

def append_audit(log: AuditLog) -> None:
    _audit.setdefault(log.incident_id, []).append(log)
    _write("audit_logs", log.id, log)


def get_audit(incident_id: str) -> list[AuditLog]:
    return _audit.get(incident_id, [])
