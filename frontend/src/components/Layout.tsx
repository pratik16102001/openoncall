import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTeam } from '../context/TeamContext'
import { CreateFirstTeam } from './CreateFirstTeam'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/incidents', label: 'Incidents' },
  { to: '/schedules', label: 'Schedules' },
  { to: '/escalation-policies', label: 'Escalation Policies' },
  { to: '/services', label: 'Services' },
]

export function Layout() {
  const { logout } = useAuth()
  const { teams, selectedTeamId, selectTeam, isLoading } = useTeam()

  if (!isLoading && teams.length === 0) {
    return <CreateFirstTeam />
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold">OpenOnCall</span>
            <nav className="flex gap-4">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `text-sm font-medium ${isActive ? 'text-indigo-600' : 'text-gray-600 hover:text-gray-900'}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {teams.length > 0 && (
              <select
                className="rounded border border-gray-300 px-2 py-1 text-sm"
                value={selectedTeamId ?? ''}
                onChange={(e) => selectTeam(Number(e.target.value))}
              >
                {teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={logout}
              className="text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
