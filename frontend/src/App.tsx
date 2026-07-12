import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { TeamProvider } from './context/TeamContext'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Schedules } from './pages/Schedules'
import { EscalationPolicies } from './pages/EscalationPolicies'
import { Services } from './pages/Services'
import { Incidents } from './pages/Incidents'
import { IncidentDetail } from './pages/IncidentDetail'

function LoginRoute() {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/" replace />
  return <Login />
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route
          element={
            <ProtectedRoute>
              <TeamProvider>
                <Layout />
              </TeamProvider>
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:id" element={<IncidentDetail />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/escalation-policies" element={<EscalationPolicies />} />
          <Route path="/services" element={<Services />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
