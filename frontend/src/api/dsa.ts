import { apiGet, apiPost, apiPatch, apiDelete } from './client'

export type Platform = 'LeetCode' | 'GFG' | 'Codeforces'
export type Difficulty = 'Easy' | 'Medium' | 'Hard'
export type DSAStatus = 'Not Started' | 'In Progress' | 'Solved' | 'Skipped' | 'Marked for Revision'
export type RevisionStatus = 'None' | 'Due' | 'Done'

export interface TagPublic {
  id: string
  name: string
  problem_count: number
}

export interface ProblemPublic {
  id: string
  user_id: string
  title: string
  platform: Platform
  external_url: string
  difficulty: Difficulty
  status: DSAStatus
  revision_status: RevisionStatus
  completed_at: string | null
  notes: string | null
  tags: TagPublic[]
  created_at: string
  updated_at: string
}

export interface ProblemList {
  items: ProblemPublic[]
  total: number
  limit: number
  offset: number
}

export interface ProblemCreate {
  title: string
  platform: Platform
  external_url: string
  difficulty: Difficulty
  status?: DSAStatus
  revision_status?: RevisionStatus
  tag_names?: string[]
  notes?: string | null
}

export interface ProblemUpdate {
  title?: string
  platform?: Platform
  external_url?: string
  difficulty?: Difficulty
  status?: DSAStatus
  revision_status?: RevisionStatus
  tag_names?: string[]
  notes?: string | null
}

export interface TopicStat {
  tag: string
  total: number
  solved: number
  pct: number
}

export interface DifficultyStat {
  difficulty: Difficulty
  total: number
  solved: number
  pct: number
}

export interface DsaStats {
  topic_wise: TopicStat[]
  difficulty_wise: DifficultyStat[]
  overall_total: number
  overall_solved: number
  overall_pct: number
}

export const dsaApi = {
  listProblems: (params?: {
    topic?: string
    difficulty?: string
    status?: string
    platform?: string
    q?: string
    limit?: number
    offset?: number
  }) => apiGet<ProblemList>('/dsa/problems', { params }),

  createProblem: (body: ProblemCreate) =>
    apiPost<ProblemPublic>('/dsa/problems', body),

  updateProblem: (id: string, body: ProblemUpdate) =>
    apiPatch<ProblemPublic>(`/dsa/problems/${id}`, body),

  deleteProblem: (id: string) =>
    apiDelete<void>(`/dsa/problems/${id}`),

  getStats: () =>
    apiGet<DsaStats>('/dsa/stats'),

  listTags: () =>
    apiGet<TagPublic[]>('/dsa/tags'),
}
