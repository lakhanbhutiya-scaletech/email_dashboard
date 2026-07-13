import type { ReactNode } from 'react'
import { ArrowUpRight, ArrowDownRight, MinusIcon, CheckIcon, AlertIcon, ClockIcon, PlugIcon } from './icons'
import { avatarColor, initials } from '../lib/format'

/* ── Section card: muted header band + white body (reference: Initiation / Engagement) ── */
export function SectionCard({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-surface overflow-hidden">
      <header className="flex items-center justify-between bg-band px-5 py-3 border-b border-line-soft">
        <h2 className="text-[15px] font-semibold tracking-[-0.01em]">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  )
}

/* ── Stat tile: label / icon + value + delta badge / "vs last period" ── */
export function StatTile({ label, icon, value, delta, deltaGoodWhen = 'up', hint = 'vs last hour' }: {
  label: string
  icon: ReactNode
  value: string
  delta: number | null
  /** 'up' = increase is good (green); 'down' = decrease is good (e.g. response time) */
  deltaGoodWhen?: 'up' | 'down'
  hint?: string
}) {
  return (
    <div className="flex flex-col gap-3 px-5 py-4">
      <div className="text-[13px] text-ink-2">{label}</div>
      <div className="flex items-center gap-3">
        <span className="text-ink-3">{icon}</span>
        <span className="text-[30px]/none font-semibold tracking-[-0.02em] tnum">{value}</span>
        <DeltaBadge delta={delta} goodWhen={deltaGoodWhen} />
      </div>
      <div className="text-[13px] text-ink-3">{hint}</div>
    </div>
  )
}

export function DeltaBadge({ delta, goodWhen = 'up' }: { delta: number | null; goodWhen?: 'up' | 'down' }) {
  if (delta === null || delta === undefined) return null
  const flat = Math.abs(delta) < 1e-9
  const up = delta > 0
  const good = flat ? null : (up ? goodWhen === 'up' : goodWhen === 'down')
  const cls = flat
    ? 'bg-sunken text-ink-2'
    : good
      ? 'bg-delta-good-bg text-delta-good'
      : 'bg-delta-bad-bg text-delta-bad'
  const Icon = flat ? MinusIcon : up ? ArrowUpRight : ArrowDownRight
  const n = Math.abs(delta)
  return (
    <span className={`ml-auto inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[13px] font-semibold tnum ${cls}`}>
      <Icon size={13} />
      {Number.isInteger(n) ? n : n.toFixed(1)}
    </span>
  )
}

/* ── Status pill: outline pill, icon + label (never color alone) ── */
export type StatusKind = 'good' | 'warning' | 'serious' | 'critical' | 'neutral'

const STATUS_STYLES: Record<StatusKind, string> = {
  good: 'text-good border-good/40 bg-good/5',
  warning: 'text-[#8a6200] dark:text-warning border-warning/50 bg-warning/10',
  serious: 'text-[#a04a24] dark:text-serious border-serious/50 bg-serious/10',
  critical: 'text-critical border-critical/40 bg-critical/5',
  neutral: 'text-ink-2 border-line bg-sunken/60',
}
const STATUS_ICONS: Record<StatusKind, ReactNode> = {
  good: <CheckIcon size={13} />,
  warning: <AlertIcon size={13} />,
  serious: <AlertIcon size={13} />,
  critical: <AlertIcon size={13} />,
  neutral: <ClockIcon size={13} />,
}

export function StatusPill({ kind, label, icon }: { kind: StatusKind; label: string; icon?: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[13px] font-medium whitespace-nowrap ${STATUS_STYLES[kind]}`}>
      {icon ?? STATUS_ICONS[kind]}
      {label}
    </span>
  )
}

/* ── Tinted tag chip (Hot Lead / High Priority style) ── */
export function Tag({ tone, children }: { tone: 'red' | 'amber' | 'gray' | 'green' | 'blue'; children: ReactNode }) {
  const tones = {
    red: 'bg-critical/10 text-critical',
    amber: 'bg-warning/15 text-[#8a6200] dark:text-warning',
    gray: 'bg-sunken text-ink-2',
    green: 'bg-good/10 text-good',
    blue: 'bg-series-1/10 text-series-1',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[13px] font-medium whitespace-nowrap ${tones[tone]}`}>
      {children}
    </span>
  )
}

/* ── Priority badge (high / medium / low) ── */
export function PriorityBadge({ priority }: { priority?: string }) {
  const p = (priority || 'medium').toLowerCase()
  const tone: 'red' | 'amber' | 'gray' = p === 'high' ? 'red' : p === 'low' ? 'gray' : 'amber'
  const label = p === 'high' ? 'High' : p === 'low' ? 'Low' : 'Medium'
  return <Tag tone={tone}>{label} priority</Tag>
}

/* ── Avatar circle with initials ── */
export function Avatar({ name, size = 34 }: { name: string; size?: number }) {
  const c = avatarColor(name)
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold select-none"
      style={{ width: size, height: size, background: `${c}22`, color: c, fontSize: size * 0.38 }}
      aria-hidden
    >
      {initials(name)}
    </span>
  )
}

/* ── Segmented control (Today / Last 7 days / …) ── */
export function Segmented<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-xl bg-sunken p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-lg px-3.5 py-1.5 text-[13.5px] font-medium transition-colors ${
            o.value === value
              ? 'bg-surface text-ink shadow-[0_1px_2px_rgba(11,11,11,0.08)] border border-line'
              : 'text-ink-2 hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* ── Outlook connection pill used in tables ── */
export function ConnectionPill({ connected, needsAttention }: { connected: boolean; needsAttention: boolean }) {
  if (needsAttention) return <StatusPill kind="critical" label="Needs re-provision" />
  if (connected) return <StatusPill kind="good" label="Connected" icon={<PlugIcon size={13} />} />
  return <StatusPill kind="neutral" label="Not connected" icon={<PlugIcon size={13} />} />
}
