"""Server-side provisioning: frontend → customer backend → AI Labs (spec §3, §8).

Agent model: ONE shared analyzer agent per org (spec header). Provisioning an
employee never creates an agent — oauth-login is called with the company's
domain/org id so AI Labs auto-grants the shared agent, then a per-employee API
key is minted against it. Isolation comes from the key (owned by the employee),
not the agent.

The JWT is kept in memory only long enough to mint the key, then returned to the
browser *solely* to finish the Outlook OAuth dance (step 3), and never persisted.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.logging import get_logger
from app.crud import employee as employee_crud
from app.models import Company, Employee
from app.services.ailabs_client import AILabsClient
from app.services.prompts import build_agent_payload

logger = get_logger("onboarding")


class OnboardingError(Exception):
    pass


async def setup_shared_agent(
    db: Session,
    company: Company,
    admin_access_token: str,
    *,
    client: AILabsClient | None = None,
) -> int:
    """Step 0 (one-time per company) — create the org's shared analyzer agent.

    The agent is owned by the AI Labs admin/service user behind the JWT. Stores
    the id on the company. Pointing organizations.analyzer_agent_id at it is done
    on the AI Labs side (spec §7 'Per-org setup').
    """
    client = client or AILabsClient()
    agent_payload = build_agent_payload(
        email=company.domain or company.name,
        model=settings.AGENT_MODEL,
        temperature=settings.AGENT_TEMPERATURE,
        max_tokens=settings.AGENT_MAX_TOKENS,
        memory_window=settings.AGENT_MEMORY_WINDOW,
    )
    agent = await client.create_agent(admin_access_token, agent_payload)
    agent_id = int(agent["id"])
    company.analyzer_agent_id = agent_id
    db.add(company)
    db.commit()
    logger.info("created shared analyzer agent %s for company %s", agent_id, company.name)
    return agent_id


async def provision_employee(
    db: Session,
    *,
    company_id: str,
    microsoft_id_token: str,
    email: str | None,
    client: AILabsClient | None = None,
) -> tuple[Employee, str]:
    """Run steps 1–2 (login with org context + mint key). Returns (employee, access_token).

    access_token (the JWT) is returned to the caller for step 3 (Outlook connect)
    and is NOT stored.
    """
    client = client or AILabsClient()

    company = employee_crud.get_company(db, company_id)
    if company is None:
        raise OnboardingError(f"unknown company_id {company_id}")
    if company.analyzer_agent_id is None:
        raise OnboardingError(
            "company has no shared analyzer agent — run Step 0 "
            "(POST /onboarding/companies/{id}/setup-agent or set analyzer_agent_id) first"
        )
    if not company.domain and not company.ai_labs_org_id:
        raise OnboardingError(
            "company needs domain or ai_labs_org_id so AI Labs can auto-grant "
            "the shared agent at login"
        )

    # Step 1 — provision the AI Labs account WITH org context (auto-grants the
    # shared agent; without it, key minting 404s).
    login = await client.oauth_login(
        microsoft_id_token,
        domain=company.domain,
        organization_id=company.ai_labs_org_id,
    )
    user = login["user"]
    access_token = login["access_token"]
    ai_labs_user_id = str(user["id"])
    resolved_email = email or user.get("email")
    if not resolved_email:
        raise OnboardingError("could not resolve employee email from AI Labs response")

    # Re-provisioning path: if we already know this employee, update in place.
    existing = employee_crud.get_by_company_email(db, company_id, resolved_email)

    # Step 2 — mint the API key against the SHARED agent (grant-aware minting:
    # the employee doesn't own the agent, but was auto-granted access in step 1).
    agent_id = company.analyzer_agent_id
    key_name = f"cron-{existing.id if existing else resolved_email}"
    key = await client.create_api_key(access_token, name=key_name, agent_id=agent_id)
    raw_key = key["raw_key"]

    if existing:
        existing.ai_labs_user_id = ai_labs_user_id
        existing.ai_labs_agent_id = agent_id
        existing.api_key_encrypted = encrypt(raw_key)
        existing.api_key_masked = key.get("masked_key")
        existing.needs_reprovision = False
        emp = existing
    else:
        emp = Employee(
            company_id=company_id,
            email=resolved_email,
            ai_labs_user_id=ai_labs_user_id,
            ai_labs_agent_id=agent_id,
            api_key_encrypted=encrypt(raw_key),
            api_key_masked=key.get("masked_key"),
            outlook_connected=False,
        )
        db.add(emp)

    db.commit()
    db.refresh(emp)
    logger.info("provisioned employee %s (shared agent %s)", emp.email, agent_id)
    # raw_key + access_token deliberately not logged or stored beyond the encrypted key.
    return emp, access_token
