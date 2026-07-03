import { apiClient, apiGet, apiPost, apiPatch, apiDelete } from './client'

export interface ResumePublic {
  id: string
  user_id: string
  version_label: string
  cloudinary_url: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResumeWithScore extends ResumePublic {
  keyword_coverage_pct: number
  readiness_score: number
}

export interface ResumeList {
  items: ResumeWithScore[]
}

export interface KeywordPublic {
  id: string
  resume_id: string
  keyword: string
  is_present: boolean
  created_at: string
  updated_at: string
}

export interface ResumeCompanyMapPublic {
  id: string
  user_company_id: string
  resume_id: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ReadinessResponse {
  keyword_coverage_pct: number
  has_active_resume: boolean
  readiness_score: number
  formula: string
  keyword_total: number
  keyword_present: number
}

export const resumesApi = {
  list: () => apiGet<ResumeList>('/resumes'),

  upload: (file: File, versionLabel: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('version_label', versionLabel)
    return apiClient.post<ResumePublic>('/resumes/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  activate: (id: string) =>
    apiPost<ResumePublic>(`/resumes/${id}/activate`),

  delete: (id: string) =>
    apiDelete<void>(`/resumes/${id}`),

  listKeywords: (resumeId: string) =>
    apiGet<KeywordPublic[]>(`/resumes/${resumeId}/keywords`),

  addKeyword: (resumeId: string, keyword: string) =>
    apiPost<KeywordPublic>(`/resumes/${resumeId}/keywords`, { keyword }),

  updateKeyword: (resumeId: string, keywordId: string, is_present: boolean) =>
    apiPatch<KeywordPublic>(`/resumes/${resumeId}/keywords/${keywordId}`, { is_present }),

  deleteKeyword: (resumeId: string, keywordId: string) =>
    apiDelete<void>(`/resumes/${resumeId}/keywords/${keywordId}`),

  mapCompany: (resumeId: string, user_company_id: string, notes?: string) =>
    apiPost<ResumeCompanyMapPublic>(`/resumes/${resumeId}/map-company`, { user_company_id, notes }),

  getReadiness: (resumeId: string) =>
    apiGet<ReadinessResponse>(`/resumes/${resumeId}/readiness`),

  /** Fetch the PDF via authenticated request and return a blob URL for rendering. */
  fetchPdfBlobUrl: async (resumeId: string): Promise<string> => {
    const response = await apiClient.get(`/resumes/${resumeId}/pdf`, {
      responseType: 'blob',
    })
    const blob = new Blob([response.data], { type: 'application/pdf' })
    return URL.createObjectURL(blob)
  },
}
