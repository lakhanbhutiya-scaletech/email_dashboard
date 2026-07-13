from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ProvisionRequest(BaseModel):
    """Frontend → customer backend. Backend runs spec §3 steps 1–3 server-side."""

    company_id: str
    microsoft_id_token: str = Field(..., description="Microsoft ID token from the browser login")
    email: EmailStr | None = Field(
        None, description="Optional; falls back to the email AI Labs returns for the user."
    )


class ProvisionResponse(BaseModel):
    employee_id: str
    ai_labs_user_id: str
    ai_labs_agent_id: int
    api_key_masked: str | None
    outlook_connected: bool
    # Short-lived JWT handed back to the browser ONLY to complete the Outlook OAuth
    # dance (spec §3 step 4). Never persisted. Discarded by the frontend after connect.
    outlook_provisioning_token: str


class OutlookAuthUrlResponse(BaseModel):
    url: str


class OutlookConnectRequest(BaseModel):
    # The JWT returned as `outlook_provisioning_token` from /provision.
    access_token: str
    code: str
    redirect_uri: str


class OutlookConnectResponse(BaseModel):
    status: str
    provider_email: str | None
    outlook_connected: bool


class CompanyCreate(BaseModel):
    name: str
    admin_email: EmailStr
    # At least one of domain / ai_labs_org_id is needed before provisioning —
    # it's what lets AI Labs auto-grant the shared analyzer agent at login.
    domain: str | None = None
    ai_labs_org_id: str | None = None
    # Set directly if the shared agent already exists in AI Labs; otherwise use
    # POST /onboarding/companies/{id}/setup-agent (Step 0).
    analyzer_agent_id: int | None = None


class CompanyRead(BaseModel):
    id: str
    name: str
    admin_email: str
    domain: str | None
    ai_labs_org_id: str | None
    analyzer_agent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SetupAgentRequest(BaseModel):
    """Step 0 — one-time per company: create the shared analyzer agent in AI Labs.

    Needs a JWT for the AI Labs admin/service user who will OWN the agent.
    NOTE: pointing the org at the agent (organizations.analyzer_agent_id) is an
    AI-Labs-side step — do it there after this returns the agent id.
    """

    admin_access_token: str


class SetupAgentResponse(BaseModel):
    company_id: str
    analyzer_agent_id: int
