from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.database import Base


class AdminSiteConfig(Base):
    """
    Корневая запись конфигурации сайта (ключ набора настроек).

    ```sql
    CREATE TABLE admin_site_config (
        id BIGSERIAL PRIMARY KEY,
        config_key VARCHAR(64) NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX ix_admin_site_config_config_key ON admin_site_config (config_key);
    ```
    """

    __tablename__ = "admin_site_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    services: Mapped[list["AdminSiteService"]] = relationship(
        "AdminSiteService",
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="AdminSiteService.sort_order",
    )
    budget_range: Mapped["AdminSiteBudgetRange | None"] = relationship(
        "AdminSiteBudgetRange",
        back_populates="config",
        cascade="all, delete-orphan",
        uselist=False,
    )
    extra_ui_rows: Mapped[list["AdminSiteExtraUi"]] = relationship(
        "AdminSiteExtraUi",
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="AdminSiteExtraUi.id",
    )


class AdminSiteConfigCRUD:
    """CRUD для корня конфигурации."""

    @staticmethod
    def create(db: Session, row: AdminSiteConfig) -> AdminSiteConfig:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_id(db: Session, config_id: int) -> AdminSiteConfig | None:
        return db.get(AdminSiteConfig, config_id)

    @staticmethod
    def get_by_key(db: Session, config_key: str) -> AdminSiteConfig | None:
        stmt = select(AdminSiteConfig).where(AdminSiteConfig.config_key == config_key).limit(1)
        return db.scalars(stmt).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[AdminSiteConfig]:
        stmt = (
            select(AdminSiteConfig)
            .order_by(AdminSiteConfig.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update(db: Session, row: AdminSiteConfig, data: dict) -> AdminSiteConfig:
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        db.flush()
        return row

    @staticmethod
    def delete(db: Session, row: AdminSiteConfig) -> None:
        db.delete(row)
        db.flush()


class AdminSiteService(Base):
    """
    Услуга для динамического UI (отдельная строка).

    ```sql
    CREATE TABLE admin_site_service (
        id BIGSERIAL PRIMARY KEY,
        config_id BIGINT NOT NULL REFERENCES admin_site_config (id) ON DELETE CASCADE,
        title VARCHAR(512) NOT NULL,
        description TEXT,
        price_amount INTEGER,
        execution_time VARCHAR(255),
        sort_order INTEGER NOT NULL DEFAULT 0
    );

    CREATE INDEX ix_admin_site_service_config_id ON admin_site_service (config_id);
    ```
    """

    __tablename__ = "admin_site_service"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_site_config.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    config: Mapped[AdminSiteConfig] = relationship("AdminSiteConfig", back_populates="services")


class AdminSiteServiceCRUD:
    """CRUD для услуг."""

    @staticmethod
    def create(db: Session, row: AdminSiteService) -> AdminSiteService:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def delete_for_config(db: Session, config_id: int) -> None:
        stmt = select(AdminSiteService).where(AdminSiteService.config_id == config_id)
        for r in db.scalars(stmt).all():
            db.delete(r)
        db.flush()


class AdminSiteBudgetRange(Base):
    """
    Один диапазон бюджета (ползунок) на конфиг: отдельные столбцы.

    ```sql
    CREATE TABLE admin_site_budget_range (
        id BIGSERIAL PRIMARY KEY,
        config_id BIGINT NOT NULL UNIQUE REFERENCES admin_site_config (id) ON DELETE CASCADE,
        min_amount INTEGER,
        max_amount INTEGER,
        step_amount INTEGER,
        currency VARCHAR(8) NOT NULL DEFAULT 'RUB',
        label VARCHAR(255)
    );

    CREATE UNIQUE INDEX uq_admin_site_budget_range_config_id ON admin_site_budget_range (config_id);
    ```
    """

    __tablename__ = "admin_site_budget_range"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admin_site_config.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    min_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'RUB'"))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    config: Mapped[AdminSiteConfig] = relationship("AdminSiteConfig", back_populates="budget_range")


class AdminSiteBudgetRangeCRUD:
    """CRUD для диапазона бюджета."""

    @staticmethod
    def create(db: Session, row: AdminSiteBudgetRange) -> AdminSiteBudgetRange:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def delete_for_config(db: Session, config_id: int) -> None:
        stmt = select(AdminSiteBudgetRange).where(AdminSiteBudgetRange.config_id == config_id)
        row = db.scalars(stmt).first()
        if row:
            db.delete(row)
            db.flush()


class AdminSiteExtraUi(Base):
    """
    Доп. опции UI: пара ключ–значение в обычных столбцах.

    ```sql
    CREATE TABLE admin_site_extra_ui (
        id BIGSERIAL PRIMARY KEY,
        config_id BIGINT NOT NULL REFERENCES admin_site_config (id) ON DELETE CASCADE,
        field_key VARCHAR(128) NOT NULL,
        field_value TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX ix_admin_site_extra_ui_config_id ON admin_site_extra_ui (config_id);
    ```
    """

    __tablename__ = "admin_site_extra_ui"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_site_config.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))

    config: Mapped[AdminSiteConfig] = relationship("AdminSiteConfig", back_populates="extra_ui_rows")


class AdminSiteExtraUiCRUD:
    """CRUD для доп. полей UI."""

    @staticmethod
    def create(db: Session, row: AdminSiteExtraUi) -> AdminSiteExtraUi:
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def delete_for_config(db: Session, config_id: int) -> None:
        stmt = select(AdminSiteExtraUi).where(AdminSiteExtraUi.config_id == config_id)
        for r in db.scalars(stmt).all():
            db.delete(r)
        db.flush()
