import { apiClient } from './client'
import type { EscalationPolicy, EscalationStep, Paginated } from './types'

export async function listEscalationPolicies(teamId?: number): Promise<EscalationPolicy[]> {
  const { data } = await apiClient.get<Paginated<EscalationPolicy>>('/escalation-policies/', {
    params: teamId ? { team: teamId } : undefined,
  })
  return data.results
}

export interface CreateEscalationPolicyInput {
  team: number
  name: string
  repeat_count: number
  steps: EscalationStep[]
}

export async function createEscalationPolicy(
  input: CreateEscalationPolicyInput,
): Promise<EscalationPolicy> {
  const { data } = await apiClient.post<EscalationPolicy>('/escalation-policies/', input)
  return data
}

export async function updateEscalationPolicy(
  id: number,
  input: Partial<CreateEscalationPolicyInput>,
): Promise<EscalationPolicy> {
  const { data } = await apiClient.patch<EscalationPolicy>(`/escalation-policies/${id}/`, input)
  return data
}

export async function deleteEscalationPolicy(id: number): Promise<void> {
  await apiClient.delete(`/escalation-policies/${id}/`)
}
