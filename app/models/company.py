from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Company(Base, TimestampMixin):
    __tablename__ = "company"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_email: Mapped[str] = mapped_column(String(320), nullable=False)
    # Org identity in AI Labs. `domain` (e.g. "acme.com") or org id is passed at
    # oauth-login so AI Labs auto-grants the shared analyzer agent (spec §3 step 1).
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_labs_org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The org's ONE shared "Outlook Analyzer" agent (spec: one agent per org;
    # per-employee isolation comes from the API key, not the agent).
    analyzer_agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
