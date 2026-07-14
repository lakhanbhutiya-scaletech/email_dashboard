"""Authentication for the dashboard's own users (spec: "Sign in with Microsoft").

Real login exchanges a Microsoft ID token via AI Labs' `/auth/oauth-login`, which
verifies the token with Microsoft and returns the AI Labs identity for that user.
This backend then maps the identity's email to a locally known company admin or
provisioned employee and issues its own browser session. A dev-login shim signs a
seeded user in directly so the login/employee/admin surfaces are demoable without
a real Microsoft token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import employee as employee_crud
from app.db.session import get_db
from app.services.ailabs_client import AILabsAuthError, AILabsClient, AILabsError
from app.services.session import get_session_user, issue_session, resolve_login

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: str


class MicrosoftLoginRequest(BaseModel):
    token: str  # Microsoft ID token from the browser SSO


class SessionUser(BaseModel):
    email: str
    role: str
    company_id: str
    employee_id: str | None = None
    # employee-only extras
    outlook_connected: bool | None = None
    api_key_masked: str | None = None


class LoginResponse(BaseModel):
    token: str
    user: SessionUser


def _enrich(db: Session, user: dict) -> SessionUser:
    out = SessionUser(**user)
    if user.get("employee_id"):
        emp = employee_crud.get_employee(db, user["employee_id"])
        if emp is not None:
            out.outlook_connected = emp.outlook_connected
            out.api_key_masked = emp.api_key_masked
    return out


@router.post("/dev-login", response_model=LoginResponse)
def dev_login(body: DevLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """DEV ONLY — sign in as a seeded admin/employee without Microsoft.

    Disabled outside development so it can never be a backdoor in production."""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="not found")
    user = resolve_login(db, body.email)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown email. Use a company admin_email or a provisioned employee.",
        )
    return LoginResponse(token=issue_session(**user), user=_enrich(db, user))


@router.post("/microsoft", response_model=LoginResponse)
async def microsoft_login(body: MicrosoftLoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Real login — exchange the Microsoft ID token via AI Labs oauth-login, then
    map the verified identity's email to a locally known admin/employee and issue
    a dashboard session.

    This does NOT provision a new employee — that only happens through the
    onboarding flow (`POST /onboarding/provision`), which needs a company_id.
    A Microsoft login for an email this backend doesn't recognize is rejected.
    """
    try:
        login = await AILabsClient().oauth_login(body.token)
    except AILabsAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except AILabsError as e:
        raise HTTPException(status_code=502, detail=str(e))

    email = login["user"].get("email")
    if not email:
        raise HTTPException(status_code=502, detail="AI Labs did not return an email for this account")

    user = resolve_login(db, email)
    if user is None:
        raise HTTPException(
            status_code=403,
            detail=f"{email} is not a registered admin or employee for this dashboard",
        )
    return LoginResponse(token=issue_session(**user), user=_enrich(db, user))


@router.get("/me", response_model=SessionUser)
def me(db: Session = Depends(get_db), user: dict = Depends(get_session_user)) -> SessionUser:
    return _enrich(db, user)
