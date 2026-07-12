import { apiClient } from './client'

export async function login(email: string, password: string): Promise<string> {
  const { data } = await apiClient.post<{ token: string }>('/auth/login/', { email, password })
  return data.token
}
