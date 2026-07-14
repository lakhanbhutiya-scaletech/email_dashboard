import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { setSession, isAuthed, getUser } from '../lib/auth'
import { MailIcon } from '../components/icons'
import { microsoftSsoConfigured, signInWithMicrosoft } from '../lib/firebase'

// Seeded accounts for the dev sign-in shim (see scripts/seed_demo.py).
const DEV_ACCOUNTS = [
  { email: 'admin@demo.co', label: 'Admin (sales manager)', role: 'admin' },
  { email: 'liam.anderson@demo.co', label: 'Liam Anderson', role: 'employee' },
  { email: 'sophia.bennett@demo.co', label: 'Sophia Bennett', role: 'employee' },
  { email: 'ethan.parker@demo.co', label: 'Ethan Parker', role: 'employee' },
  { email: 'maya.iyer@demo.co', label: 'Maya Iyer (no Outlook yet)', role: 'employee' },
]

function landing(user: { role: string; outlook_connected?: boolean | null }): string {
  if (user.role === 'admin') return '/'
  return user.outlook_connected ? '/me' : '/connect-outlook'
}

export function LoginPage() {
  const nav = useNavigate()
  const [busy, setBusy] = useState<string | null>(null)
  const [msNote, setMsNote] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Already signed in → skip the login screen.
  useEffect(() => {
    if (isAuthed()) {
      const u = getUser()
      if (u) nav(landing(u), { replace: true })
    }
  }, [nav])

  const signIn = async (email: string) => {
    setBusy(email)
    setError(null)
    try {
      const { token, user } = await api.devLogin(email)
      setSession(token, user)
      nav(landing(user), { replace: true })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const signInMicrosoft = async () => {
    if (!microsoftSsoConfigured) {
      setMsNote(true)
      return
    }
    setBusy('microsoft')
    setError(null)
    try {
      const idToken = await signInWithMicrosoft()
      // Verifies the token via AI Labs' oauth-login, then maps the email to a
      // registered admin/employee here (see app/api/routes/auth.py:microsoft_login).
      const { token, user } = await api.microsoftLogin(idToken)
      setSession(token, user)
      nav(landing(user), { replace: true })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-band px-6">
      <div className="w-full max-w-[400px]">
        <div className="mb-7 flex flex-col items-center gap-3 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-ink text-surface">
            <MailIcon size={22} />
          </span>
          <div>
            <div className="text-[20px] font-semibold tracking-[-0.02em]">Sales Outlook</div>
            <div className="text-[13.5px] text-ink-3">Sign in to your engagement dashboard</div>
          </div>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-6 shadow-[0_1px_3px_rgba(11,11,11,0.06)]">
          {/* Primary: Microsoft SSO */}
          <button
            onClick={signInMicrosoft}
            disabled={!!busy}
            className="flex w-full items-center justify-center gap-2.5 rounded-xl border border-line bg-surface px-4 py-3 text-[14.5px] font-medium transition-colors hover:bg-band disabled:opacity-50"
          >
            <MsLogo />
            {busy === 'microsoft' ? 'Signing in…' : 'Sign in with Microsoft'}
          </button>
          {msNote && (
            <p className="mt-2.5 rounded-lg bg-warning/10 px-3 py-2 text-[12.5px] text-[#8a6200] dark:text-warning">
              Microsoft SSO isn’t configured yet (needs the Azure app registration). Use a
              developer sign-in below to explore the app.
            </p>
          )}

          {/* Dev sign-in shim */}
          <div className="my-5 flex items-center gap-3 text-[12px] text-ink-3">
            <span className="h-px flex-1 bg-line-soft" />
            developer sign-in
            <span className="h-px flex-1 bg-line-soft" />
          </div>

          <div className="flex flex-col gap-2">
            {DEV_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                onClick={() => signIn(a.email)}
                disabled={!!busy}
                className="flex items-center justify-between rounded-xl border border-line bg-surface px-4 py-2.5 text-left transition-colors hover:bg-band disabled:opacity-50"
              >
                <span>
                  <span className="block text-[14px] font-medium">{a.label}</span>
                  <span className="block text-[12px] text-ink-3">{a.email}</span>
                </span>
                <span className="rounded-full bg-sunken px-2 py-0.5 text-[11.5px] font-medium capitalize text-ink-2">
                  {busy === a.email ? '…' : a.role}
                </span>
              </button>
            ))}
          </div>

          {error && <p className="mt-3 text-[12.5px] text-critical">{error}</p>}
        </div>
      </div>
    </div>
  )
}

function MsLogo() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
      <rect x="0" y="0" width="7" height="7" fill="#F25022" />
      <rect x="9" y="0" width="7" height="7" fill="#7FBA00" />
      <rect x="0" y="9" width="7" height="7" fill="#00A4EF" />
      <rect x="9" y="9" width="7" height="7" fill="#FFB900" />
    </svg>
  )
}
