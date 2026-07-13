from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class MailboxSnapshot(Base):
    __tablename__ = "mailbox_snapshot"
    # Idempotent per (employee, captured hour) — spec §9.
    __table_args__ = (
        UniqueConstraint("employee_id", "hour_bucket", name="uq_snapshot_employee_hour"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Truncated-to-hour UTC string, e.g. "2026-07-13T09" — the idempotency key.
    hour_bucket: Mapped[str] = mapped_column(String(20), nullable=False)

    # Parsed structured JSON (spec §6). Null when parse_failed.
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Always kept for debugging drift.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_labs_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # "ok" | "parse_failed" | "empty" | "error"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="snapshots")
