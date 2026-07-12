import type { IncidentStatus } from '../api/types'

const STYLES: Record<IncidentStatus, string> = {
  triggered: 'bg-red-100 text-red-800 border-red-300',
  acknowledged: 'bg-amber-100 text-amber-800 border-amber-300',
  resolved: 'bg-green-100 text-green-800 border-green-300',
}

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span
      className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      {status}
    </span>
  )
}
