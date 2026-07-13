// Typed client for the customer backend (see app/api/routes/*).
import { getToken, clearSession, type SessionUser } from './auth'

const BASE = '/api/v1'

function authHeaders(): Record<string, string> {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

function handle401(status: number): void {
  // Session expired/invalid → drop it and bounce to login.
  if (status === 401) {
    clearSession()
    if (!location.pathname.startsWith('/login')) location.assign('/login')
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { ...authHeaders() } })
  if (!res.ok) {
    handle401(res.status)
    throw new Error(`${res.status} ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    handle401(res.status)
    throw new Error(`${res.status} ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

// ── Types (mirror app/schemas) ──────────────────────────────────────────────

export interface KpiValue { value: number | null; delta: number | null }
export interface PendingReply {
  employee_id: string
  employee_email: string
  from_: string
  subject: string
  received_at: string
  priority: string          // "high" | "medium" | "low"
  priority_reason: string
  incoming_excerpt: string
}
export interface VolumePoint { hour_bucket: string; incoming: number; replied: number }
export interface Overview {
  employees_total: number
  employees_connected: number
  employees_needing_attention: number
  incoming: KpiValue
  replied: KpiValue
  avg_response_minutes: KpiValue
  pending_count: KpiValue
  high_priority: KpiValue
  pending_replies: PendingReply[]
  volume_series: VolumePoint[]
}

// A thread from a snapshot payload (payload.threads[]) — incoming + the reply sent.
export interface Thread {
  from?: string
  subject?: string
  received_at?: string
  priority?: string
  priority_reason?: string
  incoming_excerpt?: string
  status?: 'awaiting' | 'replied'
  reply_excerpt?: string | null
  replied_at?: string | null
}

export interface Employee {
  id: string
  company_id: string
  email: string
  ai_labs_user_id: string
  ai_labs_agent_id: number
  api_key_masked: string | null
  outlook_connected: boolean
  provider_email: string | null
  needs_reprovision: boolean
  created_at: string
}

export interface Snapshot {
  id: string
  employee_id: string
  captured_at: string
  hour_bucket: string
  payload: Record<string, unknown> | null
  ai_labs_session_id: number | null
  status: 'ok' | 'parse_failed' | 'empty' | 'error'
  error: string | null
}

export interface EmployeeDashboard {
  employee: Employee
  latest_snapshot: Snapshot | null
  snapshot_count: number
}

export interface Company {
  id: string
  name: string
  admin_email: string
  domain: string | null
  ai_labs_org_id: string | null
  analyzer_agent_id: number | null
  created_at: string
}

// ── Calls ───────────────────────────────────────────────────────────────────

export const api = {
  overview: (companyId?: string) =>
    get<Overview>(`/dashboard/overview${companyId ? `?company_id=${companyId}` : ''}`),
  employees: (companyId?: string) =>
    get<Employee[]>(`/dashboard/employees${companyId ? `?company_id=${companyId}` : ''}`),
  employee: (id: string) => get<EmployeeDashboard>(`/dashboard/employees/${id}`),
  snapshots: (id: string, limit = 50) =>
    get<Snapshot[]>(`/dashboard/employees/${id}/snapshots?limit=${limit}`),
  runNow: (id: string) => post<{ status: string }>(`/dashboard/employees/${id}/run-now`),
  runCron: () => post<{ tally: Record<string, number> }>(`/dashboard/cron/run-now`),
  companies: () => get<Company[]>(`/onboarding/companies`),
  createCompany: (body: {
    name: string; admin_email: string; domain?: string | null
    ai_labs_org_id?: string | null; analyzer_agent_id?: number | null
  }) => post<Company>(`/onboarding/companies`, body),

  // ── Auth + employee self-service ──
  devLogin: (email: string) =>
    post<{ token: string; user: SessionUser }>(`/auth/dev-login`, { email }),
  authMe: () => get<SessionUser>(`/auth/me`),
  myDashboard: () => get<EmployeeDashboard>(`/me/dashboard`),
  mySnapshots: (limit = 50) => get<Snapshot[]>(`/me/snapshots?limit=${limit}`),
  devConnectOutlook: () =>
    post<{ outlook_connected: boolean; provider_email: string }>(`/me/outlook/dev-connect`),
}
