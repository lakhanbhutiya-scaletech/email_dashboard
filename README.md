# Sales Outlook Dashboard — Customer Backend

Standalone FastAPI backend that provisions per-employee AI-Lab agents, runs an
hourly cron asking each agent to analyze that employee's Outlook mailbox, stores
the structured JSON result, and serves dashboard data.

Implements `SALES_DASHBOARD_BACKEND_SPEC.md`. AI Labs stays the source of truth
for **identity + the Outlook OAuth token**; this backend owns **the API keys
(encrypted) and all analysis snapshots**.

**Agent model: ONE shared agent per org.** All employees of a company share a
single "Outlook Analyzer" agent in AI Labs. Per-employee isolation comes from the
**API key** (owned by the employee — the agent reads *their* Outlook connection),
not from per-employee agents.

## Stack

- Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic
- `httpx` async client for the AI Labs API
- `APScheduler` in-process hourly cron
- `cryptography` (Fernet) to encrypt AI Labs API keys at rest
- managed with **uv**

## Frontend

`frontend/` — Vite + React + TS + Tailwind v4 dashboard (design reference:
Dribbble "CRM Web App — Email Outreach & Lead Engagement"). Pages: **Overview**
(KPI tiles + hourly volume chart + pending replies), **Employees** (+ per-employee
detail with snapshot history), **Onboarding** (companies + register form).

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 — proxies /api → localhost:8090
```

Demo data for the UI: `PYTHONPATH=. uv run python scripts/seed_demo.py` (`--wipe`
to remove).

## Quick start (local)

```bash
cp .env.example .env
# generate a real Fernet key and paste it into .env as FERNET_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker compose up -d          # Postgres on host port 5433
uv sync                       # install deps
uv run alembic upgrade head   # create schema
uv run python run_server.py   # API on http://localhost:8090  (docs at /docs)
```

Point `AILABS_BASE_URL` at the AI Labs API:
- **Dev:** `http://localhost:8000/api/v1`
- **Prod:** `https://ailabs.scaletechsolutions.ai/api/v1`

## API (all under `/api/v1`)

### Onboarding (frontend → this backend → AI Labs)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/onboarding/companies` | Register a company (`domain` and/or `ai_labs_org_id` required before provisioning; `analyzer_agent_id` if the shared agent already exists) |
| `POST` | `/onboarding/companies/{id}/setup-agent` | **Step 0, one-time:** create the org's shared analyzer agent (needs an AI Labs admin JWT). Then point `organizations.analyzer_agent_id` at it on the AI Labs side. |
| `POST` | `/onboarding/provision` | Steps 1–2: oauth-login **with org context** (auto-grants the shared agent), mint + **encrypt** the per-employee API key. Returns a short-lived JWT for the Outlook step. No agent is created here. |
| `GET`  | `/onboarding/outlook/auth-url` | Step 3a: Microsoft consent URL |
| `POST` | `/onboarding/employees/{id}/outlook/connect` | Step 3b: exchange OAuth code, mark connected |

The JWT returned by `/provision` is used **only** to finish the browser-driven
Outlook OAuth dance and is never persisted. The Outlook token itself never
reaches this backend.

### Dashboard (JSON)
| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/dashboard/employees?company_id=` | List employees |
| `GET`  | `/dashboard/employees/{id}` | Employee + latest snapshot + count |
| `GET`  | `/dashboard/employees/{id}/snapshots` | Snapshot history (paginated) |
| `POST` | `/dashboard/employees/{id}/run-now` | Trigger one analysis now (testing) |
| `POST` | `/dashboard/cron/run-now` | Trigger the full hourly batch now (testing) |

## Hourly cron (spec §4)

`APScheduler` fires `run_hourly_batch()` every `CRON_INTERVAL_MINUTES`. For each
Outlook-connected employee it calls `POST /public/agents/{id}/chat` with the
decrypted API key, `session_id=null` (fresh session each hour), parses the JSON
out of the free-text reply, and upserts one `mailbox_snapshot` per (employee, hour)
— idempotent. Runs are staggered by `CRON_STAGGER_SECONDS`.

- 401 from AI Labs → employee flagged `needs_reprovision` and skipped.
- Unparseable reply → snapshot stored with `status=parse_failed` and `raw_text` kept.
- Transient transport errors → retried with exponential backoff.

> Run the cron in a **single** process in production (not per API replica), or the
> batch fires N times. Set `CRON_ENABLED=false` on replicas that shouldn't schedule.

## Layout

```
app/
  core/        config, Fernet crypto, logging
  db/          engine, session, declarative Base
  models/      company, employee, mailbox_snapshot
  schemas/     onboarding + dashboard pydantic models
  services/    ailabs_client, onboarding, analysis, cron, prompts, json_parse
  api/routes/  onboarding, dashboard, health
  scheduler.py APScheduler wiring
migrations/    Alembic
```

## Notes / open items (spec §7–§8)

- **AI Labs side prerequisites:** add this backend's origin to `BACKEND_CORS_ORIGINS`;
  Outlook scope must include `offline_access` (+ `Mail.Read`) or the cron dies ~1h in;
  register the customer callback `redirect_uri` in the Azure app; per org, set
  `organizations.analyzer_agent_id` to the shared agent (spec §7). The auto-grant-at-login
  and grant-aware key minting ship on the AI Labs branch with migration `b7e2f1a9c3d4`.
- `POST /agents` on the live API is **multipart/form-data** (`data` = JSON-encoded
  AgentCreate), handled in `ailabs_client.create_agent`.
- Full end-to-end provisioning needs a real Microsoft ID token from a browser login.
```
