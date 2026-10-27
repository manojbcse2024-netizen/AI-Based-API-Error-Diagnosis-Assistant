from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    api_name: str = Field(min_length=1, max_length=160)
    method: str = Field(default="GET", max_length=16)
    endpoint: str = Field(default="", max_length=1000)
    status_code: int | None = Field(default=None, ge=100, le=599)
    error_message: str = Field(default="", max_length=10000)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    request_sample: str = Field(default="", max_length=50000)
    response_sample: str = Field(default="", max_length=50000)
    duration_ms: float | None = Field(default=None, ge=0, le=86400000)
    timestamp: datetime | None = None
    logs: str = Field(default="", max_length=100000)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "OTHER"}
        v = v.strip().upper()
        if v not in allowed:
            raise ValueError("Use a standard HTTP method or OTHER")
        return v


class IncidentStatusUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved"]


class FixAttemptCreate(BaseModel):
    notes: str = Field(min_length=1, max_length=5000)
    outcome: Literal["pending", "successful", "unsuccessful", "inconclusive"] = "pending"


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    observed_status: int | None = Field(default=None, ge=100, le=599)
    input_sample: str = Field(default="", max_length=20000)
    result: Literal["not_run", "pass", "fail"] = "not_run"
    notes: str = Field(default="", max_length=5000)


class IncidentOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    title: str
    api_name: str
    method: str
    endpoint: str
    status_code: int | None
    category: str
    confidence: float
    status: str
    created_at: str
    updated_at: str
