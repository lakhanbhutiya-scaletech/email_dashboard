import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Snapshot, type Thread } from '../lib/api'
import { useApi } from '../lib/useApi'
import { fmtNum, fmtMinutes, fmtDateTime, fmtHour } from '../lib/format'
import { SectionCard, StatTile, StatusPill, Avatar, ConnectionPill, PriorityBadge, type StatusKind } from '../components/ui'
import { VolumeChart } from '../components/VolumeChart'
import { InboxIcon, ReplyIcon, ClockIcon, MailIcon, AlertIcon, RefreshIcon } from '../components/icons'
import { EmptyRows, ErrorState } from './Overview'

const SNAPSHOT_STATUS: Record<Snapshot['status'], { kind: StatusKind; label: string }> = {
  ok: { kind: 'good', label: 'Analyzed' },
  parse_failed: { kind: 'warning', label: 'Parse failed' },
  empty: { kind: 'neutral', label: 'No mailbox' },
  error: { kind: 'critical', label: 'Error' },
}

const PRIORITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 }

/** Threads from the payload, newest schema first; falls back to the legacy
 * pending_replies + notable_threads shape so old snapshots still render. */
function deriveThreads(payload: Record<string, unknown> | null | undefined): Thread[] {
  if (!payload) return []
  const t = payload.threads
  if (Array.isArray(t)) return t as Thread[]
  const legacy: Thread[] = []
  for (const p of (payload.pending_replies as Thread[] | undefined) ?? [])
    legacy.push({ ...p, status: 'awaiting', priority: 'medium' })
  return legacy
}

