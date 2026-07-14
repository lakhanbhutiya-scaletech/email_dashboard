"""DEV-ONLY demo seed: a demo company, 5 employees, and ~30 days of hourly
snapshots so the dashboard has data to render (including older dates for the
history/date-picker view) before real AI Labs provisioning exists.

    PYTHONPATH=. uv run python scripts/seed_demo.py        # seed
    PYTHONPATH=. uv run python scripts/seed_demo.py --wipe # remove demo rows

Demo rows are recognizable: company name 'Demo Co (seed)'.
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone

from app.core.crypto import encrypt
from app.crud.snapshot import hour_bucket
from app.db.session import SessionLocal
from app.models import Company, Employee, MailboxSnapshot
from app.services.dummy import build_dummy_payload

DEMO_COMPANY = "Demo Co (seed)"
DAYS_BACK = 30  # hourly snapshots this many days back (covers mid-June for the date picker)

# (email, outlook_connected, needs_reprovision)
EMPLOYEES = [
    ("liam.anderson@demo.co", True, False),
    ("sophia.bennett@demo.co", True, False),
    ("ethan.parker@demo.co", True, True),   # flagged for re-provision
    ("noah.carter@demo.co", True, False),
    ("maya.iyer@demo.co", False, False),    # not connected — shows the onboarding state
]


def seed() -> None:
    db = SessionLocal()
    try:
        company = Company(
            name=DEMO_COMPANY, admin_email="admin@demo.co",
            domain="demo.co", analyzer_agent_id=101,
        )
        db.add(company)
        db.flush()

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        hours = DAYS_BACK * 24
        total = 0
        for idx, (email, connected, reprov) in enumerate(EMPLOYEES):
            emp = Employee(
                company_id=company.id, email=email,
                ai_labs_user_id=f"demo-user-{idx}", ai_labs_agent_id=101,
                api_key_encrypted=encrypt(f"sk_demo_{idx}"),
                api_key_masked=f"sk_...em{idx}0",
                outlook_connected=connected,
                provider_email=email if connected else None,
                needs_reprovision=reprov,
            )
            db.add(emp)
            db.flush()

            if not connected:
                continue

            rng = random.Random(1000 + idx)  # per-employee variety, deterministic
            for h in range(hours, 0, -1):
                t = now - timedelta(hours=h)
                payload = build_dummy_payload(rng, t, lively=(h == 1))
                db.add(MailboxSnapshot(
                    employee_id=emp.id, captured_at=t, hour_bucket=hour_bucket(t),
                    payload=payload, raw_text=None, ai_labs_session_id=1000 + (h % 1000),
                    status="ok", error=None,
                ))
                total += 1
            # one parse_failed row for realism
            t = now - timedelta(hours=hours + 1)
            db.add(MailboxSnapshot(
                employee_id=emp.id, captured_at=t, hour_bucket=hour_bucket(t),
                payload=None, raw_text="I could not produce JSON, sorry",
                ai_labs_session_id=999, status="parse_failed",
                error="no JSON object found in response",
            ))

        db.commit()
        print(f"seeded: 1 company, {len(EMPLOYEES)} employees, {total} snapshots over {DAYS_BACK} days")
    finally:
        db.close()


def wipe() -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select
        for c in db.scalars(select(Company).where(Company.name == DEMO_COMPANY)):
            db.delete(c)  # cascades to employees + snapshots
        db.commit()
        print("demo rows removed")
    finally:
        db.close()


if __name__ == "__main__":
    wipe() if "--wipe" in sys.argv else seed()
