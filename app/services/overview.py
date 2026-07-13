"""Org-wide dashboard aggregation over stored snapshots.

Everything is computed from `mailbox_snapshot.payload` (the parsed JSON the agent
emitted, spec §6): per-employee latest hour for the KPI tiles, previous hour for
the deltas, and a per-hour sum for the volume trend.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee, MailboxSnapshot
from app.schemas.overview import (
    KpiValue,
    OverviewResponse,
    PendingReply,
    VolumePoint,
)


def _num(payload: dict | None, key: str) -> float | None:
    if not payload:
        return None
    v = payload.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _sum(values: list[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    return sum(known) if known else None


def _avg(values: list[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    return sum(known) / len(known) if known else None


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _threads(payload: dict | None) -> list[dict]:
    """Normalize a snapshot's threads. Prefers the new `threads` array; falls
    back to the legacy `pending_replies` shape so old snapshots still render."""
    if not payload:
        return []
    threads = payload.get("threads")
    if isinstance(threads, list):
        return [t for t in threads if isinstance(t, dict)]
    legacy = []
    for it in payload.get("pending_replies", []) or []:
        if isinstance(it, dict):
            legacy.append({**it, "status": "awaiting", "priority": "medium"})
    return legacy


# Threads still needing a reply (new "awaiting" status, or any legacy pending row).
def _awaiting(payload: dict | None) -> list[dict]:
    return [t for t in _threads(payload) if str(t.get("status", "awaiting")) != "replied"]


_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def build_overview(db: Session, company_id: str | None = None) -> OverviewResponse:
    emp_stmt = select(Employee)
    if company_id:
        emp_stmt = emp_stmt.where(Employee.company_id == company_id)
    employees = list(db.scalars(emp_stmt))
    emp_by_id = {e.id: e for e in employees}

    snaps: list[MailboxSnapshot] = []
    if employees:
        snaps = list(
            db.scalars(
                select(MailboxSnapshot)
                .where(
                    MailboxSnapshot.employee_id.in_(emp_by_id),
                    MailboxSnapshot.status == "ok",
                )
                .order_by(MailboxSnapshot.hour_bucket)
            )
        )

    # Per-employee snapshots ordered by hour: last = latest, second-to-last = previous.
    by_emp: dict[str, list[MailboxSnapshot]] = {}
    for s in snaps:
        by_emp.setdefault(s.employee_id, []).append(s)

    latest = [rows[-1] for rows in by_emp.values()]
    previous = [rows[-2] for rows in by_emp.values() if len(rows) >= 2]

    def kpi_sum(key: str) -> KpiValue:
        cur = _sum([_num(s.payload, key) for s in latest])
        prev = _sum([_num(s.payload, key) for s in previous]) if previous else None
        return KpiValue(value=cur, delta=_delta(cur, prev))

    def kpi_avg(key: str) -> KpiValue:
        cur = _avg([_num(s.payload, key) for s in latest])
        prev = _avg([_num(s.payload, key) for s in previous]) if previous else None
        return KpiValue(value=cur, delta=_delta(cur, prev))

    # Pending replies (awaiting threads), flattened from each employee's latest snapshot.
    pending: list[PendingReply] = []
    for s in latest:
        emp = emp_by_id[s.employee_id]
        for item in _awaiting(s.payload):
            pending.append(
                PendingReply(
                    employee_id=emp.id,
                    employee_email=emp.email,
                    from_=str(item.get("from", "")),
                    subject=str(item.get("subject", "")),
                    received_at=str(item.get("received_at", "")),
                    priority=str(item.get("priority", "medium")),
                    priority_reason=str(item.get("priority_reason", "")),
                    incoming_excerpt=str(item.get("incoming_excerpt", "")),
                )
            )
    # High priority first, then most recent (stable two-pass: recency, then priority).
    pending.sort(key=lambda p: p.received_at, reverse=True)
    pending.sort(key=lambda p: _PRIORITY_RANK.get(p.priority, 1))

    pending_count_cur = float(len(pending))
    pending_prev = (
        float(sum(len(_awaiting(s.payload)) for s in previous)) if previous else None
    )

    # High-priority awaiting threads — the "act now" number.
    def _high(rows: list[MailboxSnapshot]) -> int:
        return sum(
            1
            for s in rows
            for t in _awaiting(s.payload)
            if str(t.get("priority", "")) == "high"
        )

    high_cur = float(_high(latest))
    high_prev = float(_high(previous)) if previous else None

    # Volume trend: sum per hour bucket across employees.
    volume: dict[str, VolumePoint] = {}
    for s in snaps:
        pt = volume.setdefault(
            s.hour_bucket, VolumePoint(hour_bucket=s.hour_bucket, incoming=0, replied=0)
        )
        pt.incoming += int(_num(s.payload, "incoming_count") or 0)
        pt.replied += int(_num(s.payload, "replied_count") or 0)

    return OverviewResponse(
        employees_total=len(employees),
        employees_connected=sum(1 for e in employees if e.outlook_connected),
        employees_needing_attention=sum(1 for e in employees if e.needs_reprovision),
        incoming=kpi_sum("incoming_count"),
        replied=kpi_sum("replied_count"),
        avg_response_minutes=kpi_avg("avg_response_minutes"),
        pending_count=KpiValue(
            value=pending_count_cur, delta=_delta(pending_count_cur, pending_prev)
        ),
        high_priority=KpiValue(value=high_cur, delta=_delta(high_cur, high_prev)),
        pending_replies=pending[:50],
        volume_series=sorted(volume.values(), key=lambda p: p.hour_bucket)[-48:],
    )
