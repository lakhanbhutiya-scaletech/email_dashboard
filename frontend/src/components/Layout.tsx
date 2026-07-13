import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { GridIcon, UsersIcon, InboxIcon, MailIcon } from './icons'
import { getUser, clearSession } from '../lib/auth'

const ADMIN_NAV = [
  { to: '/', label: 'Overview', icon: GridIcon, end: true },
  { to: '/employees', label: 'Employees', icon: UsersIcon, end: false },
]
const EMPLOYEE_NAV = [{ to: '/me', label: 'My mailbox', icon: InboxIcon, end: true }]

export function Layout() {
  const nav = useNavigate()
  const user = getUser()
  const items = user?.role === 'admin' ? ADMIN_NAV : EMPLOYEE_NAV

  const signOut = () => {
    clearSession()
    nav('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen">
      {/* sidebar */}
      <aside className="sticky top-0 flex h-screen w-[228px] shrink-0 flex-col border-r border-line bg-surface px-4 py-5">
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-surface">
            <MailIcon size={16} />
          </span>
          <div>
            <div className="text-[14.5px] font-semibold leading-tight tracking-[-0.01em]">Sales Outlook</div>
            <div className="text-[12px] text-ink-3 leading-tight">
              {user?.role === 'admin' ? 'Admin dashboard' : 'My engagement'}
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-[14px] font-medium transition-colors ${
                  isActive ? 'bg-sunken text-ink' : 'text-ink-2 hover:bg-sunken/60 hover:text-ink'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* user + sign out */}
        <div className="mt-auto flex flex-col gap-2">
          <div className="rounded-xl border border-line bg-band px-3.5 py-2.5">
            <div className="truncate text-[12.5px] font-medium">{user?.email}</div>
            <div className="text-[11.5px] capitalize text-ink-3">{user?.role}</div>
          </div>
          <button
            onClick={signOut}
            className="rounded-lg px-3 py-2 text-left text-[13px] font-medium text-ink-2 transition-colors hover:bg-sunken/60 hover:text-ink"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* main */}
      <main className="min-w-0 flex-1 px-8 py-7">
        <div className="mx-auto max-w-[1100px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
