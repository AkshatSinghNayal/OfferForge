import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export const STAGES = [
  'Saved',
  'Applied',
  'Assessment',
  'Interview',
  'Offer',
  'Closed',
] as const
export type Stage = (typeof STAGES)[number]
export interface Application {
  id: string
  company_name: string
  role: string
  stage: Stage
  deadline: string | null
  next_action: string
  notes: string
  is_pinned: boolean
  resume_id: string | null
  history: { stage: Stage; at: string }[]
  created_at: string
  updated_at: string
}
export type ApplicationInput = Omit<
  Application,
  'id' | 'history' | 'created_at' | 'updated_at'
>
export interface PreparationTask {
  id: string
  title: string
  details: string
  due_date: string | null
  minutes: number
  is_done: boolean
  source_analysis_id: string | null
  source_index: number | null
  source_label: string | null
  created_at: string
}
export const workspaceApi = {
  applications: () => apiGet<Application[]>('/workspace/applications'),
  createApplication: (body: ApplicationInput) =>
    apiPost<Application>('/workspace/applications', body),
  updateApplication: (id: string, body: Partial<ApplicationInput>) =>
    apiPatch<Application>(`/workspace/applications/${id}`, body),
  deleteApplication: (id: string) =>
    apiDelete<void>(`/workspace/applications/${id}`),
  tasks: () => apiGet<PreparationTask[]>('/workspace/tasks'),
  createTask: (body: {
    title: string
    details?: string
    due_date?: string | null
    minutes?: number
  }) => apiPost<PreparationTask>('/workspace/tasks', body),
  completeTask: (id: string, is_done: boolean) =>
    apiPatch<PreparationTask>(`/workspace/tasks/${id}`, { is_done }),
  deleteTask: (id: string) => apiDelete<void>(`/workspace/tasks/${id}`),
  analysisTask: (id: string, requirement_index: number) =>
    apiPost<PreparationTask>(`/workspace/analyses/${id}/tasks`, {
      requirement_index,
    }),
}
