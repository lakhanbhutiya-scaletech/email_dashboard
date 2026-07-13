import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { fmtNum, fmtMinutes, fmtDateTime } from '../lib/format'
import { SectionCard, StatTile, Segmented, Avatar, Tag, PriorityBadge } from '../components/ui'
import { VolumeChart } from '../components/VolumeChart'
import { MailIcon, ReplyIcon, ClockIcon, InboxIcon, SearchIcon, RefreshIcon, AlertIcon } from '../components/icons'

type Range = '24h' | '48h'

export function OverviewPage() {
  const { data, error, loading, reload } = useApi(() => api.overview(), [])
  const [range, setRange] = useState<Range>('24h')
  const [search, setSearch] = useState('')
  const [running, setRunning] = useState(false)

  const series = useMemo(() => {
    if (!data) return []
    return range === '24h' ? data.volume_series.slice(-24) : data.volume_series
  }, [data, range])

  const pending = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    if (!q) return data.pending_replies
    return data.pending_replies.filter(
      (p) =>
        p.from_.toLowerCase().includes(q) ||
        p.subject.toLowerCase().includes(q) ||
        p.employee_email.toLowerCase().includes(q),
    )
  }, [data, search])

  const runCron = async () => {
    setRunning(true)
    try {
      await api.runCron()
      reload()
    } finally {
      setRunning(false)
    }
  }

  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div className="flex flex-col gap-6">
      {/* top bar: search + range + run-now */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="relative grow max-w-[340px]">
          <SearchIcon size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search pending replies…"
            className="w-full rounded-xl border border-line bg-surface py-2.5 pl-10 pr-4 text-[14px] placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-series-1/30"
          />
        </label>
        <Segmented<Range>
          options={[
            { value: '24h', label: 'Last 24 hours' },
            { value: '48h', label: 'Last 48 hours' },
          ]}
          value={range}
          onChange={setRange}
        />
        <button
          onClick={runCron}
          disabled={running}
          className="ml-auto inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-[13.5px] font-medium text-ink-2 transition-colors hover:text-ink disabled:opacity-50"
        >
          <RefreshIcon size={14} className={running ? 'animate-spin' : ''} />
          {running ? 'Running…' : 'Run analysis now'}
        </button>
      </div>

      {/* KPI groups — Initiation / Engagement style from the reference */}
      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Volume">
          <div className="grid grid-cols-2 divide-x divide-line-soft">
            <StatTile
              label="Incoming"
              icon={<InboxIcon size={18} />}
              value={loading ? '…' : fmtNum(data?.incoming.value)}
              delta={data?.incoming.delta ?? null}
            />
            <StatTile
              label="Replied"
              icon={<ReplyIcon size={18} />}
              value={loading ? '…' : fmtNum(data?.replied.value)}
              delta={data?.replied.delta ?? null}
            />
          </div>
        </SectionCard>
        <SectionCard title="Responsiveness">
          <div className="grid grid-cols-3 divide-x divide-line-soft">
            <StatTile
              label="Avg response time"
              icon={<ClockIcon size={18} />}
              value={loading ? '…' : fmtMinutes(data?.avg_response_minutes.value)}
              delta={data?.avg_response_minutes.delta ?? null}
              deltaGoodWhen="down"
            />
            <StatTile
              label="Awaiting reply"
              icon={<MailIcon size={18} />}
              value={loading ? '…' : fmtNum(data?.pending_count.value)}
              delta={data?.pending_count.delta ?? null}
              deltaGoodWhen="down"
            />
            <StatTile
              label="High priority"
              icon={<AlertIcon size={18} />}
              value={loading ? '…' : fmtNum(data?.high_priority.value)}
              delta={data?.high_priority.delta ?? null}
              deltaGoodWhen="down"
            />
          </div>
        </SectionCard>
      </div>

      {/* volume trend */}
      <SectionCard
        title="Email volume by hour"
        action={
          <span className="text-[13px] text-ink-3">
            {data ? `${data.employees_connected}/${data.employees_total} mailboxes connected` : ''}
          </span>
        }
      >
        <VolumeChart data={series} />
      </SectionCard>

      {/* pending replies table */}
      <SectionCard
        title="Pending replies"
        action={<span className="text-[13px] text-ink-3">{pending.length} awaiting response</span>}
      >
        {pending.length === 0 ? (
          <EmptyRows loading={loading} label="No pending replies — inbox zero." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[14px]">
              <thead>
                <tr className="bg-band text-left text-[13px] text-ink-2">
                  <th className="px-5 py-3 font-medium">Priority</th>
                  <th className="px-5 py-3 font-medium">From</th>
                  <th className="px-5 py-3 font-medium">Subject</th>
                  <th className="px-5 py-3 font-medium">Mailbox</th>
                  <th className="px-5 py-3 font-medium">Received</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {pending.map((p, i) => (
                  <tr key={`${p.employee_id}-${i}`} className="hover:bg-band/60 transition-colors">
                    <td className="px-5 py-3.5">
                      <PriorityBadge priority={p.priority} />
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="flex items-center gap-3">
                        <Avatar name={p.from_ || '??'} />
                        <span className="font-medium">{p.from_ || 'Unknown sender'}</span>
                      </span>
                    </td>
                    <td className="max-w-[340px] px-5 py-3.5">
                      <span className="block truncate font-medium">{p.subject}</span>
                      {(p.incoming_excerpt || p.priority_reason) && (
                        <span className="mt-0.5 block truncate text-[12.5px] text-ink-3">
                          {p.incoming_excerpt || p.priority_reason}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <Link to={`/employees/${p.employee_id}`} className="text-series-1 hover:underline">
                        {p.employee_email}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 date-serif text-ink-2">
                      {fmtDateTime(p.received_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {data && data.employees_needing_attention > 0 && (
        <div className="flex items-center gap-3 rounded-2xl border border-critical/30 bg-critical/5 px-5 py-3.5 text-[14px]">
          <Tag tone="red">{data.employees_needing_attention} employee(s)</Tag>
          <span className="text-ink-2">
            have a revoked API key and need re-provisioning —{' '}
            <Link to="/employees" className="font-medium text-series-1 hover:underline">
              review employees
            </Link>
          </span>
        </div>
      )}
    </div>
  )
}

export function EmptyRows({ loading, label }: { loading: boolean; label: string }) {
  return (
    <div className="flex h-[120px] items-center justify-center text-[13.5px] text-ink-3">
      {loading ? 'Loading…' : label}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-2xl border border-critical/30 bg-critical/5 p-6">
      <div className="font-semibold">Couldn't reach the backend</div>
      <div className="text-[13.5px] text-ink-2 break-all">{message}</div>
      <button
        onClick={onRetry}
        className="rounded-lg border border-line bg-surface px-4 py-2 text-[13.5px] font-medium hover:bg-band"
      >
        Retry
      </button>
    </div>
  )
}
