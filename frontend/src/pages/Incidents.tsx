import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTeam } from '../context/TeamContext'
import { listServices } from '../api/services'
import { listIncidents } from '../api/incidents'
import type { IncidentStatus } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'

const POLL_INTERVAL_MS = 15_000

export function Incidents() {
  const { selectedTeamId } = useTeam()
  const [status, setStatus] = useState<IncidentStatus | ''>('')
  const [serviceId, setServiceId] = useState<number | ''>('')

  const { data: services = [] } = useQuery({
    queryKey: ['services', selectedTeamId],
    queryFn: () => listServices(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const { data: incidents = [] } = useQuery({
    queryKey: ['incidents', selectedTeamId, status, serviceId],
    queryFn: () =>
      listIncidents({
        team: selectedTeamId ?? undefined,
        status: status || undefined,
        service: serviceId || undefined,
      }),
    enabled: selectedTeamId !== null,
    refetchInterval: POLL_INTERVAL_MS,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Incidents</h1>
        <div className="flex gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as IncidentStatus | '')}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">All statuses</option>
            <option value="triggered">Triggered</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
          <select
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value ? Number(e.target.value) : '')}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">All services</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Service</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {incidents.map((incident) => (
              <tr key={incident.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link
                    to={`/incidents/${incident.id}`}
                    className="font-medium text-indigo-600 hover:underline"
                  >
                    {incident.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{incident.service_name}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={incident.status} />
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {new Date(incident.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {incidents.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  No incidents match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
