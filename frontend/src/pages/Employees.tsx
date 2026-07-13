import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { fmtDate } from '../lib/format'
import { SectionCard, Avatar, ConnectionPill, Tag } from '../components/ui'
import { SearchIcon } from '../components/icons'
import { EmptyRows, ErrorState } from './Overview'

export function EmployeesPage() {
  const { data, error, loading, reload } = useApi(() => api.employees(), [])
  const [search, setSearch] = useState('')

  const rows = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    return q ? data.filter((e) => e.email.toLowerCase().includes(q)) : data
  }, [data, search])

  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Employees</h1>
        <label className="relative ml-auto w-[300px]">
          <SearchIcon size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email…"
            className="w-full rounded-xl border border-line bg-surface py-2.5 pl-10 pr-4 text-[14px] placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-series-1/30"
          />
        </label>
      </div>

      <SectionCard
        title="Team"
        action={<span className="text-[13px] text-ink-3">{rows.length} employee(s)</span>}
      >
        {rows.length === 0 ? (
          <EmptyRows loading={loading} label="No employees yet — provision one from Onboarding." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[14px]">
              <thead>
                <tr className="bg-band text-left text-[13px] text-ink-2">
                  <th className="px-5 py-3 font-medium">Employee</th>
                  <th className="px-5 py-3 font-medium">Outlook</th>
                  <th className="px-5 py-3 font-medium">Agent</th>
                  <th className="px-5 py-3 font-medium">API key</th>
                  <th className="px-5 py-3 font-medium">Onboarded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {rows.map((e) => (
                  <tr key={e.id} className="hover:bg-band/60 transition-colors">
                    <td className="px-5 py-3.5">
                      <Link to={`/employees/${e.id}`} className="flex items-center gap-3 group">
                        <Avatar name={e.email} />
                        <span>
                          <span className="block font-medium group-hover:text-series-1">{e.email}</span>
                          {e.provider_email && e.provider_email !== e.email && (
                            <span className="block text-[12.5px] text-ink-3">{e.provider_email}</span>
                          )}
                        </span>
                      </Link>
                    </td>
                    <td className="px-5 py-3.5">
                      <ConnectionPill connected={e.outlook_connected} needsAttention={e.needs_reprovision} />
                    </td>
                    <td className="px-5 py-3.5">
                      <Tag tone="blue">Shared #{e.ai_labs_agent_id}</Tag>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[12.5px] text-ink-2">
                      {e.api_key_masked ?? '—'}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 date-serif text-ink-2">
                      {fmtDate(e.created_at)}
                    </td>
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
