export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Team {
  id: number
  name: string
  slug: string
  slack_webhook_url: string | null
  created_at: string
  updated_at: string
}

export interface TeamMembership {
  id: number
  team: number
  user: number
  user_email: string
  role: 'admin' | 'member'
  created_at: string
}

export interface User {
  id: number
  email: string
}

export interface ScheduleParticipant {
  id: number
  user: number
  order: number
}

export interface ScheduleOverride {
  id: number
  schedule: number
  user: number
  start_time: string
  end_time: string
  reason: string | null
}

export type RotationType = 'daily' | 'weekly' | 'custom'

export interface Schedule {
  id: number
  team: number
  name: string
  timezone: string
  rotation_type: RotationType
  rotation_start: string
  rotation_length_hours: number
  participants: ScheduleParticipant[]
  created_at: string
  updated_at: string
}

export type EscalationTargetType = 'schedule' | 'user' | 'team'
export type NotifyChannel = 'slack' | 'sms' | 'voice' | 'push'

export interface EscalationStep {
  id?: number
  order: number
  target_type: EscalationTargetType
  target_id: number
  timeout_minutes: number
  notify_channels: NotifyChannel[]
}

export interface EscalationPolicy {
  id: number
  team: number
  name: string
  repeat_count: number
  steps: EscalationStep[]
  created_at: string
  updated_at: string
}

export interface Service {
  id: number
  team: number
  name: string
  escalation_policy: number
  integration_key: string
  webhook_urls: Record<'alertmanager' | 'datadog' | 'cloudwatch' | 'sentry' | 'generic', string>
  runbook_url: string | null
  runbook_markdown: string | null
  created_at: string
  updated_at: string
}

export type IncidentStatus = 'triggered' | 'acknowledged' | 'resolved'

export interface Incident {
  id: number
  title: string
  status: IncidentStatus
  service: number
  service_name: string
  team: number
  triggering_alert: number
  current_escalation_step: number
  assigned_to: number | null
  acknowledged_at: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export type TimelineEventType =
  | 'alert_received'
  | 'notification_sent'
  | 'escalated'
  | 'acknowledged'
  | 'resolved'
  | 'note_added'

export interface TimelineEvent {
  id: number
  event_type: TimelineEventType
  actor: number | null
  actor_email: string | null
  message: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface IncidentDetail extends Incident {
  timeline: TimelineEvent[]
  runbook_url: string | null
  runbook_markdown: string | null
}
