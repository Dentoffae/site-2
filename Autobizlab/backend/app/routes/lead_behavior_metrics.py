from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lead_behavior_metrics import LeadBehaviorMetrics, LeadBehaviorMetricsCRUD

router = APIRouter()


def _row_to_dict(row: LeadBehaviorMetrics) -> dict[str, Any]:
    return {
        "lead_id": row.lead_id,
        "time_on_page_ms": row.time_on_page_ms,
        "session_id": row.session_id,
        "page_views_estimate": row.page_views_estimate,
        "button_clicks_json": row.button_clicks_json,
        "cursor_hover_zones_json": row.cursor_hover_zones_json,
        "return_visit_count": row.return_visit_count,
        "metrics_json": row.metrics_json,
        "metrics_summary_json": row.metrics_summary_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
def list_metrics(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = LeadBehaviorMetricsCRUD.list_all(db, skip=skip, limit=limit)
    return [_row_to_dict(r) for r in rows]


@router.get("/{lead_id}")
def get_metrics(lead_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = LeadBehaviorMetricsCRUD.get_by_lead_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="metrics_not_found")
    return _row_to_dict(row)


@router.patch("/{lead_id}")
def patch_metrics(
    lead_id: int, body: dict[str, Any], db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = LeadBehaviorMetricsCRUD.get_by_lead_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="metrics_not_found")
    allowed = {
        "time_on_page_ms",
        "session_id",
        "page_views_estimate",
        "button_clicks_json",
        "cursor_hover_zones_json",
        "return_visit_count",
        "metrics_json",
        "metrics_summary_json",
    }
    data = {k: v for k, v in body.items() if k in allowed}
    try:
        LeadBehaviorMetricsCRUD.update(db, row, data)
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return _row_to_dict(row)


@router.delete("/{lead_id}", status_code=204)
def delete_metrics(lead_id: int, db: Session = Depends(get_db)) -> None:
    row = LeadBehaviorMetricsCRUD.get_by_lead_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="metrics_not_found")
    try:
        LeadBehaviorMetricsCRUD.delete(db, row)
        db.commit()
    except Exception:
        db.rollback()
        raise
