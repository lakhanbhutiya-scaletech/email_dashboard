"""The hourly batch: iterate active employees, staggered, one snapshot each (spec §4)."""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.crud import employee as employee_crud
from app.db.session import SessionLocal
from app.services.ailabs_client import AILabsClient
from app.services.analysis import run_analysis_for_employee

logger = get_logger("cron")


async def run_hourly_batch() -> dict[str, int]:
    """Analyze every eligible employee. Staggered so we don't fire everyone at once.

    Returns a status tally. Runs its own DB session (not request-scoped).
    """
    client = AILabsClient()
    db = SessionLocal()
    tally: dict[str, int] = {}
    try:
        employees = employee_crud.list_active_for_cron(db)
        logger.info("hourly batch starting — %d eligible employee(s)", len(employees))
        for i, emp in enumerate(employees):
            if i > 0 and settings.CRON_STAGGER_SECONDS > 0:
                await asyncio.sleep(settings.CRON_STAGGER_SECONDS)
            try:
                status = await run_analysis_for_employee(db, emp, client=client)
            except Exception:  # defensive — one employee must not kill the batch
                logger.exception("unexpected failure analyzing %s", emp.email)
                status = "error"
            tally[status] = tally.get(status, 0) + 1
        logger.info("hourly batch done — %s", tally)
        return tally
    finally:
        db.close()
