import { useMemo, useRef, useState } from 'react'
import type { VolumePoint } from '../lib/api'
import { fmtHour } from '../lib/format'

/**
 * Hourly email volume — two series (Incoming: area+line, Replied: line).
 * Dataviz rules applied: 2px lines, recessive hairline grid, legend + direct
 * labels for 2 series, crosshair + shared tooltip on hover, markers ≥8px with
 * a 2px surface ring, text in ink tokens (never series color).
 */
const M = { top: 16, right: 76, bottom: 26, left: 40 }

export function VolumeChart({ data }: { data: VolumePoint[] }) {
  const [hover, setHover] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const W = 860
  const H = 240

  const { xs, yI, yR, ticks, yMax } = useMemo(() => {
    const n = Math.max(data.length, 1)
    const innerW = W - M.left - M.right
    const innerH = H - M.top - M.bottom
    const max = Math.max(1, ...data.map((d) => Math.max(d.incoming, d.replied)))
    // round y-max up to a clean step
    const step = Math.pow(10, Math.floor(Math.log10(max)))
    const yMax = Math.ceil(max / step) * step
    const x = (i: number) => M.left + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
    const y = (v: number) => M.top + innerH - (v / yMax) * innerH
    return {
      xs: data.map((_, i) => x(i)),
      yI: data.map((d) => y(d.incoming)),
      yR: data.map((d) => y(d.replied)),
      ticks: [0, 0.25, 0.5, 0.75, 1].map((f) => ({ v: Math.round(yMax * f), y: y(yMax * f) })),
      yMax,
    }
  }, [data])

  if (data.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center text-[13px] text-ink-3">
        No snapshot data yet — volume appears after the first hourly run.
      </div>
    )
  }

  const line = (ys: number[]) => xs.map((x, i) => `${i === 0 ? 'M' : 'L'}${x},${ys[i]}`).join(' ')
  const area = `${line(yI)} L${xs[xs.length - 1]},${H - M.bottom} L${xs[0]},${H - M.bottom} Z`

  const onMove = (e: React.MouseEvent) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const px = ((e.clientX - rect.left) / rect.width) * W
    let best = 0
    for (let i = 1; i < xs.length; i++) if (Math.abs(xs[i] - px) < Math.abs(xs[best] - px)) best = i
    setHover(best)
  }

  const h = hover !== null ? data[hover] : null
  const xLabelEvery = Math.max(1, Math.ceil(data.length / 6))

  return (
    <div className="relative">
      {/* legend — always present for 2 series */}
      <div className="flex items-center gap-4 px-5 pt-4 text-[13px] text-ink-2">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-[3px] w-4 rounded-full bg-series-1" /> Incoming
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-[3px] w-4 rounded-full bg-series-2" /> Replied
        </span>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label={`Hourly email volume, ${data.length} hours, max ${yMax}`}
      >
        {/* recessive grid */}
        {ticks.map((t) => (
          <g key={t.v}>
            <line x1={M.left} x2={W - M.right} y1={t.y} y2={t.y} className="stroke-line-soft" strokeWidth={1} />
            <text x={M.left - 8} y={t.y + 4} textAnchor="end" className="fill-ink-3 tnum" fontSize={11}>
              {t.v}
            </text>
          </g>
        ))}

        {/* x labels */}
        {data.map((d, i) =>
          i % xLabelEvery === 0 ? (
            <text key={d.hour_bucket} x={xs[i]} y={H - 8} textAnchor="middle" className="fill-ink-3" fontSize={11}>
              {fmtHour(d.hour_bucket)}
            </text>
          ) : null,
        )}

        {/* incoming: soft area + 2px line */}
        <path d={area} className="fill-series-1" opacity={0.12} />
        <path d={line(yI)} className="stroke-series-1" strokeWidth={2} fill="none" />
        {/* replied: 2px line */}
        <path d={line(yR)} className="stroke-series-2" strokeWidth={2} fill="none" />

        {/* direct labels at last point (text in ink, mark carries identity) */}
        <g fontSize={12} className="fill-ink-2">
          <circle cx={xs[xs.length - 1]} cy={yI[yI.length - 1]} r={4} className="fill-series-1" />
          <text x={xs[xs.length - 1] + 10} y={yI[yI.length - 1] + 4}>Incoming</text>
          <circle cx={xs[xs.length - 1]} cy={yR[yR.length - 1]} r={4} className="fill-series-2" />
          <text x={xs[xs.length - 1] + 10} y={yR[yR.length - 1] + 4}>Replied</text>
        </g>

        {/* crosshair + hover markers with 2px surface ring */}
        {hover !== null && (
          <g>
            <line x1={xs[hover]} x2={xs[hover]} y1={M.top} y2={H - M.bottom} className="stroke-ink-3" strokeWidth={1} strokeDasharray="3 3" />
            <circle cx={xs[hover]} cy={yI[hover]} r={5} className="fill-series-1 stroke-surface" strokeWidth={2} />
            <circle cx={xs[hover]} cy={yR[hover]} r={5} className="fill-series-2 stroke-surface" strokeWidth={2} />
          </g>
        )}
      </svg>

      {/* shared tooltip */}
      {h && hover !== null && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-line bg-surface px-3 py-2 text-[13px] shadow-lg"
          style={{
            left: `${(xs[hover] / W) * 100}%`,
            top: 30,
            transform: xs[hover] > W * 0.7 ? 'translateX(-108%)' : 'translateX(8%)',
          }}
        >
          <div className="mb-1 font-medium text-ink">{fmtHour(h.hour_bucket)}</div>
          <div className="flex items-center gap-2 text-ink-2">
            <span className="h-2 w-2 rounded-full bg-series-1" /> Incoming
            <span className="ml-auto pl-3 font-semibold text-ink tnum">{h.incoming}</span>
          </div>
          <div className="flex items-center gap-2 text-ink-2">
            <span className="h-2 w-2 rounded-full bg-series-2" /> Replied
            <span className="ml-auto pl-3 font-semibold text-ink tnum">{h.replied}</span>
          </div>
        </div>
      )}
    </div>
  )
}
