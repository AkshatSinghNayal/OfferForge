import { apiGet } from './client'

export interface DashboardSummary {
  overall_progress: number
  dsa_completion_pct: number
  resume_readiness_score: number
  checklist_completion_pct: number
  active_companies_count: number
  upcoming_deadlines: {
    user_company_id: string
    company_id: string
    company_name: string
    deadline: string
    application_status: string
  }[]
  recent_activity: {
    id: string
    action: string
    entity_type: string
    entity_id: string | null
    metadata: Record<string, unknown> | null
    created_at: string
  }[]
  charts: {
    dsa_solved_over_time: { date: string; count: number }[]
    topic_distribution: { tag: string; solved: number; total: number }[]
    company_readiness: { user_company_id: string; company_id: string; company_name: string; checklist_progress_pct: number }[]
  }
}

export interface StreakResponse {
  current_streak: number
  longest_streak: number
  last_active_date: string | null
  today_active: boolean
}

export interface WeeklyProductivityPoint {
  iso_week: string
  activity_count: number
}

export interface WeeklyProductivityResponse {
  weeks: WeeklyProductivityPoint[]
  total_activities: number
}

export interface TimelineEntry {
  timestamp: string
  event_type: 'dsa_solved' | 'checklist_item_completed' | 'company_status_changed'
  action: string
  entity_type: string
  entity_id: string | null
  metadata: Record<string, unknown> | null
}

export interface TimelineResponse {
  entries: TimelineEntry[]
  total: number
  limit: number
  offset: number
}

export const dashboardApi = {
  getSummary: () => apiGet<DashboardSummary>('/dashboard/summary'),
  getStreak: () => apiGet<StreakResponse>('/dashboard/streak'),
  getWeeklyProductivity: (weeks = 12) =>
    apiGet<WeeklyProductivityResponse>(`/dashboard/weekly-productivity?weeks=${weeks}`),
  getTimeline: (limit = 50, offset = 0) =>
    apiGet<TimelineResponse>(`/dashboard/timeline?limit=${limit}&offset=${offset}`),
}
