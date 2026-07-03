import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import axios from 'axios'
import { ArrowLeft } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { companiesApi, checklistApi, type ApplicationStatus } from '@/api/companies'

const APPLICATION_STATUSES: ApplicationStatus[] = [
  'Not Started', 'Researching', 'Applied', 'OA Received',
  'Interview Scheduled', 'Offer Received', 'Rejected',
]

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: company, isLoading } = useQuery({
    queryKey: ['company', id],
    queryFn: () => companiesApi.get(id!),
    enabled: !!id,
  })

  const ucId = company?.user_state?.user_company_id

  const { data: checklist, isLoading: checklistLoading } = useQuery({
    queryKey: ['checklist', ucId],
    queryFn: () => checklistApi.list(ucId!),
    enabled: !!ucId,
  })

  const trackMutation = useMutation({
    mutationFn: () => companiesApi.track(id!, {}),
    onSuccess: () => {
      toast.success('Now tracking this company')
      qc.invalidateQueries({ queryKey: ['company', id] })
      qc.invalidateQueries({ queryKey: ['tracked-companies'] })
    },
    onError: (err) => {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        toast.error('Already tracking this company')
      } else {
        toast.error('Failed to track company')
      }
    },
  })

  const statusMutation = useMutation({
    mutationFn: (status: ApplicationStatus) =>
      companiesApi.updateTracking(id!, { application_status: status }),
    onSuccess: () => {
      toast.success('Status updated')
      qc.invalidateQueries({ queryKey: ['company', id] })
      qc.invalidateQueries({ queryKey: ['tracked-companies'] })
    },
    onError: () => toast.error('Failed to update status'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ itemId, is_done }: { itemId: string; is_done: boolean }) =>
      checklistApi.toggle(ucId!, itemId, is_done),
    onSuccess: (data) => {
      qc.setQueryData(['checklist', ucId], data)
      // Also invalidate the tracked-companies list so progress % updates
      qc.invalidateQueries({ queryKey: ['tracked-companies'] })
    },
    onError: () => toast.error('Failed to update checklist item'),
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  if (!company) {
    return <div className="text-[var(--text-muted)] text-sm">Company not found.</div>
  }

  const isTracked = !!company.user_state

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Back */}
      <button
        onClick={() => navigate('/companies')}
        className="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Companies
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{company.name}</h1>
          <Badge variant="secondary" className="mt-1">{company.cluster}</Badge>
        </div>
        <div className="flex items-center gap-2">
          {!isTracked ? (
            <Button size="sm" onClick={() => trackMutation.mutate()} disabled={trackMutation.isPending}>
              {trackMutation.isPending ? 'Tracking…' : 'Track Company'}
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--text-muted)]">Status:</span>
              <Select
                value={company.user_state?.application_status}
                onValueChange={(v) => statusMutation.mutate(v as ApplicationStatus)}
              >
                <SelectTrigger className="h-8 text-xs w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPLICATION_STATUSES.map(s => (
                    <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-4">
          {company.hiring_process && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Hiring Process</CardTitle></CardHeader>
              <CardContent>
                <div className="prose prose-sm prose-invert max-w-none text-[var(--text-secondary)]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{company.hiring_process}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}
          {company.oa_pattern && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">OA Pattern</CardTitle></CardHeader>
              <CardContent>
                <div className="prose prose-sm prose-invert max-w-none text-[var(--text-secondary)]">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{company.oa_pattern}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}
          {company.frequent_dsa_topics.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Frequent DSA Topics</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5">
                  {company.frequent_dsa_topics.map(t => (
                    <Badge key={t} variant="secondary">{t}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Checklist sidebar */}
        <div>
          {isTracked && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                  Checklist
                  <span className="text-xs font-normal text-[var(--text-muted)]">
                    {checklist?.progress_pct.toFixed(0)}%
                  </span>
                </CardTitle>
                {checklist && <Progress value={checklist.progress_pct} className="h-1" />}
              </CardHeader>
              <CardContent className="pt-0">
                {checklistLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-5" />)}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {checklist?.items.map(item => (
                      <label
                        key={item.id}
                        className="flex items-center gap-2.5 cursor-pointer group"
                      >
                        <Checkbox
                          checked={item.is_done}
                          onCheckedChange={(checked) =>
                            toggleMutation.mutate({ itemId: item.id, is_done: checked === true })
                          }
                          disabled={toggleMutation.isPending}
                        />
                        <span className={`text-xs ${item.is_done ? 'line-through text-[var(--text-muted)]' : 'text-[var(--text-secondary)]'}`}>
                          {item.label}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
