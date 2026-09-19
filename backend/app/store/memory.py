"""
SAHAYA — In-memory store.
Replaces Supabase for the MVP demo. Swap out these functions with Supabase
client calls once credentials are provided.

All state is stored in module-level dicts keyed by ID.
"""
from __future__ import annotations

from typing import Optional

from app.models.incident import Incident
from app.models.resource import Resource
from app.models.evaluation import EvaluationReport
from app.models.audit import AuditLog
from app.seed_data import SEED_RESOURCES, DEMO_INCIDENT

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_incidents: dict[str, Incident] = {
    DEMO_INCIDENT.id: DEMO_INCIDENT,
}

_resources: dict[str, Resource] = {r.id: r for r in SEED_RESOURCES}

# evaluations[incident_id] = list of EvaluationReports
_evaluations: dict[str, list[EvaluationReport]] = {}

# audit[incident_id] = list of AuditLogs
_audit: dict[str, list[AuditLog]] = {}


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


# ---------------------------------------------------------------------------
# Resource store
# ---------------------------------------------------------------------------

def get_resource(resource_id: str) -> Optional[Resource]:
    return _resources.get(resource_id)


def list_resources() -> list[Resource]:
    return list(_resources.values())


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


def get_evaluation(evaluation_id: str) -> Optional[EvaluationReport]:
    for reports in _evaluations.values():
        for r in reports:
            if r.id == evaluation_id:
                return r
    return None


# ---------------------------------------------------------------------------
# Audit store
# ---------------------------------------------------------------------------

def append_audit(log: AuditLog) -> None:
    _audit.setdefault(log.incident_id, []).append(log)


def get_audit(incident_id: str) -> list[AuditLog]:
    return _audit.get(incident_id, [])
