import { apiClient } from './client'
import type { Paginated, Service } from './types'

export async function listServices(teamId?: number): Promise<Service[]> {
  const { data } = await apiClient.get<Paginated<Service>>('/services/', {
    params: teamId ? { team: teamId } : undefined,
  })
  return data.results
}

export interface CreateServiceInput {
  team: number
  name: string
  escalation_policy: number
  runbook_url?: string
  runbook_markdown?: string
}

export async function createService(input: CreateServiceInput): Promise<Service> {
  const { data } = await apiClient.post<Service>('/services/', input)
  return data
}

export async function updateService(
  id: number,
  input: Partial<CreateServiceInput>,
): Promise<Service> {
  const { data } = await apiClient.patch<Service>(`/services/${id}/`, input)
  return data
}

export async function regenerateKey(id: number): Promise<Service> {
  const { data } = await apiClient.post<Service>(`/services/${id}/regenerate-key/`)
  return data
}
