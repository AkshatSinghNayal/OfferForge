import { apiGet, apiPost, apiPatch, apiDelete } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type Cluster = 'FAANG' | 'Product-based' | 'Service-based' | 'FinTech' | 'Startups'
export type ApplicationStatus =
  | 'Not Started'
  | 'Researching'
  | 'Applied'
  | 'OA Received'
  | 'Interview Scheduled'
  | 'Offer Received'
  | 'Rejected'

export interface CompanyPublic {
  id: string
  name: string
  cluster: Cluster
  hiring_process: string | null
  oa_pattern: string | null
  frequent_dsa_topics: string[]
  core_cs_subjects: string[]
  resume_requirements: string | null
  interview_experiences: unknown[]
  is_custom: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface UserState {
  user_company_id: string
  application_status: ApplicationStatus
  deadline: string | null
  checklist_progress_pct: number
  mapped_resume_ids: string[]
}

export interface CompanyDetail extends CompanyPublic {
  user_state: UserState | null
}

export interface CompanyList {
  items: CompanyPublic[]
  total: number
  limit: number
  offset: number
}

export interface TrackedCompany {
  id: string // user_company.id
  company_id: string
  company_name: string
  cluster: Cluster
  application_status: ApplicationStatus
  deadline: string | null
  notes_summary: string | null
  checklist_progress_pct: number
  created_at: string
  updated_at: string
}

export interface TrackedCompanyList {
  items: TrackedCompany[]
  total: number
  limit: number
  offset: number
}

export interface ChecklistItem {
  id: string
  user_company_id: string
  item_key: string
  label: string
  is_done: boolean
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface ChecklistResponse {
  items: ChecklistItem[]
  progress_pct: number
}

export interface TrackResponse {
  user_company_id: string
  company_id: string
  application_status: ApplicationStatus
  deadline: string | null
  checklist_items: ChecklistItem[]
  checklist_progress_pct: number
}

export interface CompanyCreate {
  name: string
  cluster: Cluster
  hiring_process?: string | null
  oa_pattern?: string | null
  frequent_dsa_topics?: string[]
  core_cs_subjects?: string[]
  resume_requirements?: string | null
}

// ─── API calls ───────────────────────────────────────────────────────────────

export const companiesApi = {
  list: (params?: { cluster?: string; q?: string; limit?: number; offset?: number }) =>
    apiGet<CompanyList>('/companies', { params }),

  get: (id: string) =>
    apiGet<CompanyDetail>(`/companies/${id}`),

  create: (body: CompanyCreate) =>
    apiPost<CompanyPublic>('/companies', body),

  listTracked: (params?: { cluster?: string; application_status?: string; limit?: number; offset?: number }) =>
    apiGet<TrackedCompanyList>('/companies/tracked/list', { params }),

  track: (companyId: string, body: { application_status?: ApplicationStatus; deadline?: string | null }) =>
    apiPost<TrackResponse>(`/companies/${companyId}/track`, body),

  updateTracking: (companyId: string, body: { application_status?: ApplicationStatus; deadline?: string | null; notes_summary?: string }) =>
    apiPatch<TrackedCompany>(`/companies/${companyId}/track`, body),

  untrack: (companyId: string) =>
    apiDelete<void>(`/companies/${companyId}/track`),
}

export const checklistApi = {
  list: (userCompanyId: string) =>
    apiGet<ChecklistResponse>(`/checklist/${userCompanyId}`),

  toggle: (userCompanyId: string, itemId: string, is_done: boolean) =>
    apiPatch<ChecklistResponse>(`/checklist/${userCompanyId}/${itemId}`, { is_done }),
}
