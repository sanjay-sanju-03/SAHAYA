"""
SAHAYA — In-memory store.
Replaces Supabase for the MVP demo. Swap out these functions with Supabase
client calls once credentials are provided.

All state is stored in module-level dicts keyed by ID.
"""
from __future__ import annotations

from typing import Optional

from app.models.incident import CasePerson, Incident
from app.models.resource import Resource
from app.models.evaluation import EvaluationReport, GroupEvaluation
from app.models.audit import AuditLog
from app.seed_data import DEMO_GROUP_INCIDENT, DEMO_GROUP_PEOPLE, SEED_RESOURCES, DEMO_INCIDENT

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


# ---------------------------------------------------------------------------
# Incident store
# ---------------------------------------------------------------------------

def save_incident(incident: Incident) -> Incident:
    _incidents[incident.id] = incident
    return incident


def get_incident(incident_id: str) -> Optional[Incident]:
    return _incidents.get(incident_id)


def list_incidents() -> list[Incident]:
    return list(_incidents.values())


def save_person(person: CasePerson) -> CasePerson:
    _people.setdefault(person.incident_id, {})[person.id] = person
    return person


def get_person(incident_id: str, person_id: str) -> Optional[CasePerson]:
    return _people.get(incident_id, {}).get(person_id)


def list_people(incident_id: str) -> list[CasePerson]:
    return list(_people.get(incident_id, {}).values())


def remove_person(incident_id: str, person_id: str) -> Optional[CasePerson]:
    return _people.get(incident_id, {}).pop(person_id, None)


# ---------------------------------------------------------------------------
# Resource store
# ---------------------------------------------------------------------------

def get_resource(resource_id: str) -> Optional[Resource]:
    return _resources.get(resource_id)


def list_resources() -> list[Resource]:
    return list(_resources.values())


def save_resource(resource: Resource) -> Resource:
    _resources[resource.id] = resource
    return resource


# ---------------------------------------------------------------------------
# Evaluation store
# ---------------------------------------------------------------------------

def save_evaluations(incident_id: str, reports: list[EvaluationReport]) -> None:
    _evaluations[incident_id] = reports


def get_evaluations(incident_id: str) -> list[EvaluationReport]:
    return _evaluations.get(incident_id, [])


def clear_evaluations(incident_id: str) -> None:
    """Discard stale reports after the incident requirements change."""
    _evaluations.pop(incident_id, None)


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
    return affected_incidents


def get_evaluation(evaluation_id: str) -> Optional[EvaluationReport]:
    for reports in _evaluations.values():
        for r in reports:
            if r.id == evaluation_id:
                return r
    return None


def save_group_evaluations(incident_id: str, reports: list[GroupEvaluation]) -> None:
    _group_evaluations[incident_id] = reports


def get_group_evaluations(incident_id: str) -> list[GroupEvaluation]:
    return _group_evaluations.get(incident_id, [])


def invalidate_group_evaluations(incident_id: str, reason: str) -> None:
    for report in _group_evaluations.get(incident_id, []):
        report.is_current = False
        report.outdated_reason = reason


def invalidate_group_evaluations_for_resource(resource_id: str) -> list[str]:
    affected = [incident_id for incident_id, reports in _group_evaluations.items() if any(report.resource_id == resource_id for report in reports)]
    for incident_id in affected:
        invalidate_group_evaluations(incident_id, "Resource capabilities changed after this group evaluation.")
    return affected


# ---------------------------------------------------------------------------
# Audit store
# ---------------------------------------------------------------------------

def append_audit(log: AuditLog) -> None:
    _audit.setdefault(log.incident_id, []).append(log)


def get_audit(incident_id: str) -> list[AuditLog]:
    return _audit.get(incident_id, [])
