from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base


class LeadBehaviorMetrics(Base):
    """
    Поведенческие и технические метрики лида (время на странице, клики, курсор, возвраты и пр.).
    Связь с заявкой 1:1: первичный ключ совпадает с `lead_application.id`.

    ```sql
    CREATE TABLE lead_behavior_metrics (
        lead_id BIGINT PRIMARY KEY REFERENCES lead_application (id) ON DELETE CASCADE,
        time_on_page_ms BIGINT,
        session_id VARCHAR(128),
        page_views_estimate INTEGER,
        button_clicks_json JSONB,
        cursor_hover_zones_json JSONB,
        return_visit_count INTEGER,
        metrics_json JSONB NOT NULL,
        metrics_summary_json JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX ix_lead_behavior_metrics_session_id ON lead_behavior_metrics (session_id);
    ```
    """

    __tablename__ = "lead_behavior_metrics"

    lead_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("lead_application.id", ondelete="CASCADE"),
        primary_key=True,
    )
    time_on_page_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    page_views_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    button_clicks_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    cursor_hover_zones_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    return_visit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metrics_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    lead: Mapped["LeadApplication"] = relationship("LeadApplication", back_populates="behavior_metrics")


class LeadBehaviorMetricsCRUD:
    """CRUD для метрик по заявке (один к одному с lead_id)."""

    @staticmethod
    def create(db: Session, row: LeadBehaviorMetrics) -> LeadBehaviorMetrics:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_lead_id(db: Session, lead_id: int) -> LeadBehaviorMetrics | None:
        return db.get(LeadBehaviorMetrics, lead_id)

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[LeadBehaviorMetrics]:
        stmt = (
            select(LeadBehaviorMetrics)
            .order_by(LeadBehaviorMetrics.lead_id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update(db: Session, row: LeadBehaviorMetrics, data: dict[str, Any]) -> LeadBehaviorMetrics:
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        db.flush()
        return row

    @staticmethod
    def delete(db: Session, row: LeadBehaviorMetrics) -> None:
        db.delete(row)
        db.flush()
