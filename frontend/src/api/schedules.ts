import { apiClient } from './client'
import type { Paginated, Schedule, ScheduleOverride, User } from './types'

export async function listSchedules(teamId?: number): Promise<Schedule[]> {
  const { data } = await apiClient.get<Paginated<Schedule>>('/schedules/', {
    params: teamId ? { team: teamId } : undefined,
  })
  return data.results
}

export async function getSchedule(id: number): Promise<Schedule> {
  const { data } = await apiClient.get<Schedule>(`/schedules/${id}/`)
  return data
}

export interface CreateScheduleInput {
  team: number
  name: string
  timezone: string
  rotation_type: Schedule['rotation_type']
  rotation_start: string
  rotation_length_hours: number
  participants: { user: number; order: number }[]
}

export async function createSchedule(input: CreateScheduleInput): Promise<Schedule> {
  const { data } = await apiClient.post<Schedule>('/schedules/', input)
  return data
}

export async function updateSchedule(
  id: number,
  input: Partial<CreateScheduleInput>,
): Promise<Schedule> {
  const { data } = await apiClient.patch<Schedule>(`/schedules/${id}/`, input)
  return data
}

export async function deleteSchedule(id: number): Promise<void> {
  await apiClient.delete(`/schedules/${id}/`)
}

export async function getOnCall(
  scheduleId: number,
  at?: string,
): Promise<{ user: User | null }> {
  const { data } = await apiClient.get<{ user: User | null }>(
    `/schedules/${scheduleId}/on-call/`,
    { params: at ? { at } : undefined },
  )
  return data
}

export async function createOverride(
  scheduleId: number,
  input: { user: number; start_time: string; end_time: string; reason?: string },
): Promise<ScheduleOverride> {
  const { data } = await apiClient.post<ScheduleOverride>(
    `/schedules/${scheduleId}/overrides/`,
    input,
  )
  return data
}
