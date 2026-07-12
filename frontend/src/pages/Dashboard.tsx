import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTeam } from '../context/TeamContext'
import { listSchedules, getOnCall } from '../api/schedules'
import { listIncidents, acknowledgeIncident } from '../api/incidents'
import { StatusBadge } from '../components/StatusBadge'

const POLL_INTERVAL_MS = 15_000

export function Dashboard() {
  const { selectedTeamId } = useTeam()
  const queryClient = useQueryClient()

  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules', selectedTeamId],
    queryFn: () => listSchedules(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const { data: openIncidents = [] } = useQuery({
    queryKey: ['incidents', 'open', selectedTeamId],
    queryFn: () =>
      listIncidents({ team: selectedTeamId ?? undefined }).then((incidents) =>
        incidents.filter((i) => i.status !== 'resolved'),
      ),
    enabled: selectedTeamId !== null,
    refetchInterval: POLL_INTERVAL_MS,
  })

  async function handleAcknowledge(id: number) {
    await acknowledgeIncident(id)
    queryClient.invalidateQueries({ queryKey: ['incidents'] })
  }

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-semibold">Who's on call</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {schedules.length === 0 && (
            <p className="text-sm text-gray-500">No schedules for this team yet.</p>
          )}
          {schedules.map((schedule) => (
            <OnCallCard key={schedule.id} scheduleId={schedule.id} scheduleName={schedule.name} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Open incidents</h2>
        {openIncidents.length === 0 ? (
          <p className="text-sm text-gray-500">No open incidents. All clear.</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-200">
                {openIncidents.map((incident) => (
                  <tr key={incident.id}>
                    <td className="px-4 py-3">
                      <Link
                        to={`/incidents/${incident.id}`}
                        className="font-medium text-indigo-600 hover:underline"
                      >
                        {incident.title}
                      </Link>
                      <div className="text-xs text-gray-500">{incident.service_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={incident.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      {incident.status === 'triggered' && (
                        <button
                          onClick={() => handleAcknowledge(incident.id)}
                          className="rounded bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-200"
                        >
                          Acknowledge
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function OnCallCard({ scheduleId, scheduleName }: { scheduleId: number; scheduleName: string }) {
  const { data } = useQuery({
    queryKey: ['on-call', scheduleId],
    queryFn: () => getOnCall(scheduleId),
    refetchInterval: POLL_INTERVAL_MS,
  })

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-sm text-gray-500">{scheduleName}</div>
      <div className="mt-1 text-base font-medium">{data?.user?.email ?? '—'}</div>
    </div>
  )
}
