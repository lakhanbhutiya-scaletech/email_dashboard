"""Browser session tokens for the dashboard's own login.

This is NOT the AI Labs JWT and NOT the per-employee API key. It is a short-lived
session this backend issues to a browser after the user signs in, so the frontend
can call /me and the dashboard endpoints as a known admin or employee.

The token is a Fernet-encrypted JSON blob (reusing the same key as the API-key
vault) with an embedded expiry — stateless, nothing stored server-side.

Login itself is "Sign in with Microsoft" (spec): the real flow exchanges a
Microsoft token via AI Labs oauth-login. Until Azure credentials are wired, a
dev-login shim (see api/routes/auth.py) resolves a seeded user directly so the
whole surface is clickable.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.models import Company, Employee

SESSION_TTL_HOURS = 12


def issue_session(
    *, email: str, role: str, company_id: str, employee_id: str | None = None
) -> str:
    payload = {
        "email": email,
        "role": role,  # "admin" | "employee"
        "company_id": company_id,
        "employee_id": employee_id,
        "exp": (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat(),
    }
    return encrypt(json.dumps(payload))


def decode_session(token: str) -> dict:
    data = json.loads(decrypt(token))
    if datetime.fromisoformat(data["exp"]) < datetime.now(timezone.utc):
        raise ValueError("session expired")
    return data


def resolve_login(db: Session, email: str) -> dict | None:
    """Map an email to a session user. A company's admin_email is an admin;
    any known employee address is an employee. Returns None if neither."""
    email = email.strip().lower()
    company = db.scalar(select(Company).where(Company.admin_email == email))
    if company is not None:
        return {"email": email, "role": "admin", "company_id": company.id, "employee_id": None}
    emp = db.scalar(select(Employee).where(Employee.email == email))
    if emp is not None:
        return {
            "email": email,
            "role": "employee",
            "company_id": emp.company_id,
            "employee_id": emp.id,
        }
    return None


def get_session_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: require a valid session bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_session(token)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired session")
