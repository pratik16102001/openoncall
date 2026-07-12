import { apiClient } from './client'
import type { Incident, IncidentDetail, IncidentStatus, Paginated } from './types'

export interface ListIncidentsFilters {
  status?: IncidentStatus
  service?: number
  team?: number
}

export async function listIncidents(filters: ListIncidentsFilters = {}): Promise<Incident[]> {
  const { data } = await apiClient.get<Paginated<Incident>>('/incidents/', { params: filters })
  return data.results
}

export async function getIncident(id: number): Promise<IncidentDetail> {
  const { data } = await apiClient.get<IncidentDetail>(`/incidents/${id}/`)
  return data
}

export async function acknowledgeIncident(id: number): Promise<IncidentDetail> {
  const { data } = await apiClient.post<IncidentDetail>(`/incidents/${id}/acknowledge/`)
  return data
}

export async function resolveIncident(id: number): Promise<IncidentDetail> {
  const { data } = await apiClient.post<IncidentDetail>(`/incidents/${id}/resolve/`)
  return data
}

export async function addNote(id: number, message: string): Promise<void> {
  await apiClient.post(`/incidents/${id}/notes/`, { message })
}

export async function getPostmortem(id: number): Promise<string> {
  const { data } = await apiClient.get<{ markdown: string }>(`/incidents/${id}/postmortem/`)
  return data.markdown
}
