import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export type NoteType = 'Interview Note' | 'Revision Schedule' | 'Concept' | 'HR Answer' | 'Personal'

export interface NotePublic {
  id: string
  user_id: string
  title: string
  content: string
  type: NoteType
  company_id: string | null
  dsa_problem_id: string | null
  created_at: string
  updated_at: string
}

export interface NoteList {
  items: NotePublic[]
  total: number
  limit: number
  offset: number
}

export interface NoteCreate {
  title: string
  content: string
  type: NoteType
  company_id?: string | null
  dsa_problem_id?: string | null
}

export const notesApi = {
  list: (params?: { type?: string; company_id?: string; dsa_problem_id?: string; q?: string; limit?: number; offset?: number }) =>
    apiGet<NoteList>('/notes', { params }),

  get: (id: string) =>
    apiGet<NotePublic>(`/notes/${id}`),

  create: (body: NoteCreate) =>
    apiPost<NotePublic>('/notes', body),

  update: (id: string, body: Partial<NoteCreate>) =>
    apiPatch<NotePublic>(`/notes/${id}`, body),

  delete: (id: string) =>
    apiDelete<void>(`/notes/${id}`),
}
