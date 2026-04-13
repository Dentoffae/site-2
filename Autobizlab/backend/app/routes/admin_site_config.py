from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.core.database import get_db
from app.models.admin_site_config import (
    AdminSiteBudgetRange,
    AdminSiteBudgetRangeCRUD,
    AdminSiteConfig,
    AdminSiteConfigCRUD,
    AdminSiteExtraUi,
    AdminSiteExtraUiCRUD,
    AdminSiteService,
    AdminSiteServiceCRUD,
)

router = APIRouter()


def _coerce_optional_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v.strip().replace(" ", "").replace(",", ".")))
        except ValueError:
            return None
    return int(v)


def _coerce_int_default0(v: Any) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, str):
        try:
            return int(float(v.strip().replace(" ", "").replace(",", ".")))
        except ValueError:
            return 0
    return int(v)


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


class ServiceItem(BaseModel):
    title: str = Field(max_length=512, description="Наименование услуги")
    description: str | None = Field(None, description="Описание")
    price_amount: int | None = Field(None, description="Стоимость услуги (целое, например руб.)")
    execution_time: str | None = Field(
        None, max_length=255, description="Время исполнения (например «5 рабочих дней»)"
    )
    sort_order: int = Field(0, description="Порядок в списке")

    @field_validator("price_amount", mode="before")
    @classmethod
    def v_price(cls, v: Any) -> Any:
        return _coerce_optional_int(v)

    @field_validator("sort_order", mode="before")
    @classmethod
    def v_sort(cls, v: Any) -> Any:
        return _coerce_int_default0(v)

    @field_validator("description", "execution_time", mode="before")
    @classmethod
    def v_empty_str_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v


