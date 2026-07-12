import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listTeams } from '../api/teams'
import type { Team } from '../api/types'

const STORAGE_KEY = 'openoncall_selected_team'

interface TeamContextValue {
  teams: Team[]
  selectedTeamId: number | null
  selectTeam: (id: number) => void
  isLoading: boolean
}

const TeamContext = createContext<TeamContextValue | null>(null)

export function TeamProvider({ children }: { children: ReactNode }) {
  const { data: teams = [], isLoading } = useQuery({ queryKey: ['teams'], queryFn: listTeams })
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? Number(stored) : null
  })

  useEffect(() => {
    if (selectedTeamId === null && teams.length > 0) {
      setSelectedTeamId(teams[0].id)
    }
  }, [teams, selectedTeamId])

  const selectTeam = (id: number) => {
    localStorage.setItem(STORAGE_KEY, String(id))
    setSelectedTeamId(id)
  }

  return (
    <TeamContext.Provider value={{ teams, selectedTeamId, selectTeam, isLoading }}>
      {children}
    </TeamContext.Provider>
  )
}

export function useTeam(): TeamContextValue {
  const ctx = useContext(TeamContext)
  if (!ctx) throw new Error('useTeam must be used within a TeamProvider')
  return ctx
}
