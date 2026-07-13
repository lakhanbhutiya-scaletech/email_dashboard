import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { getUser, setSession, getToken } from '../lib/auth'
import { MailIcon, PlugIcon, CheckIcon } from '../components/icons'

// Employee-facing "connect your mailbox" step. Real flow is the Microsoft consent
// dance (auth-url → redirect → connect); until Azure is wired we use the dev
// shim that marks the mailbox connected so the employee flow is walkable.
export function ConnectOutlookPage() {
  const nav = useNavigate()
  const user = getUser()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const connect = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.devConnectOutlook()
      // refresh cached session so guards see outlook_connected
      const token = getToken()
      if (token && user) setSession(token, { ...user, outlook_connected: true })
      nav('/me', { replace: true })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-6">
      <div className="w-full max-w-[440px] rounded-2xl border border-line bg-surface p-7 text-center shadow-[0_1px_3px_rgba(11,11,11,0.06)]">
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-series-1/10 text-series-1">
          <MailIcon size={22} />
        </span>
        <h1 className="text-[19px] font-semibold tracking-[-0.02em]">Connect your Outlook</h1>
        <p className="mx-auto mt-2 max-w-[340px] text-[13.5px] text-ink-2">
          To analyze your inbox and surface high-priority replies, connect your Outlook
          mailbox. Your emails stay in Microsoft — only the hourly analysis is stored.
        </p>

        <button
          onClick={connect}
          disabled={busy}
          className="mt-6 inline-flex w-full items-center justify-center gap-2.5 rounded-xl bg-ink px-4 py-3 text-[14.5px] font-medium text-surface transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <PlugIcon size={16} />
          {busy ? 'Connecting…' : 'Connect Outlook'}
        </button>

        <ul className="mt-5 space-y-1.5 text-left text-[12.5px] text-ink-3">
          <li className="flex items-center gap-2"><CheckIcon size={13} /> Read-only mailbox analysis</li>
          <li className="flex items-center gap-2"><CheckIcon size={13} /> Runs automatically every hour</li>
          <li className="flex items-center gap-2"><CheckIcon size={13} /> Disconnect any time</li>
        </ul>

        <p className="mt-4 text-[11.5px] text-ink-3">
          Dev mode: this simulates the Microsoft consent (Azure not wired yet).
        </p>
        {error && <p className="mt-3 text-[12.5px] text-critical">{error}</p>}
      </div>
    </div>
  )
}
