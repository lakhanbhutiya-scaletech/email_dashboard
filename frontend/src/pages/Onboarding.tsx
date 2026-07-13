import { useState } from 'react'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { fmtDate } from '../lib/format'
import { SectionCard, Tag, StatusPill } from '../components/ui'
import { BuildingIcon } from '../components/icons'
import { EmptyRows, ErrorState } from './Overview'

export function OnboardingPage() {
  const { data, error, loading, reload } = useApi(() => api.companies(), [])
  const [form, setForm] = useState({ name: '', admin_email: '', domain: '', analyzer_agent_id: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await api.createCompany({
        name: form.name,
        admin_email: form.admin_email,
        domain: form.domain || null,
        analyzer_agent_id: form.analyzer_agent_id ? Number(form.analyzer_agent_id) : null,
      })
      setForm({ name: '', admin_email: '', domain: '', analyzer_agent_id: '' })
      reload()
    } catch (err) {
      setFormError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (error) return <ErrorState message={error} onRetry={reload} />

  const input =
    'w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-[14px] placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-series-1/30'

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Onboarding</h1>

      <div className="grid items-start gap-4 lg:grid-cols-[1fr_360px]">
        {/* companies */}
        <SectionCard title="Companies" action={<span className="text-[13px] text-ink-3">{data?.length ?? 0}</span>}>
          {!data || data.length === 0 ? (
            <EmptyRows loading={loading} label="No companies yet — register one to start." />
          ) : (
            <ul className="divide-y divide-line-soft">
              {data.map((c) => (
                <li key={c.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-sunken text-ink-2">
                    <BuildingIcon size={16} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[14.5px] font-medium">{c.name}</span>
                    <span className="block text-[12.5px] text-ink-3">
                      {c.domain ?? 'no domain'} · {c.admin_email}
                    </span>
                  </span>
                  <span className="ml-auto flex items-center gap-2">
                    {c.analyzer_agent_id !== null ? (
                      <Tag tone="blue">Shared agent #{c.analyzer_agent_id}</Tag>
                    ) : (
                      <StatusPill kind="warning" label="Agent not set up" />
                    )}
                    <span className="date-serif text-[13px] text-ink-3">{fmtDate(c.created_at)}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        {/* register form */}
        <SectionCard title="Register a company">
          <form onSubmit={submit} className="flex flex-col gap-3 p-5">
            <input required placeholder="Company name" className={input} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <input required type="email" placeholder="Admin email" className={input} value={form.admin_email}
              onChange={(e) => setForm({ ...form, admin_email: e.target.value })} />
            <input placeholder="Domain (e.g. acme.com) — used for agent auto-grant" className={input} value={form.domain}
              onChange={(e) => setForm({ ...form, domain: e.target.value })} />
            <input placeholder="Analyzer agent id (if it already exists)" className={input} inputMode="numeric"
              value={form.analyzer_agent_id}
              onChange={(e) => setForm({ ...form, analyzer_agent_id: e.target.value.replace(/\D/g, '') })} />
            {formError && <div className="text-[13px] text-critical break-all">{formError}</div>}
            <button
              type="submit"
              disabled={saving}
              className="mt-1 rounded-xl bg-ink px-4 py-2.5 text-[14px] font-medium text-surface transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Register company'}
            </button>
            <p className="text-[12.5px] leading-relaxed text-ink-3">
              Employees onboard from the customer app: Microsoft sign-in → provision (mints their
              API key against the shared agent) → Outlook consent. This dashboard reads the results.
            </p>
          </form>
        </SectionCard>
      </div>
    </div>
  )
}
