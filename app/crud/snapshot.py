from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import MailboxSnapshot


def hour_bucket(dt: datetime) -> str:
    """UTC hour key used for idempotency (spec §9). Expects an aware UTC datetime."""
    return dt.strftime("%Y-%m-%dT%H")


def upsert_snapshot(
    db: Session,
    *,
    employee_id: str,
    captured_at: datetime,
    bucket: str,
    payload: dict | None,
    raw_text: str | None,
    ai_labs_session_id: int | None,
    status: str,
    error: str | None,
) -> None:
    """Idempotent per (employee_id, hour_bucket) — re-running the same hour updates
    the existing row instead of creating a duplicate."""
    stmt = insert(MailboxSnapshot).values(
        employee_id=employee_id,
        captured_at=captured_at,
        hour_bucket=bucket,
        payload=payload,
        raw_text=raw_text,
        ai_labs_session_id=ai_labs_session_id,
        status=status,
        error=error,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_snapshot_employee_hour",
        set_={
            "captured_at": stmt.excluded.captured_at,
            "payload": stmt.excluded.payload,
            "raw_text": stmt.excluded.raw_text,
            "ai_labs_session_id": stmt.excluded.ai_labs_session_id,
            "status": stmt.excluded.status,
            "error": stmt.excluded.error,
        },
    )
    db.execute(stmt)
    db.commit()


def latest_snapshot(db: Session, employee_id: str) -> MailboxSnapshot | None:
    return db.scalar(
        select(MailboxSnapshot)
        .where(MailboxSnapshot.employee_id == employee_id)
        .order_by(MailboxSnapshot.captured_at.desc())
        .limit(1)
    )


def get_snapshot_by_bucket(
    db: Session, employee_id: str, bucket: str
) -> MailboxSnapshot | None:
    return db.scalar(
        select(MailboxSnapshot).where(
            MailboxSnapshot.employee_id == employee_id,
            MailboxSnapshot.hour_bucket == bucket,
        )
    )


def list_snapshots(
    db: Session, employee_id: str, limit: int = 50, offset: int = 0
) -> list[MailboxSnapshot]:
    return list(
        db.scalars(
            select(MailboxSnapshot)
            .where(MailboxSnapshot.employee_id == employee_id)
            .order_by(MailboxSnapshot.captured_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def count_snapshots(db: Session, employee_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(MailboxSnapshot).where(
            MailboxSnapshot.employee_id == employee_id
        )
    ) or 0
