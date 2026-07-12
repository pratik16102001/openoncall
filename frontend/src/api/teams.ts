import { apiClient } from './client'
import type { Paginated, Team, TeamMembership } from './types'

export async function listTeams(): Promise<Team[]> {
  const { data } = await apiClient.get<Paginated<Team>>('/teams/')
  return data.results
}

export async function listMembers(teamId: number): Promise<TeamMembership[]> {
  const { data } = await apiClient.get<TeamMembership[]>(`/teams/${teamId}/members/`)
  return data
}

export async function createTeam(name: string, slug: string): Promise<Team> {
  const { data } = await apiClient.post<Team>('/teams/', { name, slug })
  return data
}
