// Browser-side session: the token this backend issued at login, plus the user.
// Stored in localStorage; attached as a Bearer header by lib/api.ts.

export interface SessionUser {
  email: string
  role: 'admin' | 'employee'
  company_id: string
  employee_id: string | null
  outlook_connected?: boolean | null
  api_key_masked?: string | null
}

const TOKEN_KEY = 'sod_token'
const USER_KEY = 'sod_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getUser(): SessionUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as SessionUser
  } catch {
    return null
  }
}

export function setSession(token: string, user: SessionUser): void {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAuthed(): boolean {
  return !!getToken()
}
