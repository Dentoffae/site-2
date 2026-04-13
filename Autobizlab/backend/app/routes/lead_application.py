from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lead_application import LeadApplication, LeadApplicationCRUD
from app.models.lead_behavior_metrics import LeadBehaviorMetrics, LeadBehaviorMetricsCRUD
from app.schemas.lead_payload import LeadSubmitPayload, parse_submitted_at, split_full_name

router = APIRouter()


def _lead_to_dict(row: LeadApplication) -> dict[str, Any]:
    return {
        "id": row.id,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "middle_name": row.middle_name,
        "contact_full_name": row.contact_full_name,
        "email": row.email,
        "phone": row.phone,
        "company": row.company,
        "business_description": row.business_description,
        "business_niche": row.business_niche,
        "website": row.website,
        "company_size": row.company_size,
        "task_volume": row.task_volume,
        "role_in_company": row.role_in_company,
        "business_size": row.business_size,
        "need_volume": row.need_volume,
        "result_deadline": row.result_deadline,
        "task_type": row.task_type,
        "product_interest": row.product_interest,
        "budget": row.budget,
        "preferred_contact_method": row.preferred_contact_method,
        "preferred_contact_time": row.preferred_contact_time,
        "comments": row.comments,
        "client_schema_version": row.client_schema_version,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("", status_code=201)
def submit_lead(payload: LeadSubmitPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Приём заявки с фронта: форма + метрики в одной транзакции."""
    form = payload.form
    c = form.contact
    b = form.business
    first, last, middle = split_full_name(c.fullName)

    lead = LeadApplication(
        first_name=first,
        last_name=last,
        middle_name=middle,
        contact_full_name=(c.fullName or "").strip() or "—",
        email=c.email or None,
        phone=c.phone or None,
        company=c.company or None,
        business_description=(b.description or "").strip() or "—",
        business_niche=b.industry or None,
        website=b.website or None,
        company_size=form.companySize or None,
        task_volume=form.taskVolume or None,
        role_in_company=form.role or None,
        business_size=form.businessSize or None,
        need_volume=form.needVolume or None,
        result_deadline=form.resultDeadline or None,
        task_type=form.taskType or None,
        product_interest=form.productInterest or None,
        budget=form.budget or None,
        preferred_contact_method=form.contactPreference or None,
        preferred_contact_time=form.preferredTime or None,
        comments=form.comments or None,
        client_schema_version=payload.schemaVersion,
        submitted_at=parse_submitted_at(payload.submittedAt),
    )
    try:
        LeadApplicationCRUD.create(db, lead)
        m = payload.metrics or {}
        metrics_row = LeadBehaviorMetrics(
            lead_id=lead.id,
            time_on_page_ms=m.get("timeOnPageMs"),
            session_id=m.get("sessionId"),
            page_views_estimate=m.get("pageViewsEstimate"),
            button_clicks_json=m.get("buttonClicks"),
            cursor_hover_zones_json=m.get("cursorHoverZones"),
            return_visit_count=m.get("returnVisitCount"),
            metrics_json=m,
            metrics_summary_json=payload.metricsSummary,
        )
        LeadBehaviorMetricsCRUD.create(db, metrics_row)
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise

    return {"id": lead.id, "status": "created"}


@router.get("")
def list_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = LeadApplicationCRUD.list_all(db, skip=skip, limit=limit)
    return [_lead_to_dict(r) for r in rows]


@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = LeadApplicationCRUD.get_by_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return _lead_to_dict(row)


@router.patch("/{lead_id}")
def patch_lead(
    lead_id: int, body: dict[str, Any], db: Session = Depends(get_db)
) -> dict[str, Any]:
    row = LeadApplicationCRUD.get_by_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="lead_not_found")
    allowed = {
        "first_name",
        "last_name",
        "middle_name",
        "contact_full_name",
        "email",
        "phone",
        "company",
        "business_description",
        "business_niche",
        "website",
        "company_size",
        "task_volume",
        "role_in_company",
        "business_size",
        "need_volume",
        "result_deadline",
        "task_type",
        "product_interest",
        "budget",
        "preferred_contact_method",
        "preferred_contact_time",
        "comments",
    }
    data = {k: v for k, v in body.items() if k in allowed}
    try:
        LeadApplicationCRUD.update(db, row, data)
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return _lead_to_dict(row)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> None:
    row = LeadApplicationCRUD.get_by_id(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="lead_not_found")
    try:
        LeadApplicationCRUD.delete(db, row)
        db.commit()
    except Exception:
        db.rollback()
        raise
