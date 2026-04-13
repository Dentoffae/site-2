from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base


class LeadApplication(Base):
    """
    Заявка «тёплого» клиента: контакты, бизнес, бюджет, предпочтения и расширенные поля формы.

    ```sql
    CREATE TABLE lead_application (
        id BIGSERIAL PRIMARY KEY,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        middle_name VARCHAR(255),
        contact_full_name VARCHAR(512) NOT NULL,
        email VARCHAR(320),
        phone VARCHAR(64),
        company VARCHAR(512),
        business_description TEXT NOT NULL,
        business_niche VARCHAR(512),
        website VARCHAR(2048),
        company_size VARCHAR(255),
        task_volume VARCHAR(255),
        role_in_company VARCHAR(64),
        business_size VARCHAR(255),
        need_volume VARCHAR(255),
        result_deadline VARCHAR(255),
        task_type VARCHAR(255),
        product_interest VARCHAR(512),
        budget VARCHAR(255),
        preferred_contact_method VARCHAR(255),
        preferred_contact_time VARCHAR(255),
        comments TEXT,
        client_schema_version INTEGER,
        submitted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX ix_lead_application_email ON lead_application (email);
    CREATE INDEX ix_lead_application_submitted_at ON lead_application (submitted_at);
    ```
    """

    __tablename__ = "lead_application"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company: Mapped[str | None] = mapped_column(String(512), nullable=True)
    business_description: Mapped[str] = mapped_column(Text, nullable=False)
    business_niche: Mapped[str | None] = mapped_column(String(512), nullable=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_volume: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_in_company: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_size: Mapped[str | None] = mapped_column(String(255), nullable=True)
    need_volume: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_deadline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_interest: Mapped[str | None] = mapped_column(String(512), nullable=True)
    budget: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_contact_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    behavior_metrics: Mapped["LeadBehaviorMetrics | None"] = relationship(
        "LeadBehaviorMetrics",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
    )


class LeadApplicationCRUD:
    """CRUD для заявок."""

    @staticmethod
    def create(db: Session, row: LeadApplication) -> LeadApplication:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_id(db: Session, lead_id: int) -> LeadApplication | None:
        return db.get(LeadApplication, lead_id)

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[LeadApplication]:
        stmt = (
            select(LeadApplication)
            .order_by(LeadApplication.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update(db: Session, row: LeadApplication, data: dict[str, Any]) -> LeadApplication:
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        db.flush()
        return row

    @staticmethod
    def delete(db: Session, row: LeadApplication) -> None:
        db.delete(row)
        db.flush()
