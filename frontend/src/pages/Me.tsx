import { useMemo } from 'react'
import { api, type Thread } from '../lib/api'
import { useApi } from '../lib/useApi'
import { fmtNum, fmtMinutes, fmtDateTime, fmtHour } from '../lib/format'
import { SectionCard, StatTile, StatusPill, Avatar, PriorityBadge } from '../components/ui'
import { VolumeChart } from '../components/VolumeChart'
import { InboxIcon, ReplyIcon, ClockIcon, MailIcon, AlertIcon } from '../components/icons'
import { EmptyRows, ErrorState } from './Overview'
import { getUser } from '../lib/auth'

const PRIORITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 }

function deriveThreads(payload: Record<string, unknown> | null | undefined): Thread[] {
  if (!payload) return []
  const t = payload.threads
  if (Array.isArray(t)) return t as Thread[]
  const legacy: Thread[] = []
  for (const p of (payload.pending_replies as Thread[] | undefined) ?? [])
    legacy.push({ ...p, status: 'awaiting', priority: 'medium' })
  return legacy
}

export function MePage() {
  const user = getUser()
  const detail = useApi(() => api.myDashboard(), [])
  const snaps = useApi(() => api.mySnapshots(), [])

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

  const { latest_snapshot: latest } = detail.data
  const payload = latest?.status === 'ok' ? latest.payload : null
  const threads = deriveThreads(payload)
    .slice()
    .sort((a, b) => (PRIORITY_RANK[a.priority ?? 'medium'] ?? 1) - (PRIORITY_RANK[b.priority ?? 'medium'] ?? 1))
  const awaiting = threads.filter((t) => (t.status ?? 'awaiting') !== 'replied')
  const highPriority = awaiting.filter((t) => t.priority === 'high').length

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-[20px] font-semibold tracking-[-0.02em]">My mailbox</h1>
          <span className="text-[13px] text-ink-3">{user?.email}</span>
        </div>
        {latest && (
          <span className="ml-auto text-[13px] text-ink-3">Last analyzed {fmtHour(latest.hour_bucket)}</span>
        )}
      </div>

      {highPriority > 0 && (
        <div className="flex items-center gap-3 rounded-2xl border border-critical/30 bg-critical/5 px-5 py-3.5 text-[14px]">
          <AlertIcon size={16} className="text-critical" />
          <span className="text-ink-2">
            <span className="font-semibold text-ink">{highPriority}</span> high-priority{' '}
            {highPriority === 1 ? 'reply is' : 'replies are'} waiting on you.
          </span>
        </div>
      )}

      <SectionCard title="This hour">
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

      <SectionCard title="Volume by hour">
        <VolumeChart data={volume} />
      </SectionCard>

      <SectionCard
        title="My threads — incoming & reply"
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
                        {replied ? (t.reply_excerpt || '—') : 'You haven’t replied yet.'}
                      </div>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </SectionCard>
    </div>
  )
}
