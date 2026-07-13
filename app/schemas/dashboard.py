from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EmployeeRead(BaseModel):
    id: str
    company_id: str
    email: str
    ai_labs_user_id: str
    ai_labs_agent_id: int
    api_key_masked: str | None
    outlook_connected: bool
    provider_email: str | None
    needs_reprovision: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SnapshotRead(BaseModel):
    id: str
    employee_id: str
    captured_at: datetime
    hour_bucket: str
    payload: dict | None
    ai_labs_session_id: int | None
    status: str
    error: str | None

    model_config = {"from_attributes": True}


class EmployeeDashboard(BaseModel):
    employee: EmployeeRead
    latest_snapshot: SnapshotRead | None
    snapshot_count: int
