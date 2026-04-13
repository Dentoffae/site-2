from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ContactBlock(BaseModel):
    fullName: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""

    @field_validator("fullName", "email", "phone", "company", mode="before")
    @classmethod
    def contact_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class BusinessBlock(BaseModel):
    description: str = ""
    industry: str = ""
    website: str = ""

    @field_validator("description", "industry", "website", mode="before")
    @classmethod
    def business_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class FormBlock(BaseModel):
    contact: ContactBlock = Field(default_factory=ContactBlock)
    business: BusinessBlock = Field(default_factory=BusinessBlock)
    budget: str = ""
    contactPreference: str = ""
    comments: str = ""
    companySize: str = ""
    taskVolume: str = ""
    role: str = ""
    businessSize: str = ""
    needVolume: str = ""
    resultDeadline: str = ""
    taskType: str = ""
    productInterest: str = ""
    preferredTime: str = ""

    @field_validator(
        "budget",
        "contactPreference",
        "comments",
        "companySize",
        "taskVolume",
        "role",
        "businessSize",
        "needVolume",
        "resultDeadline",
        "taskType",
        "productInterest",
        "preferredTime",
        mode="before",
    )
    @classmethod
    def form_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("contact", "business", mode="before")
    @classmethod
    def nested_blocks(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v


class LeadSubmitPayload(BaseModel):
    """Тело POST /api/v1/leads — как отправляет фронтенд (lead-form.js)."""

    schemaVersion: int = 1
    submittedAt: str | None = None
    form: FormBlock = Field(default_factory=FormBlock)
    metrics: dict[str, Any] = Field(default_factory=dict)
    metricsSummary: dict[str, Any] | None = None

    @field_validator("schemaVersion", mode="before")
    @classmethod
    def schema_version_coerce(cls, v: Any) -> Any:
        if v is None or v == "":
            return 1
        if isinstance(v, str):
            try:
                return int(float(v))
            except ValueError:
                return 1
        return v

    @field_validator("form", mode="before")
    @classmethod
    def form_none_to_empty(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    @field_validator("metrics", mode="before")
    @classmethod
    def metrics_none_to_empty(cls, v: Any) -> Any:
        if v is None:
            return {}
        if not isinstance(v, dict):
            return {}
        return v

    @field_validator("metricsSummary", mode="before")
    @classmethod
    def metrics_summary_dict_or_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, dict):
            return None
        return v


def parse_submitted_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        s = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def split_full_name(full: str) -> tuple[str | None, str | None, str | None]:
    parts = [p for p in full.strip().split() if p]
    if not parts:
        return None, None, None
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0], parts[-1], " ".join(parts[1:-1])
