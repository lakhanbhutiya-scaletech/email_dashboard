"""One hourly analysis run for one employee (spec §4).

Fresh session every hour (session_id=null) — no history carryover, lower cost,
cleaner isolation. Persists exactly one idempotent snapshot per (employee, hour).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt
from app.core.logging import get_logger
from app.crud import snapshot as snapshot_crud
from app.models import Employee
from app.services.ailabs_client import AILabsAuthError, AILabsClient, AILabsError
from app.services.json_parse import parse_analysis
from app.services.prompts import hourly_message

logger = get_logger("analysis")


async def run_analysis_for_employee(
    db: Session,
    employee: Employee,
    *,
    client: AILabsClient | None = None,
) -> str:
    """Invoke the agent, parse, persist a snapshot. Returns the snapshot status.

    Never raises for expected failures — records them on the snapshot instead so a
    single bad employee doesn't halt the cron batch.
    """
    client = client or AILabsClient()
    now = datetime.now(timezone.utc)
    bucket = snapshot_crud.hour_bucket(now)
    window_hours = max(1, settings.CRON_INTERVAL_MINUTES // 60)

    # Dev dummy mode: skip Outlook + AI Labs entirely and store generated data,
    # so the pipeline is exercisable without a real mailbox connection.
    if settings.DUMMY_ANALYSIS:
        import random

        from app.services.dummy import build_dummy_payload

        rng = random.Random(f"{employee.id}:{bucket}")  # stable per employee+hour
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=build_dummy_payload(rng, now, lively=True), raw_text=None,
            ai_labs_session_id=None, status="ok", error=None,
        )
        return "ok"

    if not employee.outlook_connected:
        # Until Outlook is connected the agent has no mailbox to read (spec §3 step 4).
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=None, raw_text=None, ai_labs_session_id=None,
            status="empty", error="outlook not connected",
        )
        return "empty"

    try:
        api_key = decrypt(employee.api_key_encrypted)
        result = await client.public_chat(
            agent_id=employee.ai_labs_agent_id,
            api_key=api_key,
            message=hourly_message(window_hours),
            session_id=None,  # fresh session every hour
            timezone=settings.ANALYSIS_TIMEZONE,
        )
    except AILabsAuthError as e:
        # 401/403 — key revoked/inactive. Flag for re-provisioning (spec §9).
        employee.needs_reprovision = True
        db.add(employee)
        db.commit()
        logger.warning("auth error for %s — flagged for re-provision: %s", employee.email, e)
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=None, raw_text=None, ai_labs_session_id=None,
            status="error", error=f"auth: {e}",
        )
        return "error"
    except AILabsError as e:
        logger.error("AI Labs error for %s: %s", employee.email, e)
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=None, raw_text=None, ai_labs_session_id=None,
            status="error", error=str(e),
        )
        return "error"

    raw_text = result.get("response")
    session_id = result.get("session_id")
    payload, parse_err = parse_analysis(raw_text)

    status = "ok" if payload is not None else "parse_failed"
    snapshot_crud.upsert_snapshot(
        db, employee_id=employee.id, captured_at=now, bucket=bucket,
        payload=payload, raw_text=raw_text, ai_labs_session_id=session_id,
        status=status, error=parse_err,
    )
    if status == "parse_failed":
        logger.warning("parse_failed for %s: %s", employee.email, parse_err)
    return status
