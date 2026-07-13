"""Onboarding endpoints (spec §3). Frontend → customer backend → AI Labs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import employee as employee_crud
from app.db.session import get_db
from app.schemas.onboarding import (
    CompanyCreate,
    CompanyRead,
    OutlookAuthUrlResponse,
    OutlookConnectRequest,
    OutlookConnectResponse,
    ProvisionRequest,
    ProvisionResponse,
    SetupAgentRequest,
    SetupAgentResponse,
)
from app.services.ailabs_client import AILabsAuthError, AILabsClient, AILabsError
from app.services.onboarding import OnboardingError, provision_employee, setup_shared_agent
from app.models import Company

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _ailabs_http(e: AILabsError) -> HTTPException:
    code = 401 if isinstance(e, AILabsAuthError) else 502
    return HTTPException(status_code=code, detail=str(e))


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.created_at)))


@router.post("/companies", response_model=CompanyRead, status_code=201)
def create_company(body: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    company = Company(
        name=body.name,
        admin_email=body.admin_email,
        domain=body.domain,
        ai_labs_org_id=body.ai_labs_org_id,
        analyzer_agent_id=body.analyzer_agent_id,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.post("/companies/{company_id}/setup-agent", response_model=SetupAgentResponse)
async def setup_agent(
    company_id: str, body: SetupAgentRequest, db: Session = Depends(get_db)
) -> SetupAgentResponse:
    """Step 0 (one-time per company) — create the shared analyzer agent in AI Labs.

    Owned by the admin/service user behind `admin_access_token`. After this,
    point the org's `analyzer_agent_id` at the returned id on the AI Labs side
    so new employees are auto-granted access at login (spec §3 step 0 / §7).
    """
    company = employee_crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    if company.analyzer_agent_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"company already has analyzer_agent_id={company.analyzer_agent_id}",
        )
    try:
        agent_id = await setup_shared_agent(db, company, body.admin_access_token)
    except AILabsError as e:
        raise _ailabs_http(e)
    return SetupAgentResponse(company_id=company.id, analyzer_agent_id=agent_id)


@router.post("/provision", response_model=ProvisionResponse)
async def provision(body: ProvisionRequest, db: Session = Depends(get_db)) -> ProvisionResponse:
    """Steps 1–2: provision AI Labs account (with org context, which auto-grants
    the shared analyzer agent) and mint + encrypt the per-employee API key.

    No agent is created here — the org's ONE shared agent must exist first
    (Step 0). Returns a short-lived JWT the browser uses ONLY to finish the
    Outlook connect (step 3). It is not persisted here.
    """
    try:
        emp, access_token = await provision_employee(
            db,
            company_id=body.company_id,
            microsoft_id_token=body.microsoft_id_token,
            email=body.email,
        )
    except OnboardingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AILabsError as e:
        raise _ailabs_http(e)

    return ProvisionResponse(
        employee_id=emp.id,
        ai_labs_user_id=emp.ai_labs_user_id,
        ai_labs_agent_id=emp.ai_labs_agent_id,
        api_key_masked=emp.api_key_masked,
        outlook_connected=emp.outlook_connected,
        outlook_provisioning_token=access_token,
    )


@router.get("/outlook/auth-url", response_model=OutlookAuthUrlResponse)
async def outlook_auth_url(
    access_token: str = Query(..., description="The outlook_provisioning_token from /provision"),
    redirect_uri: str = Query(..., description="Must be pre-registered in the Azure app"),
) -> OutlookAuthUrlResponse:
    """Step 4a — proxy to AI Labs for the Microsoft consent URL."""
    try:
        data = await AILabsClient().outlook_auth_url(access_token, redirect_uri)
    except AILabsError as e:
        raise _ailabs_http(e)
    return OutlookAuthUrlResponse(url=data["url"])


@router.post("/employees/{employee_id}/outlook/connect", response_model=OutlookConnectResponse)
async def outlook_connect(
    employee_id: str, body: OutlookConnectRequest, db: Session = Depends(get_db)
) -> OutlookConnectResponse:
    """Step 4b — exchange the OAuth code; mark the employee connected on success."""
    emp = employee_crud.get_employee(db, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="employee not found")

    try:
        data = await AILabsClient().outlook_connect(
            body.access_token, body.code, body.redirect_uri
        )
    except AILabsError as e:
        raise _ailabs_http(e)

    status = data.get("status")
    if status == "success":
        emp.outlook_connected = True
        emp.provider_email = data.get("provider_email")
        db.add(emp)
        db.commit()
        db.refresh(emp)

    return OutlookConnectResponse(
        status=status or "unknown",
        provider_email=data.get("provider_email"),
        outlook_connected=emp.outlook_connected,
    )
