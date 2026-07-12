import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTeam } from '../context/TeamContext'
import { listEscalationPolicies } from '../api/escalationPolicies'
import { listServices, createService, regenerateKey, updateService } from '../api/services'
import type { Service } from '../api/types'

export function Services() {
  const { selectedTeamId } = useTeam()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data: services = [] } = useQuery({
    queryKey: ['services', selectedTeamId],
    queryFn: () => listServices(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const { data: policies = [] } = useQuery({
    queryKey: ['escalation-policies', selectedTeamId],
    queryFn: () => listEscalationPolicies(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const createMutation = useMutation({
    mutationFn: createService,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] })
      setShowForm(false)
    },
  })

  const regenerateMutation = useMutation({
    mutationFn: regenerateKey,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['services'] }),
  })

  const runbookMutation = useMutation({
    mutationFn: ({ id, runbook_url, runbook_markdown }: { id: number; runbook_url: string; runbook_markdown: string }) =>
      updateService(id, { runbook_url, runbook_markdown }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['services'] }),
  })

  if (selectedTeamId === null) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Services</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          {showForm ? 'Cancel' : 'New service'}
        </button>
      </div>

      {showForm && (
        <NewServiceForm
          teamId={selectedTeamId}
          policies={policies}
          onSubmit={(input) => createMutation.mutate(input)}
          submitting={createMutation.isPending}
        />
      )}

      <div className="space-y-4">
        {services.map((service) => (
          <ServiceCard
            key={service.id}
            service={service}
            onRegenerateKey={() => regenerateMutation.mutate(service.id)}
            onSaveRunbook={(runbook_url, runbook_markdown) =>
              runbookMutation.mutate({ id: service.id, runbook_url, runbook_markdown })
            }
          />
        ))}
        {services.length === 0 && (
          <p className="text-sm text-gray-500">No services yet for this team.</p>
        )}
      </div>
    </div>
  )
}

function NewServiceForm({
  teamId,
  policies,
  onSubmit,
  submitting,
}: {
  teamId: number
  policies: { id: number; name: string }[]
  onSubmit: (input: { team: number; name: string; escalation_policy: number }) => void
  submitting: boolean
}) {
  const [name, setName] = useState('')
  const [policyId, setPolicyId] = useState(0)

  return (
    <div className="flex items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
      </label>
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Escalation policy</span>
        <select
          value={policyId}
          onChange={(e) => setPolicyId(Number(e.target.value))}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        >
          <option value={0}>Select policy…</option>
          {policies.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <button
        onClick={() => onSubmit({ team: teamId, name, escalation_policy: policyId })}
        disabled={submitting || !name || !policyId}
        className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting ? 'Creating…' : 'Create service'}
      </button>
    </div>
  )
}

function ServiceCard({
  service,
  onRegenerateKey,
  onSaveRunbook,
}: {
  service: Service
  onRegenerateKey: () => void
  onSaveRunbook: (url: string, markdown: string) => void
}) {
  const [runbookUrl, setRunbookUrl] = useState(service.runbook_url ?? '')
  const [runbookMarkdown, setRunbookMarkdown] = useState(service.runbook_markdown ?? '')
  const [copied, setCopied] = useState<string | null>(null)

  function copy(text: string, label: string) {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{service.name}</h3>
        <button
          onClick={onRegenerateKey}
          className="text-xs font-medium text-red-600 hover:underline"
        >
          Regenerate key
        </button>
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs">
        <span className="text-gray-500">Integration key:</span>
        <code className="rounded bg-gray-100 px-1.5 py-0.5">{service.integration_key}</code>
        <button
          onClick={() => copy(service.integration_key, 'key')}
          className="text-indigo-600 hover:underline"
        >
          {copied === 'key' ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <div className="mt-3 space-y-1">
        <p className="text-xs font-medium text-gray-700">Webhook URLs</p>
        {Object.entries(service.webhook_urls).map(([source, url]) => (
          <div key={source} className="flex items-center gap-2 text-xs">
            <span className="w-24 capitalize text-gray-500">{source}</span>
            <code className="flex-1 truncate rounded bg-gray-100 px-1.5 py-0.5">{url}</code>
            <button onClick={() => copy(url, source)} className="text-indigo-600 hover:underline">
              {copied === source ? 'Copied!' : 'Copy'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-gray-100 pt-3">
        <p className="mb-1 text-xs font-medium text-gray-700">Runbook</p>
        <input
          placeholder="Runbook URL"
          value={runbookUrl}
          onChange={(e) => setRunbookUrl(e.target.value)}
          className="mb-2 w-full rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <textarea
          placeholder="Runbook markdown"
          value={runbookMarkdown}
          onChange={(e) => setRunbookMarkdown(e.target.value)}
          rows={3}
          className="mb-2 w-full rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <button
          onClick={() => onSaveRunbook(runbookUrl, runbookMarkdown)}
          className="rounded bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
        >
          Save runbook
        </button>
      </div>
    </div>
  )
}
