"""Dummy analysis payloads — shared by the demo seeder and the dev "dummy
analysis" mode (DUMMY_ANALYSIS=true), so both produce the same thread-centric
shape the dashboard renders, without a real Outlook connection or AI Labs call.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

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
# (priority, priority_reason, incoming_excerpt, reply_excerpt)
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


def build_dummy_payload(rng: random.Random, t: datetime, *, lively: bool = False) -> dict:
    """A single hour's dummy analysis payload. When `lively`, guarantees a busy
    inbox with a high-priority reply still awaiting (used for the newest hour)."""
    incoming = max(0, int(rng.gauss(6, 3)) + (3 if 9 <= t.hour <= 17 else 0))
    replied = min(incoming, max(0, int(rng.gauss(incoming * 0.6, 2))))

    if lively:
        incoming = max(incoming, 6)
        n_threads = 4
    else:
        n_threads = rng.randint(0, 4) if incoming else 0

    threads = []
    for n, a in rng.sample(SENDERS, min(n_threads, len(SENDERS))):
        did_reply = rng.random() < 0.55
        pr, reason, inc, rep = rng.choice(THREAD_FLAVORS)
        threads.append({
            "from": f"{n} <{a}>",
            "subject": rng.choice(SUBJECTS),
            "received_at": (t - timedelta(minutes=rng.randint(5, 55))).isoformat(),
            "priority": pr,
            "priority_reason": reason,
            "incoming_excerpt": inc,
            "status": "replied" if did_reply else "awaiting",
            "reply_excerpt": rep if did_reply else None,
            "replied_at": (t - timedelta(minutes=rng.randint(1, 4))).isoformat() if did_reply else None,
        })

    if lively and not any(th["priority"] == "high" and th["status"] == "awaiting" for th in threads):
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
    return {
        "window_hours": 1,
        "incoming_count": incoming,
        "replied_count": replied,
        "avg_response_minutes": round(rng.uniform(12, 95), 1) if replied else None,
        "high_priority_count": high_await,
        "sentiment_summary": rng.choice(SENTIMENTS),
        "threads": threads,
    }
