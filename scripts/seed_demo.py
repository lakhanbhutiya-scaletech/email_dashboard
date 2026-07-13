"""DEV-ONLY demo seed: fake company, employees, and 30h of snapshots so the
dashboard has something to render before real AI Labs provisioning exists.

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

DEMO_COMPANY = "Demo Co (seed)"
EMPLOYEES = [
    "liam.anderson@demo.co",
    "sophia.bennett@demo.co",
    "ethan.parker@demo.co",
    "maya.iyer@demo.co",
]
SENDERS = [
    ("Ava Techify", "ava@techify.com"), ("Noah Wavelet", "noah@wavelet.net"),
    ("Mia Innova", "mia@innova.org"), ("Leo Echo", "leo@echo.io"),
    ("Zara Dynamiq", "zara@dynamiq.ai"), ("Kai Vertex", "kai@vertex.dev"),
]
SUBJECTS = [
    "Re: Proposal for Techify", "Follow-up: Website Redesign Inquiry",
    "Re: Call Summary + Next Steps", "Pricing questions", "Contract renewal",
    "Re: Onboarding timeline", "Demo request", "Partnership opportunity",
]
SENTIMENTS = [
    "Mostly positive; two prospects asked for pricing details.",
    "Neutral overall; one thread shows frustration about response delays.",
    "Positive momentum — a demo was booked and a proposal was well received.",
]
# (priority, priority_reason, incoming_excerpt, reply_excerpt) tuples for demo threads.
THREAD_FLAVORS = [
    ("high", "Contract decision this week",
     "Asked to finalize contract terms before their board meeting Friday.",
     "Sent the revised terms and offered a call Thursday to close."),
    ("high", "Upset about delay",
     "Frustrated no one replied to last week's pricing request.",
     "Apologized, sent pricing, and escalated to the account lead."),
    ("high", "Hot prospect awaiting quote",
     "Ready to buy 50 seats, needs a formal quote today.",
     "Quote attached with volume discount and a 7-day validity."),
    ("medium", "Routine follow-up",
     "Checking in on the website redesign timeline.",
     "Shared the updated milestone dates for next sprint."),
    ("medium", "Demo scheduling",
     "Wants to book a product demo next week.",
     "Proposed three slots and sent a calendar invite."),
    ("low", "Newsletter / FYI",
     "Automated product-update digest, no action needed.",
     None),
]


def seed() -> None:
    rng = random.Random(42)
    db = SessionLocal()
    try:
        company = Company(
            name=DEMO_COMPANY, admin_email="admin@demo.co",
            domain="demo.co", analyzer_agent_id=101,
        )
        db.add(company)
        db.flush()

        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        for idx, email in enumerate(EMPLOYEES):
            emp = Employee(
                company_id=company.id, email=email,
                ai_labs_user_id=f"demo-user-{idx}", ai_labs_agent_id=101,
                api_key_encrypted=encrypt(f"sk_demo_{idx}"),
                api_key_masked=f"sk_...em{idx}0",
                outlook_connected=idx != 3,          # one not connected
                provider_email=email if idx != 3 else None,
                needs_reprovision=idx == 2,          # one flagged
            )
            db.add(emp)
            db.flush()

            if not emp.outlook_connected:
                continue
            for h in range(30, 0, -1):
                t = now - timedelta(hours=h)
                incoming = max(0, int(rng.gauss(6, 3)) + (3 if 9 <= t.hour <= 17 else 0))
                replied = min(incoming, max(0, int(rng.gauss(incoming * 0.6, 2))))
                # The most recent hour is guaranteed lively so the demo dashboards
                # aren't empty: a solid inbox and a mix that includes a high-priority
                # reply still awaiting.
                is_latest = h == 1
                if is_latest:
                    incoming = max(incoming, 6)
                    n_threads = 4
                else:
                    n_threads = rng.randint(0, 4) if incoming else 0
                threads = []
                for n, a in rng.sample(SENDERS, min(n_threads, len(SENDERS))):
                    replied_thread = rng.random() < 0.55
                    pr, reason, inc, rep = rng.choice(THREAD_FLAVORS)
                    threads.append({
                        "from": f"{n} <{a}>",
                        "subject": rng.choice(SUBJECTS),
                        "received_at": (t - timedelta(minutes=rng.randint(5, 55))).isoformat(),
                        "priority": pr,
                        "priority_reason": reason,
                        "incoming_excerpt": inc,
                        "status": "replied" if replied_thread else "awaiting",
                        "reply_excerpt": rep if replied_thread else None,
                        "replied_at": (t - timedelta(minutes=rng.randint(1, 4))).isoformat() if replied_thread else None,
                    })
                # Guarantee one high-priority awaiting thread in the latest hour.
                if is_latest and not any(th["priority"] == "high" and th["status"] == "awaiting" for th in threads):
                    _, reason, inc, _ = THREAD_FLAVORS[0]
                    n, a = rng.choice(SENDERS)
                    threads.insert(0, {
                        "from": f"{n} <{a}>",
                        "subject": "Contract terms — need to finalize",
                        "received_at": (t - timedelta(minutes=rng.randint(5, 40))).isoformat(),
                        "priority": "high",
                        "priority_reason": reason,
                        "incoming_excerpt": inc,
                        "status": "awaiting",
                        "reply_excerpt": None,
                        "replied_at": None,
                    })
                high_await = sum(1 for th in threads if th["priority"] == "high" and th["status"] == "awaiting")
                payload = {
                    "window_hours": 1,
                    "incoming_count": incoming,
                    "replied_count": replied,
                    "avg_response_minutes": round(rng.uniform(12, 95), 1) if replied else None,
                    "high_priority_count": high_await,
                    "sentiment_summary": rng.choice(SENTIMENTS),
                    "threads": threads,
                }
                db.add(MailboxSnapshot(
                    employee_id=emp.id, captured_at=t, hour_bucket=hour_bucket(t),
                    payload=payload, raw_text=None, ai_labs_session_id=1000 + h,
                    status="ok", error=None,
                ))
            # sprinkle one parse_failed row for realism
            t = now - timedelta(hours=31)
            db.add(MailboxSnapshot(
                employee_id=emp.id, captured_at=t, hour_bucket=hour_bucket(t),
                payload=None, raw_text="I could not produce JSON, sorry",
                ai_labs_session_id=999, status="parse_failed",
                error="no JSON object found in response",
            ))

        db.commit()
        print(f"seeded: 1 company, {len(EMPLOYEES)} employees, snapshots for 30h")
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
