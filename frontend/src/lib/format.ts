export function fmtNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(1)
}

export function fmtMinutes(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  if (v < 60) return `${Math.round(v)}m`
  return `${Math.floor(v / 60)}h ${Math.round(v % 60)}m`
}

/** "2026-07-13T09" (hour bucket) or ISO timestamp → "Jul 13, 09:00" */
export function fmtHour(bucket: string): string {
  const d = new Date(bucket.length === 13 ? `${bucket}:00:00Z` : bucket)
  if (Number.isNaN(d.getTime())) return bucket
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function initials(nameOrEmail: string): string {
  const base = nameOrEmail.split('@')[0]
  const parts = base.split(/[.\s_-]+/).filter(Boolean)
  return (parts.length >= 2 ? parts[0][0] + parts[1][0] : base.slice(0, 2)).toUpperCase()
}

/** Stable avatar tint per identity — series hues at low alpha, text stays ink. */
const AVATAR_HUES = ['#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#e87ba4', '#eb6834']
export function avatarColor(key: string): string {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return AVATAR_HUES[h % AVATAR_HUES.length]
}
