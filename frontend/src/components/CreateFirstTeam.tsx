import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTeam } from '../api/teams'

function slugify(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

export function CreateFirstTeam() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')

  const mutation = useMutation({
    mutationFn: () => createTeam(name, slugify(name)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['teams'] }),
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-2 text-lg font-semibold">Create your first team</h1>
        <p className="mb-4 text-sm text-gray-500">
          Everything in OpenOnCall (schedules, escalation policies, services) belongs to a team.
          You'll be its first admin.
        </p>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Team name, e.g. Platform"
          autoFocus
          className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        {mutation.isError && (
          <p className="mb-3 text-sm text-red-600">Could not create team. Try a different name.</p>
        )}
        <button
          onClick={() => mutation.mutate()}
          disabled={!name || mutation.isPending}
          className="w-full rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Creating…' : 'Create team'}
        </button>
      </div>
    </div>
  )
}