export function EmployeeDetailPage() {
  const { id = '' } = useParams()
  const detail = useApi(() => api.employee(id), [id])
  const snaps = useApi(() => api.snapshots(id), [id])
  const [running, setRunning] = useState(false)

  const volume = useMemo(() => {
    if (!snaps.data) return []
    return snaps.data
      .filter((s) => s.status === 'ok' && s.payload)
      .map((s) => ({
        hour_bucket: s.hour_bucket,
        incoming: Number(s.payload?.incoming_count ?? 0),
        replied: Number(s.payload?.replied_count ?? 0),
      }))
      .reverse()
  }, [snaps.data])

  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />
  if (!detail.data) return <EmptyRows loading label="" />

  const { employee: emp, latest_snapshot: latest, snapshot_count } = detail.data
  const payload = latest?.status === 'ok' ? latest.payload : null
  const threads = deriveThreads(payload)
    .slice()
    .sort((a, b) => (PRIORITY_RANK[a.priority ?? 'medium'] ?? 1) - (PRIORITY_RANK[b.priority ?? 'medium'] ?? 1))
  const awaiting = threads.filter((t) => (t.status ?? 'awaiting') !== 'replied')
  const highPriority = awaiting.filter((t) => t.priority === 'high').length

  const runNow = async () => {
    setRunning(true)
    try {
      await api.runNow(id)
      detail.reload()
      snaps.reload()
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* header */}
      <div className="flex flex-wrap items-center gap-4">
        <Link to="/employees" className="text-[13.5px] text-ink-3 hover:text-ink">← Employees</Link>
        <span className="flex items-center gap-3">
          <Avatar name={emp.email} size={42} />
          <span>
            <h1 className="text-[20px] font-semibold tracking-[-0.02em] leading-tight">{emp.email}</h1>
            <span className="text-[13px] text-ink-3">
              Shared agent #{emp.ai_labs_agent_id} · key {emp.api_key_masked ?? '—'} · {snapshot_count} snapshot(s)
            </span>
          </span>
        </span>
        <span className="ml-auto flex items-center gap-3">
          <ConnectionPill connected={emp.outlook_connected} needsAttention={emp.needs_reprovision} />
          <button
            onClick={runNow}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-[13.5px] font-medium text-ink-2 hover:text-ink disabled:opacity-50"
          >
            <RefreshIcon size={14} className={running ? 'animate-spin' : ''} />
            {running ? 'Running…' : 'Run analysis now'}
          </button>
        </span>
      </div>

      {/* latest-hour KPIs */}
      <SectionCard
        title="Latest hour"
        action={
          latest && (
            <span className="flex items-center gap-3 text-[13px] text-ink-3">
              {fmtHour(latest.hour_bucket)}
              <StatusPill {...SNAPSHOT_STATUS[latest.status]} />
            </span>
          )
        }
      >
        <div className="grid grid-cols-2 divide-x divide-line-soft lg:grid-cols-5">
          <StatTile label="Incoming" icon={<InboxIcon size={18} />} value={fmtNum(payload?.incoming_count as number | undefined ?? null)} delta={null} hint="last analyzed hour" />
          <StatTile label="Replied" icon={<ReplyIcon size={18} />} value={fmtNum(payload?.replied_count as number | undefined ?? null)} delta={null} hint="last analyzed hour" />
          <StatTile label="Avg response" icon={<ClockIcon size={18} />} value={fmtMinutes(payload?.avg_response_minutes as number | undefined ?? null)} delta={null} hint="last analyzed hour" />
          <StatTile label="Awaiting reply" icon={<MailIcon size={18} />} value={fmtNum(awaiting.length)} delta={null} hint="last analyzed hour" />
          <StatTile label="High priority" icon={<AlertIcon size={18} />} value={fmtNum(highPriority)} delta={null} hint="awaiting now" />
        </div>
        {typeof payload?.sentiment_summary === 'string' && payload.sentiment_summary && (
          <div className="border-t border-line-soft px-5 py-4 text-[14px] text-ink-2">
            <span className="mr-2 font-semibold text-ink">Sentiment</span>
            {payload.sentiment_summary}
          </div>
        )}
      </SectionCard>

      {/* volume trend */}
      <SectionCard title="Volume by hour">
        <VolumeChart data={volume} />
      </SectionCard>

      {/* threads: the client's message and the reply that was sent */}
      <SectionCard
        title="Threads — incoming & reply"
        action={<span className="text-[13px] text-ink-3">{threads.length} this hour</span>}
      >
        {threads.length === 0 ? (
          <EmptyRows loading={false} label="No threads in the last analyzed hour." />
        ) : (
          <ul className="divide-y divide-line-soft">
            {threads.map((t, i) => {
              const replied = (t.status ?? 'awaiting') === 'replied'
              return (
                <li key={i} className="px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <Avatar name={t.from || '??'} size={30} />
                    <span className="min-w-0">
                      <span className="block truncate text-[14px] font-medium">{t.subject || '(no subject)'}</span>
                      <span className="block truncate text-[12.5px] text-ink-3">{t.from}</span>
                    </span>
                    <span className="ml-auto flex items-center gap-2">
                      <PriorityBadge priority={t.priority} />
                      <StatusPill
                        kind={replied ? 'good' : 'warning'}
                        label={replied ? 'Replied' : 'Awaiting'}
                        icon={replied ? <ReplyIcon size={13} /> : <MailIcon size={13} />}
                      />
                    </span>
                  </div>
                  {t.priority_reason && (
                    <div className="mt-2 text-[12.5px] text-ink-3">Why: {t.priority_reason}</div>
                  )}
                  {/* incoming message → reply, side by side */}
                  <div className="mt-2.5 grid gap-2.5 sm:grid-cols-2">
                    <div className="rounded-lg border border-line-soft bg-band px-3.5 py-2.5">
                      <div className="mb-1 text-[11.5px] font-semibold uppercase tracking-wide text-ink-3">
                        Client wrote{t.received_at ? ` · ${fmtDateTime(t.received_at)}` : ''}
                      </div>
                      <div className="text-[13.5px] text-ink-2">{t.incoming_excerpt || '—'}</div>
                    </div>
                    <div className={`rounded-lg border px-3.5 py-2.5 ${replied ? 'border-good/30 bg-good/5' : 'border-warning/40 bg-warning/5'}`}>
                      <div className="mb-1 text-[11.5px] font-semibold uppercase tracking-wide text-ink-3">
                        {replied ? `Reply sent${t.replied_at ? ` · ${fmtDateTime(t.replied_at)}` : ''}` : 'No reply yet'}
                      </div>
                      <div className="text-[13.5px] text-ink-2">
                        {replied ? (t.reply_excerpt || '—') : 'Awaiting a response from the employee.'}
                      </div>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </SectionCard>

      {/* snapshot history */}
      <SectionCard title="Snapshot history" action={<span className="text-[13px] text-ink-3">hourly runs</span>}>
        {!snaps.data || snaps.data.length === 0 ? (
          <EmptyRows loading={snaps.loading} label="No snapshots yet — run an analysis." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[14px]">
              <thead>
                <tr className="bg-band text-left text-[13px] text-ink-2">
                  <th className="px-5 py-3 font-medium">Captured</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Incoming</th>
                  <th className="px-5 py-3 font-medium">Replied</th>
                  <th className="px-5 py-3 font-medium">Session</th>
                  <th className="px-5 py-3 font-medium">Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {snaps.data.map((s) => (
                  <tr key={s.id} className="hover:bg-band/60 transition-colors">
                    <td className="whitespace-nowrap px-5 py-3 date-serif text-ink-2">{fmtDateTime(s.captured_at)}</td>
                    <td className="px-5 py-3"><StatusPill {...SNAPSHOT_STATUS[s.status]} /></td>
                    <td className="px-5 py-3 tnum">{fmtNum(s.payload?.incoming_count as number | undefined ?? null)}</td>
                    <td className="px-5 py-3 tnum">{fmtNum(s.payload?.replied_count as number | undefined ?? null)}</td>
                    <td className="px-5 py-3 tnum text-ink-2">{s.ai_labs_session_id ?? '—'}</td>
                    <td className="max-w-[260px] truncate px-5 py-3 text-[13px] text-ink-3">{s.error ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  )
}
