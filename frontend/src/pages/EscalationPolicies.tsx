import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTeam } from '../context/TeamContext'
import { listMembers } from '../api/teams'
import { listSchedules } from '../api/schedules'
import {
  listEscalationPolicies,
  createEscalationPolicy,
} from '../api/escalationPolicies'
import type { EscalationStep, EscalationTargetType, NotifyChannel } from '../api/types'

const CHANNELS: NotifyChannel[] = ['slack', 'sms', 'voice', 'push']

export function EscalationPolicies() {
  const { selectedTeamId } = useTeam()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data: policies = [] } = useQuery({
    queryKey: ['escalation-policies', selectedTeamId],
    queryFn: () => listEscalationPolicies(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const createMutation = useMutation({
    mutationFn: createEscalationPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escalation-policies'] })
      setShowForm(false)
    },
  })

  if (selectedTeamId === null) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Escalation Policies</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          {showForm ? 'Cancel' : 'New policy'}
        </button>
      </div>

      {showForm && (
        <PolicyForm
          teamId={selectedTeamId}
          onSubmit={(input) => createMutation.mutate(input)}
          submitting={createMutation.isPending}
        />
      )}

      <div className="space-y-4">
        {policies.map((policy) => (
          <div key={policy.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{policy.name}</h3>
              <span className="text-xs text-gray-500">repeats {policy.repeat_count}x</span>
            </div>
            <ol className="mt-2 space-y-1">
              {policy.steps
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((step) => (
                  <li key={step.order} className="text-sm text-gray-600">
                    Step {step.order + 1}: notify {step.target_type} #{step.target_id} via{' '}
                    {step.notify_channels.join(', ')} — wait {step.timeout_minutes}m
                  </li>
                ))}
            </ol>
          </div>
        ))}
        {policies.length === 0 && (
          <p className="text-sm text-gray-500">No escalation policies yet for this team.</p>
        )}
      </div>
    </div>
  )
}

function PolicyForm({
  teamId,
  onSubmit,
  submitting,
}: {
  teamId: number
  onSubmit: (input: { team: number; name: string; repeat_count: number; steps: EscalationStep[] }) => void
  submitting: boolean
}) {
  const { data: members = [] } = useQuery({
    queryKey: ['members', teamId],
    queryFn: () => listMembers(teamId),
  })
  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules', teamId],
    queryFn: () => listSchedules(teamId),
  })

  const [name, setName] = useState('')
  const [repeatCount, setRepeatCount] = useState(0)
  const [steps, setSteps] = useState<EscalationStep[]>([
    { order: 0, target_type: 'user', target_id: 0, timeout_minutes: 15, notify_channels: ['slack'] },
  ])

  function updateStep(index: number, patch: Partial<EscalationStep>) {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)))
  }

  function addStep() {
    setSteps((prev) => [
      ...prev,
      { order: prev.length, target_type: 'user', target_id: 0, timeout_minutes: 15, notify_channels: ['slack'] },
    ])
  }

  function toggleChannel(index: number, channel: NotifyChannel) {
    setSteps((prev) =>
      prev.map((s, i) => {
        if (i !== index) return s
        const has = s.notify_channels.includes(channel)
        return {
          ...s,
          notify_channels: has
            ? s.notify_channels.filter((c) => c !== channel)
            : [...s.notify_channels, channel],
        }
      }),
    )
  }

  return (
    <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid grid-cols-2 gap-3">
        <input
          placeholder="Policy name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
        <input
          type="number"
          min={0}
          value={repeatCount}
          onChange={(e) => setRepeatCount(Number(e.target.value))}
          placeholder="Repeat count"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        />
      </div>

      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="rounded border border-gray-200 p-3">
            <p className="mb-2 text-sm font-medium">Step {i + 1}</p>
            <div className="grid grid-cols-3 gap-2">
              <select
                value={step.target_type}
                onChange={(e) => updateStep(i, { target_type: e.target.value as EscalationTargetType })}
                className="rounded border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="user">User</option>
                <option value="schedule">Schedule</option>
                <option value="team">Team</option>
              </select>
              {step.target_type === 'user' && (
                <select
                  value={step.target_id}
                  onChange={(e) => updateStep(i, { target_id: Number(e.target.value) })}
                  className="rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  <option value={0}>Select user…</option>
                  {members.map((m) => (
                    <option key={m.user} value={m.user}>
                      {m.user_email}
                    </option>
                  ))}
                </select>
              )}
              {step.target_type === 'schedule' && (
                <select
                  value={step.target_id}
                  onChange={(e) => updateStep(i, { target_id: Number(e.target.value) })}
                  className="rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  <option value={0}>Select schedule…</option>
                  {schedules.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
              {step.target_type === 'team' && (
                <input value={teamId} disabled className="rounded border border-gray-300 px-2 py-1 text-sm" />
              )}
              <input
                type="number"
                min={1}
                value={step.timeout_minutes}
                onChange={(e) => updateStep(i, { timeout_minutes: Number(e.target.value) })}
                placeholder="Timeout (min)"
                className="rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
            <div className="mt-2 flex gap-2">
              {CHANNELS.map((channel) => (
                <button
                  key={channel}
                  onClick={() => toggleChannel(i, channel)}
                  className={`rounded border px-2 py-0.5 text-xs capitalize ${
                    step.notify_channels.includes(channel)
                      ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                      : 'border-gray-300 text-gray-600'
                  }`}
                >
                  {channel}
                </button>
              ))}
            </div>
          </div>
        ))}
        <button onClick={addStep} className="text-sm font-medium text-indigo-600 hover:underline">
          + Add step
        </button>
      </div>

      <button
        onClick={() =>
          onSubmit({
            team: teamId,
            name,
            repeat_count: repeatCount,
            steps: steps.map((s, order) => ({
              ...s,
              order,
              target_id: s.target_type === 'team' ? teamId : s.target_id,
            })),
          })
        }
        disabled={submitting || !name}
        className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting ? 'Creating…' : 'Create policy'}
      </button>
    </div>
  )
}
