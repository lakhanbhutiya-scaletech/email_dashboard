"""Thin async client over the AI Labs public API (spec §5).

AI Labs is the source of truth for identity + the Outlook token. This client only
ever sends/receives what the customer backend is allowed to hold: JWTs (transiently,
during provisioning) and the agent API key (encrypted at rest). The Outlook token
never crosses this boundary.

Base URL is env-driven: http://localhost:8000/api/v1 (dev) or
https://ailabs.scaletechsolutions.ai/api/v1 (prod).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ailabs")


class AILabsError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AILabsAuthError(AILabsError):
    """401/403 — key revoked/inactive or JWT expired (spec §4)."""


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    msg = f"AI Labs {resp.request.method} {resp.request.url.path} -> {resp.status_code}: {body}"
    if resp.status_code in (401, 403):
        raise AILabsAuthError(msg, resp.status_code, body)
    raise AILabsError(msg, resp.status_code, body)


class AILabsClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.AILABS_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.AILABS_TIMEOUT_SECONDS

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    # ── Onboarding (spec §3) ────────────────────────────────────────────────

    async def oauth_login(
        self,
        microsoft_id_token: str,
        domain: str | None = None,
        organization_id: str | None = None,
    ) -> dict:
        """Step 1 — provision an *active* AI Labs account from a Microsoft ID token.

        Pass `domain` or `organization_id` so AI Labs resolves the org and
        auto-grants its shared `analyzer_agent_id` to the new user. Without it,
        no agent is assigned and key minting will fail (spec §3 step 1).
        """
        async with self._client() as c:
            resp = await c.post(
                "/auth/oauth-login",
                json={
                    "token": microsoft_id_token,
                    "domain": domain,
                    "organization_id": organization_id,
                },
            )
            _raise_for_status(resp)
            return resp.json()

    async def create_agent(self, access_token: str, agent_payload: dict) -> dict:
        """Step 0 (one-time per company) — create the org's shared analyzer agent.

        Owned by an admin/service user; every employee is auto-granted access at
        login once the org's `analyzer_agent_id` points at it.

        NOTE: the live endpoint is multipart/form-data with a `data` field holding
        the JSON-encoded AgentCreate payload (not a raw JSON body, despite the spec
        sketch). Returns AgentRead.
        """
        async with self._client() as c:
            resp = await c.post(
                "/agents",
                headers={"Authorization": f"Bearer {access_token}"},
                data={"data": json.dumps(agent_payload)},
            )
            _raise_for_status(resp)
            return resp.json()

    async def create_api_key(self, access_token: str, name: str, agent_id: int) -> dict:
        """Step 3 — mint the API key. `raw_key` is shown ONCE; store it encrypted."""
        async with self._client() as c:
            resp = await c.post(
                "/api-keys",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"name": name, "agent_id": agent_id},
            )
            _raise_for_status(resp)
            return resp.json()

    async def outlook_auth_url(self, access_token: str, redirect_uri: str) -> dict:
        """Step 4a — get the Microsoft consent URL to redirect the browser to."""
        async with self._client() as c:
            resp = await c.get(
                "/integrations/outlook/auth-url",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"redirect_uri": redirect_uri},
            )
            _raise_for_status(resp)
            return resp.json()

    async def outlook_connect(self, access_token: str, code: str, redirect_uri: str) -> dict:
        """Step 4b — exchange the OAuth code; AI Labs stores the token encrypted."""
        async with self._client() as c:
            resp = await c.post(
                "/integrations/outlook/connect",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"code": code, "redirect_uri": redirect_uri},
            )
            _raise_for_status(resp)
            return resp.json()

    # ── Hourly cron (spec §4) ───────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(
            (httpx.TransportError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    async def public_chat(
        self,
        agent_id: int,
        api_key: str,
        message: str,
        session_id: int | None = None,
        timezone: str | None = None,
    ) -> dict:
        """Invoke the agent with the API key. Returns {response, session_id}.

        Retries only transient transport/timeout errors. 5xx from AI Labs is
        surfaced (the cron layer decides whether to retry the whole run). A 401 is
        raised as AILabsAuthError so the caller can flag the employee.
        """
        async with self._client() as c:
            resp = await c.post(
                f"/public/agents/{agent_id}/chat",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"message": message, "session_id": session_id, "timezone": timezone},
            )
            _raise_for_status(resp)
            return resp.json()
