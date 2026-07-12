import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  getIncident,
  acknowledgeIncident,
  resolveIncident,
  addNote,
  getPostmortem,
} from '../api/incidents'
import { StatusBadge } from '../components/StatusBadge'

const EVENT_LABELS: Record<string, string> = {
  alert_received: 'Alert received',
  notification_sent: 'Notification sent',
  escalated: 'Escalated',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
  note_added: 'Note',
}

export function IncidentDetail() {
  const { id } = useParams<{ id: string }>()
  const incidentId = Number(id)
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [postmortem, setPostmortem] = useState<string | null>(null)

  const { data: incident, isLoading } = useQuery({
    queryKey: ['incident', incidentId],
    queryFn: () => getIncident(incidentId),
    refetchInterval: 15_000,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['incident', incidentId] })

  const acknowledgeMutation = useMutation({ mutationFn: () => acknowledgeIncident(incidentId), onSuccess: invalidate })
  const resolveMutation = useMutation({ mutationFn: () => resolveIncident(incidentId), onSuccess: invalidate })
  const noteMutation = useMutation({
    mutationFn: () => addNote(incidentId, note),
    onSuccess: () => {
      setNote('')
      invalidate()
    },
  })

  async function handleExportPostmortem() {
    const markdown = await getPostmortem(incidentId)
    setPostmortem(markdown)

    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `postmortem-incident-${incidentId}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading || !incident) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">{incident.title}</h1>
          <StatusBadge status={incident.status} />
        </div>
        <p className="text-sm text-gray-500">{incident.service_name}</p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => acknowledgeMutation.mutate()}
          disabled={incident.status !== 'triggered' || acknowledgeMutation.isPending}
          className="rounded bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200 disabled:opacity-40"
        >
          Acknowledge
        </button>
        <button
          onClick={() => resolveMutation.mutate()}
          disabled={incident.status === 'resolved' || resolveMutation.isPending}
          className="rounded bg-green-100 px-3 py-1.5 text-sm font-medium text-green-800 hover:bg-green-200 disabled:opacity-40"
        >
          Resolve
        </button>
        <button
          onClick={handleExportPostmortem}
          className="rounded bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
        >
          Export postmortem
        </button>
      </div>

      {(incident.runbook_url || incident.runbook_markdown) && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-1 text-sm font-semibold">Runbook</h2>
          {incident.runbook_url && (
            <a
              href={incident.runbook_url}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-indigo-600 hover:underline"
            >
              {incident.runbook_url}
            </a>
          )}
          {incident.runbook_markdown && (
            <pre className="mt-2 whitespace-pre-wrap text-sm text-gray-700">
              {incident.runbook_markdown}
            </pre>
          )}
        </div>
      )}

      <div>
        <h2 className="mb-2 text-sm font-semibold">Timeline</h2>
        <ol className="space-y-2 border-l border-gray-200 pl-4">
          {incident.timeline.map((event) => (
            <li key={event.id} className="text-sm">
              <div className="text-xs text-gray-400">
                {new Date(event.created_at).toLocaleString()}
              </div>
              <div>
                <span className="font-medium">{EVENT_LABELS[event.event_type] ?? event.event_type}</span>
                {event.actor_email && <span className="text-gray-500"> — {event.actor_email}</span>}
              </div>
              {event.message && <p className="text-gray-600">{event.message}</p>}
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold">Add a note</h2>
        <div className="flex gap-2">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
            placeholder="What are you seeing / doing?"
          />
          <button
            onClick={() => noteMutation.mutate()}
            disabled={!note || noteMutation.isPending}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Add note
          </button>
        </div>
      </div>

      {postmortem && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Postmortem preview</h2>
          <pre className="whitespace-pre-wrap text-xs text-gray-700">{postmortem}</pre>
        </div>
      )}
    </div>
  )
}
