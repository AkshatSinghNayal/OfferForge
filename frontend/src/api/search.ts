import { apiGet } from './client'

export interface SearchCompanyHit {
  id: string
  name: string
  cluster: string
}

export interface SearchDsaHit {
  id: string
  title: string
  difficulty: string
  status: string
}

export interface SearchNoteHit {
  id: string
  title: string
  type: string
}

export interface SearchResourceHit {
  id: string
  title: string
  url: string
  category: string
}

export interface SearchResponse {
  companies: SearchCompanyHit[]
  dsa_problems: SearchDsaHit[]
  notes: SearchNoteHit[]
  resources: SearchResourceHit[]
  total: number
  q: string
  limit: number
}

export const searchApi = {
  search: (q: string, limit = 10) =>
    apiGet<SearchResponse>(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
}
