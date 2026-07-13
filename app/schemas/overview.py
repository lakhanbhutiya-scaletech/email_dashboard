from __future__ import annotations

from pydantic import BaseModel


class KpiValue(BaseModel):
    value: float | None
    # Delta vs the previous captured hour across the same employees; None when
    # there is no prior hour to compare against.
    delta: float | None


class PendingReply(BaseModel):
    employee_id: str
    employee_email: str
    from_: str
    subject: str
    received_at: str
    # Priority signal from the analysis (defaults keep legacy snapshots working).
    priority: str = "medium"  # "high" | "medium" | "low"
    priority_reason: str = ""
    # What the client actually asked, so the row is actionable at a glance.
    incoming_excerpt: str = ""

    model_config = {"populate_by_name": True}


class VolumePoint(BaseModel):
    hour_bucket: str
    incoming: int
    replied: int


class OverviewResponse(BaseModel):
    employees_total: int
    employees_connected: int
    employees_needing_attention: int

    # KPI tiles (aggregated over each employee's LATEST ok snapshot)
    incoming: KpiValue
    replied: KpiValue
    avg_response_minutes: KpiValue
    pending_count: KpiValue
    # High-priority awaiting threads across the team — the "act now" number.
    high_priority: KpiValue

    pending_replies: list[PendingReply]
    # Hourly volume series (sum over employees per hour bucket), oldest first
    volume_series: list[VolumePoint]
