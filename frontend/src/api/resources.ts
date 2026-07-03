import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export type ResourceCategory =
  | 'Career Portal'
  | 'Referral'
  | 'Coding Sheet'
  | 'Interview Prep'
  | 'YouTube'
  | 'Notes'
  | 'Article'

export interface ResourcePublic {
  id: string
  user_id: string
  company_id: string | null
  title: string
  url: string
  category: ResourceCategory
  description: string | null
  created_at: string
  updated_at: string
}

export interface ResourceList {
  items: ResourcePublic[]
  total: number
  limit: number
  offset: number
}

export interface ResourceCreate {
  title: string
  url: string
  category: ResourceCategory
  company_id?: string | null
  description?: string | null
}

export const resourcesApi = {
  list: (params?: { category?: string; company_id?: string; q?: string; limit?: number; offset?: number }) =>
    apiGet<ResourceList>('/resources', { params }),

  create: (body: ResourceCreate) =>
    apiPost<ResourcePublic>('/resources', body),

  update: (id: string, body: Partial<ResourceCreate>) =>
    apiPatch<ResourcePublic>(`/resources/${id}`, body),

  delete: (id: string) =>
    apiDelete<void>(`/resources/${id}`),
}
