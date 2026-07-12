import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTeam } from '../context/TeamContext'
import { listMembers } from '../api/teams'
import {
  listSchedules,
  createSchedule,
  createOverride,
  type CreateScheduleInput,
} from '../api/schedules'
import type { Schedule } from '../api/types'

export function Schedules() {
  const { selectedTeamId } = useTeam()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules', selectedTeamId],
    queryFn: () => listSchedules(selectedTeamId ?? undefined),
    enabled: selectedTeamId !== null,
  })

  const { data: members = [] } = useQuery({
    queryKey: ['members', selectedTeamId],
    queryFn: () => listMembers(selectedTeamId!),
    enabled: selectedTeamId !== null,
  })

  const createMutation = useMutation({
    mutationFn: createSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      setShowForm(false)
    },
  })

  if (selectedTeamId === null) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Schedules</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          {showForm ? 'Cancel' : 'New schedule'}
        </button>
      </div>

      {showForm && (
        <ScheduleForm
          teamId={selectedTeamId}
          members={members}
          onSubmit={(input) => createMutation.mutate(input)}
          submitting={createMutation.isPending}
          error={createMutation.isError ? 'Could not create schedule.' : null}
        />
      )}

      <div className="space-y-4">
        {schedules.map((schedule) => (
          <ScheduleCard key={schedule.id} schedule={schedule} members={members} />
        ))}
        {schedules.length === 0 && (
          <p className="text-sm text-gray-500">No schedules yet for this team.</p>
        )}
      </div>
    </div>
  )
}

function ScheduleForm({
  teamId,
  members,
  onSubmit,
  submitting,
  error,
}: {
  teamId: number
  members: { user: number; user_email: string }[]
  onSubmit: (input: CreateScheduleInput) => void
  submitting: boolean
  error: string | null
}) {
  const [name, setName] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  const [rotationType, setRotationType] = useState<Schedule['rotation_type']>('weekly')
  const [rotationStart, setRotationStart] = useState('')
  const [rotationLengthHours, setRotationLengthHours] = useState(168)
  const [participantIds, setParticipantIds] = useState<number[]>([])

  function toggleParticipant(userId: number) {
    setParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId],
    )
  }

  function handleSubmit() {
    onSubmit({
      team: teamId,
      name,
      timezone,
      rotation_type: rotationType,
      rotation_start: new Date(rotationStart).toISOString(),
      rotation_length_hours: rotationLengthHours,
      participants: participantIds.map((user, order) => ({ user, order })),
    })
  }

  return (
    <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Name">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </Field>
        <Field label="Timezone (IANA)">
          <input
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            placeholder="America/New_York"
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </Field>
        <Field label="Rotation type">
          <select
            value={rotationType}
            onChange={(e) => setRotationType(e.target.value as Schedule['rotation_type'])}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="custom">Custom</option>
          </select>
        </Field>
        <Field label="Rotation length (hours)">
          <input
            type="number"
            value={rotationLengthHours}
            onChange={(e) => setRotationLengthHours(Number(e.target.value))}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </Field>
        <Field label="Rotation start">
          <input
            type="datetime-local"
            value={rotationStart}
            onChange={(e) => setRotationStart(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </Field>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-gray-700">
          Participants (click in rotation order)
        </p>
        <div className="flex flex-wrap gap-2">
          {members.map((m) => {
            const order = participantIds.indexOf(m.user)
            return (
              <button
                key={m.user}
                onClick={() => toggleParticipant(m.user)}
                className={`rounded border px-2 py-1 text-xs ${
                  order >= 0
                    ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                    : 'border-gray-300 text-gray-600'
                }`}
              >
                {order >= 0 ? `${order + 1}. ` : ''}
                {m.user_email}
              </button>
            )
          })}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={submitting || !name || participantIds.length === 0}
        className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting ? 'Creating…' : 'Create schedule'}
      </button>
    </div>
  )
}

function ScheduleCard({
  schedule,
  members,
}: {
  schedule: Schedule
  members: { user: number; user_email: string }[]
}) {
  const queryClient = useQueryClient()
  const [showOverrideForm, setShowOverrideForm] = useState(false)
  const [overrideUser, setOverrideUser] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [reason, setReason] = useState('')

  const overrideMutation = useMutation({
    mutationFn: () =>
      createOverride(schedule.id, {
        user: Number(overrideUser),
        start_time: new Date(start).toISOString(),
        end_time: new Date(end).toISOString(),
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      setShowOverrideForm(false)
    },
  })

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium">{schedule.name}</h3>
          <p className="text-xs text-gray-500">
            {schedule.rotation_type} · every {schedule.rotation_length_hours}h · {schedule.timezone}
          </p>
        </div>
        <button
          onClick={() => setShowOverrideForm((s) => !s)}
          className="text-sm font-medium text-indigo-600 hover:underline"
        >
          {showOverrideForm ? 'Cancel' : 'Add override'}
        </button>
      </div>

      <ol className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
        {schedule.participants
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((p) => (
            <li key={p.id} className="rounded bg-gray-100 px-2 py-0.5">
              {p.order + 1}. {members.find((m) => m.user === p.user)?.user_email ?? `user #${p.user}`}
            </li>
          ))}
      </ol>

      {showOverrideForm && (
        <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
          <input
            placeholder="User ID"
            value={overrideUser}
            onChange={(e) => setOverrideUser(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
            <input
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </div>
          <input
            placeholder="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
          <button
            onClick={() => overrideMutation.mutate()}
            disabled={overrideMutation.isPending || !overrideUser || !start || !end}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Save override
          </button>
        </div>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      {children}
    </label>
  )
}
