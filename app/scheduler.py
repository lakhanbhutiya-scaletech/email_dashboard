"""In-process APScheduler that fires the hourly batch (spec §4).

Simple, dependency-light choice for the first pass — no Redis/Celery. For multiple
API replicas in prod, run the cron in a single dedicated process (or move to a
distributed scheduler) so the batch isn't fired N times.
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import get_logger
from app.services.cron import run_hourly_batch

logger = get_logger("scheduler")

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if not settings.CRON_ENABLED:
        logger.info("cron disabled (CRON_ENABLED=false) — scheduler not started")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_hourly_batch,
        trigger=IntervalTrigger(minutes=settings.CRON_INTERVAL_MINUTES),
        id="hourly_mailbox_analysis",
        max_instances=1,          # never overlap runs
        coalesce=True,            # collapse missed runs into one
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("scheduler started — every %d min", settings.CRON_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler stopped")
