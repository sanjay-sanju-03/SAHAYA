"""
SAHAYA — Evaluations API router.
"""
from fastapi import APIRouter, HTTPException
from app.store.memory import get_evaluations, get_evaluation

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.get("/incident/{incident_id}")
async def get_evaluations_for_incident(incident_id: str) -> dict:
    reports = get_evaluations(incident_id)
    return {"incident_id": incident_id, "evaluations": [r.model_dump() for r in reports]}


@router.get("/{evaluation_id}")
async def get_evaluation_by_id(evaluation_id: str) -> dict:
    report = get_evaluation(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    return report.model_dump()
