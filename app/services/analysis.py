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
from app.services.prompts import since_last_message

logger = get_logger("analysis")


def _merge_payload(old: dict | None, new: dict | None) -> dict | None:
    """Combine an hour-bucket's existing accumulated payload with a fresh,
    non-overlapping window's payload. Windows never overlap in time (each run
    only covers the gap since the last capture), so merging is a plain sum/
    append rather than a dedupe-by-overlap problem."""
    if new is None:
        return old
    if old is None:
        return new

    merged_threads: list[dict] = []
    seen: set[tuple] = set()
    for t in (old.get("threads") or []) + (new.get("threads") or []):
        key = (t.get("from"), t.get("subject"), t.get("received_at"))
        if key in seen:
            continue
        seen.add(key)
        merged_threads.append(t)

    old_replied = old.get("replied_count") or 0
    new_replied = new.get("replied_count") or 0
    old_avg = old.get("avg_response_minutes")
    new_avg = new.get("avg_response_minutes")
    total_replied = old_replied + new_replied
    if old_avg is not None and new_avg is not None and total_replied > 0:
        avg = (old_avg * old_replied + new_avg * new_replied) / total_replied
    else:
        avg = new_avg if new_avg is not None else old_avg

    high_priority = sum(
        1
        for t in merged_threads
        if str(t.get("status", "awaiting")) != "replied" and t.get("priority") == "high"
    )

    return {
        "window_hours": (old.get("window_hours") or 0) + (new.get("window_hours") or 0),
        "incoming_count": (old.get("incoming_count") or 0) + (new.get("incoming_count") or 0),
        "replied_count": total_replied,
        "avg_response_minutes": avg,
        "high_priority_count": high_priority,
        "sentiment_summary": new.get("sentiment_summary") or old.get("sentiment_summary"),
        "threads": merged_threads,
    }


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

    last = snapshot_crud.latest_snapshot(db, employee.id)
    existing_this_hour = last if (last is not None and last.hour_bucket == bucket) else None

    if last is not None:
        elapsed_minutes = max(1, int((now - last.captured_at).total_seconds() // 60))
    else:
        elapsed_minutes = settings.CRON_INTERVAL_MINUTES

    if not employee.outlook_connected:
        # Until Outlook is connected the agent has no mailbox to read (spec §3 step 4).
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=None, raw_text=None, ai_labs_session_id=None,
            status="empty", error="outlook not connected",
        )
        return "empty"

    # Preserve whatever's already accumulated this hour if this run fails —
    # a transient error must not wipe out already-saved good data.
    fallback_payload = existing_this_hour.payload if existing_this_hour else None
    fallback_raw = existing_this_hour.raw_text if existing_this_hour else None
    fallback_session = existing_this_hour.ai_labs_session_id if existing_this_hour else None
    fallback_status = existing_this_hour.status if existing_this_hour else None

    try:
        api_key = decrypt(employee.api_key_encrypted)
        result = await client.public_chat(
            agent_id=employee.ai_labs_agent_id,
            api_key=api_key,
            message=since_last_message(elapsed_minutes),
            session_id=None,  # fresh session every run — no history carryover
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
            payload=fallback_payload, raw_text=fallback_raw,
            ai_labs_session_id=fallback_session,
            status=fallback_status or "error", error=f"auth: {e}",
        )
        return "error"
    except AILabsError as e:
        logger.error("AI Labs error for %s: %s", employee.email, e)
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=fallback_payload, raw_text=fallback_raw,
            ai_labs_session_id=fallback_session,
            status=fallback_status or "error", error=str(e),
        )
        return "error"

    raw_text = result.get("response")
    session_id = result.get("session_id")
    new_payload, parse_err = parse_analysis(raw_text)

    if new_payload is None:
        # Parse failed — keep whatever good data this hour already has, don't discard it.
        snapshot_crud.upsert_snapshot(
            db, employee_id=employee.id, captured_at=now, bucket=bucket,
            payload=fallback_payload, raw_text=raw_text, ai_labs_session_id=session_id,
            status=fallback_status or "parse_failed", error=parse_err,
        )
        logger.warning("parse_failed for %s: %s", employee.email, parse_err)
        return fallback_status or "parse_failed"

    merged_payload = _merge_payload(fallback_payload, new_payload)
    snapshot_crud.upsert_snapshot(
        db, employee_id=employee.id, captured_at=now, bucket=bucket,
        payload=merged_payload, raw_text=raw_text, ai_labs_session_id=session_id,
        status="ok", error=None,
    )
    return "ok"