class BudgetRangeItem(BaseModel):
    min_amount: int | None = Field(None, description="Мин. сумма (целое, например руб.)")
    max_amount: int | None = Field(None, description="Макс. сумма")
    step_amount: int | None = Field(None, description="Шаг ползунка")
    currency: str = Field("RUB", max_length=8, description="Валюта, ISO-код")
    label: str | None = Field(None, max_length=255, description="Подпись для UI")

    @field_validator("min_amount", "max_amount", "step_amount", mode="before")
    @classmethod
    def v_budget_ints(cls, v: Any) -> Any:
        return _coerce_optional_int(v)

    @field_validator("label", mode="before")
    @classmethod
    def v_label_empty(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


class ExtraUiItem(BaseModel):
    field_key: str = Field(max_length=128, description="Ключ опции")
    field_value: str = Field("", description="Значение (строка)")

    @field_validator("field_value", mode="before")
    @classmethod
    def v_fv_str(cls, v: Any) -> Any:
        if v is None:
            return ""
        return str(v)


class AdminSiteConfigCreate(BaseModel):
    config_key: str = Field(max_length=64)
    services: list[ServiceItem] = Field(default_factory=list)
    budget_range: BudgetRangeItem | None = None
    extra_ui: list[ExtraUiItem] = Field(default_factory=list)
    replace_all_services: bool = Field(
        False,
        description="True — удалить все услуги и оставить только из этого запроса. "
        "False (по умолчанию) — добавить услуги к уже существующим.",
    )
    replace_all_extra_ui: bool = Field(
        False,
        description="True — заменить все пары extra_ui. False — только добавить новые из запроса.",
    )
    replace_budget_range: bool = Field(
        False,
        description="True — перезаписать блок бюджета из поля budget_range (как при первом создании). "
        "False — не менять диапазон бюджета, если вы не шлёте новый budget_range.",
    )

    @field_validator("replace_all_services", "replace_all_extra_ui", "replace_budget_range", mode="before")
    @classmethod
    def v_replace_flags(cls, v: Any) -> Any:
        return _coerce_bool(v)


class AdminSiteConfigUpdate(BaseModel):
    services: list[ServiceItem] | None = None
    budget_range: BudgetRangeItem | None = None
    extra_ui: list[ExtraUiItem] | None = None
    replace_all_services: bool = Field(
        False,
        description="При передаче services: True — полная замена списка услуг, False — дописать в конец.",
    )
    replace_all_extra_ui: bool = Field(
        False,
        description="При передаче extra_ui: True — заменить все ключи, False — добавить.",
    )

    @field_validator("replace_all_services", "replace_all_extra_ui", mode="before")
    @classmethod
    def v_patch_replace_flags(cls, v: Any) -> Any:
        return _coerce_bool(v)


class ServiceOut(ServiceItem):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BudgetRangeOut(BudgetRangeItem):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ExtraUiOut(ExtraUiItem):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AdminSiteConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    config_key: str
    services: list[ServiceOut]
    budget_range: BudgetRangeOut | None
    extra_ui: list[ExtraUiOut]
    created_at: datetime
    updated_at: datetime


def _reload_config(db: Session, config_id: int) -> AdminSiteConfig:
    stmt = (
        select(AdminSiteConfig)
        .options(
            selectinload(AdminSiteConfig.services),
            selectinload(AdminSiteConfig.budget_range),
            selectinload(AdminSiteConfig.extra_ui_rows),
        )
        .where(AdminSiteConfig.id == config_id)
        .limit(1)
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=404, detail="config_not_found")
    return row


def _service_row(cfg_id: int, s: ServiceItem) -> AdminSiteService:
    return AdminSiteService(
        config_id=cfg_id,
        title=s.title,
        description=s.description,
        price_amount=s.price_amount,
        execution_time=s.execution_time,
        sort_order=s.sort_order,
    )


def _apply_nested_create(db: Session, cfg: AdminSiteConfig, body: AdminSiteConfigCreate) -> None:
    for s in body.services:
        AdminSiteServiceCRUD.create(db, _service_row(cfg.id, s))
    if body.budget_range is not None:
        b = body.budget_range
        AdminSiteBudgetRangeCRUD.create(
            db,
            AdminSiteBudgetRange(
                config_id=cfg.id,
                min_amount=b.min_amount,
                max_amount=b.max_amount,
                step_amount=b.step_amount,
                currency=b.currency,
                label=b.label,
            ),
        )
    for e in body.extra_ui:
        AdminSiteExtraUiCRUD.create(
            db,
            AdminSiteExtraUi(config_id=cfg.id, field_key=e.field_key, field_value=e.field_value),
        )


def _apply_nested_update(db: Session, cfg: AdminSiteConfig, body: AdminSiteConfigCreate) -> None:
    if body.replace_all_services:
        AdminSiteServiceCRUD.delete_for_config(db, cfg.id)
    for s in body.services:
        AdminSiteServiceCRUD.create(db, _service_row(cfg.id, s))

    if body.replace_budget_range:
        AdminSiteBudgetRangeCRUD.delete_for_config(db, cfg.id)
        if body.budget_range is not None:
            b = body.budget_range
            AdminSiteBudgetRangeCRUD.create(
                db,
                AdminSiteBudgetRange(
                    config_id=cfg.id,
                    min_amount=b.min_amount,
                    max_amount=b.max_amount,
                    step_amount=b.step_amount,
                    currency=b.currency,
                    label=b.label,
                ),
            )

    if body.replace_all_extra_ui:
        AdminSiteExtraUiCRUD.delete_for_config(db, cfg.id)
    for e in body.extra_ui:
        AdminSiteExtraUiCRUD.create(
            db,
            AdminSiteExtraUi(config_id=cfg.id, field_key=e.field_key, field_value=e.field_value),
        )


def _to_response(cfg: AdminSiteConfig) -> AdminSiteConfigResponse:
    return AdminSiteConfigResponse(
        id=cfg.id,
        config_key=cfg.config_key,
        services=[ServiceOut.model_validate(s) for s in cfg.services],
        budget_range=BudgetRangeOut.model_validate(cfg.budget_range) if cfg.budget_range else None,
        extra_ui=[ExtraUiOut.model_validate(r) for r in cfg.extra_ui_rows],
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.post(
    "",
    summary="Upsert конфига: по умолчанию услуги и extra_ui добавляются, а не затирают старые",
    responses={
        201: {"description": "Создано"},
        200: {"description": "Обновлено (данные дописаны или заменены по флагам replace_all_*)"},
    },
)
def create_or_update_config(
    body: AdminSiteConfigCreate, db: Session = Depends(get_db)
) -> JSONResponse:
    existing = AdminSiteConfigCRUD.get_by_key(db, body.config_key)
    if existing:
        try:
            _apply_nested_update(db, existing, body)
            db.commit()
            cfg = _reload_config(db, existing.id)
        except Exception:
            db.rollback()
            raise
        return JSONResponse(status_code=200, content=_to_response(cfg).model_dump(mode="json"))

    row = AdminSiteConfig(config_key=body.config_key)
    try:
        AdminSiteConfigCRUD.create(db, row)
        _apply_nested_create(db, row, body)
        db.commit()
        cfg = _reload_config(db, row.id)
    except Exception:
        db.rollback()
        raise
    return JSONResponse(status_code=201, content=_to_response(cfg).model_dump(mode="json"))


@router.get("", response_model=list[AdminSiteConfigResponse])
def list_configs(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[AdminSiteConfigResponse]:
    stmt = (
        select(AdminSiteConfig)
        .options(
            selectinload(AdminSiteConfig.services),
            selectinload(AdminSiteConfig.budget_range),
            selectinload(AdminSiteConfig.extra_ui_rows),
        )
        .order_by(AdminSiteConfig.id.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    return [_to_response(r) for r in rows]


@router.get("/by-key/{config_key}", response_model=AdminSiteConfigResponse)
def get_config_by_key(config_key: str, db: Session = Depends(get_db)) -> AdminSiteConfigResponse:
    row = AdminSiteConfigCRUD.get_by_key(db, config_key)
    if not row:
        raise HTTPException(status_code=404, detail="config_not_found")
    return _to_response(_reload_config(db, row.id))


@router.get("/{config_id}", response_model=AdminSiteConfigResponse)
def get_config(config_id: int, db: Session = Depends(get_db)) -> AdminSiteConfigResponse:
    return _to_response(_reload_config(db, config_id))


@router.patch("/{config_id}", response_model=AdminSiteConfigResponse)
def patch_config(
    config_id: int, body: AdminSiteConfigUpdate, db: Session = Depends(get_db)
) -> AdminSiteConfigResponse:
    row = AdminSiteConfigCRUD.get_by_id(db, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="config_not_found")
    payload = body.model_dump(exclude_unset=True)
    try:
        if "services" in payload and body.services is not None:
            if body.replace_all_services:
                AdminSiteServiceCRUD.delete_for_config(db, row.id)
            for s in body.services:
                AdminSiteServiceCRUD.create(db, _service_row(row.id, s))
        if "budget_range" in payload:
            AdminSiteBudgetRangeCRUD.delete_for_config(db, row.id)
            if body.budget_range is not None:
                b = body.budget_range
                AdminSiteBudgetRangeCRUD.create(
                    db,
                    AdminSiteBudgetRange(
                        config_id=row.id,
                        min_amount=b.min_amount,
                        max_amount=b.max_amount,
                        step_amount=b.step_amount,
                        currency=b.currency,
                        label=b.label,
                    ),
                )
        if "extra_ui" in payload and body.extra_ui is not None:
            if body.replace_all_extra_ui:
                AdminSiteExtraUiCRUD.delete_for_config(db, row.id)
            for e in body.extra_ui:
                AdminSiteExtraUiCRUD.create(
                    db,
                    AdminSiteExtraUi(config_id=row.id, field_key=e.field_key, field_value=e.field_value),
                )
        db.commit()
        cfg = _reload_config(db, row.id)
    except Exception:
        db.rollback()
        raise
    return _to_response(cfg)


@router.delete("/{config_id}", status_code=204)
def delete_config(config_id: int, db: Session = Depends(get_db)) -> None:
    row = AdminSiteConfigCRUD.get_by_id(db, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="config_not_found")
    try:
        AdminSiteConfigCRUD.delete(db, row)
        db.commit()
    except Exception:
        db.rollback()
        raise