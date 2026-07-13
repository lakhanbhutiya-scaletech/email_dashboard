from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.snapshot import MailboxSnapshot


class Employee(Base, TimestampMixin):
    __tablename__ = "employee"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_employee_company_email"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)

    # AI Labs is the source of truth for identity + the agent definition.
    ai_labs_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # The org's SHARED analyzer agent (same for every employee of the company).
    # Isolation comes from the API key: the key is owned by this employee, so the
    # agent reads *their* Outlook connection.
    ai_labs_agent_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Bearer credential to the agent — Fernet-encrypted at rest (spec §9).
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)

    outlook_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Set true when the cron sees a 401 — key revoked/inactive, needs re-provisioning.
    needs_reprovision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="employees")
    snapshots: Mapped[list["MailboxSnapshot"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
