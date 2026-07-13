import { StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import './index.css'
import { Layout } from './components/Layout'
import { OverviewPage } from './pages/Overview'
import { EmployeesPage } from './pages/Employees'
import { EmployeeDetailPage } from './pages/EmployeeDetail'
import { OnboardingPage } from './pages/Onboarding'
import { LoginPage } from './pages/Login'
import { ConnectOutlookPage } from './pages/ConnectOutlook'
import { MePage } from './pages/Me'
import { isAuthed, getUser } from './lib/auth'

function RequireAuth({ children }: { children: ReactNode }) {
  if (!isAuthed()) return <Navigate to="/login" replace />
  return <>{children}</>
}

// Admin-only: employees are bounced to their own mailbox view.
function AdminOnly({ children }: { children: ReactNode }) {
  const user = getUser()
  if (user?.role !== 'admin') return <Navigate to="/me" replace />
  return <>{children}</>
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/connect-outlook',
    element: (
      <RequireAuth>
        <ConnectOutlookPage />
      </RequireAuth>
    ),
  },
  {
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { path: '/', element: <AdminOnly><OverviewPage /></AdminOnly> },
      { path: '/employees', element: <AdminOnly><EmployeesPage /></AdminOnly> },
      { path: '/employees/:id', element: <AdminOnly><EmployeeDetailPage /></AdminOnly> },
      { path: '/me', element: <MePage /> },
      // Vendor/admin-only company setup — intentionally not in the nav.
      { path: '/onboarding', element: <AdminOnly><OnboardingPage /></AdminOnly> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
