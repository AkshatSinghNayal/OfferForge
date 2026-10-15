/** Company preparation library; role tracking lives in Applications. */
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import confetti from 'canvas-confetti'
import axios from 'axios'
import { Plus, ChevronRight, Building2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState } from '@/components/shared/EmptyState'
import { companiesApi, type Cluster, type TrackedCompany } from '@/api/companies'
import { differenceInCalendarDays } from 'date-fns'

// ─── Confetti session flag ────────────────────────────────────────────────────
const CELEBRATED_KEY = 'celebrated_companies'
function getCelebrated(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(CELEBRATED_KEY) ?? '[]') as string[])
  } catch { return new Set() }
}
function markCelebrated(id: string) {
  const s = getCelebrated()
  s.add(id)
  try { sessionStorage.setItem(CELEBRATED_KEY, JSON.stringify([...s])) } catch { /* ignore */ }
}

// ─── Cluster tabs ─────────────────────────────────────────────────────────────
const CLUSTERS: Array<{ value: string; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'FAANG', label: 'FAANG' },
  { value: 'Product-based', label: 'Product' },
  { value: 'Service-based', label: 'Service' },
  { value: 'FinTech', label: 'FinTech' },
  { value: 'Startups', label: 'Startups' },
]

// ─── Add company form ─────────────────────────────────────────────────────────
const addCompanySchema = z.object({
  name: z.string().min(1, 'Name is required').max(160),
  cluster: z.enum(['FAANG', 'Product-based', 'Service-based', 'FinTech', 'Startups'] as const),
})
type AddCompanyForm = z.infer<typeof addCompanySchema>

export default function CompaniesPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [cluster, setCluster] = useState('all')
  const [addOpen, setAddOpen] = useState(false)

  // Tracked companies (user_company)
  const { data, isLoading } = useQuery({
    queryKey: ['tracked-companies', cluster],
    queryFn: () =>
      companiesApi.listTracked({
        cluster: cluster === 'all' ? undefined : cluster,
        limit: 100,
      }),
  })

  // Confetti effect when a company hits 100%
  const celebrated = useRef(getCelebrated())
  useEffect(() => {
    data?.items.forEach(tc => {
      if (
        tc.checklist_progress_pct === 100 &&
        !celebrated.current.has(tc.id)
      ) {
        markCelebrated(tc.id)
        celebrated.current.add(tc.id)
        confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } })
        toast.success(`🎉 ${tc.company_name} checklist complete!`)
      }
    })
  }, [data])

  // Add company mutation — creates a custom company, then tracks it
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AddCompanyForm>({ resolver: zodResolver(addCompanySchema) })

  const addMutation = useMutation({
    mutationFn: async (form: AddCompanyForm) => {
      const company = await companiesApi.create({ name: form.name, cluster: form.cluster as Cluster })
      await companiesApi.track(company.id, {})
      return company
    },
    onSuccess: (company) => {
      toast.success(`Added ${company.name} to your preparation library`)
      qc.invalidateQueries({ queryKey: ['tracked-companies'] })
      setAddOpen(false)
      reset()
    },
    onError: (err) => {
      if (axios.isAxiosError(err)) {
        toast.error(err.response?.data?.detail ?? 'Failed to add company')
      } else {
        toast.error('Failed to add company')
      }
    },
  })

  const onSubmit = (form: AddCompanyForm) => addMutation.mutate(form)
  const selectedCluster = watch('cluster')

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Company library</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            {data?.total ?? 0} tracked
          </p>
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4 mr-1" /> Add Company
        </Button>
      </div>

      {/* Cluster tabs */}
      <Tabs value={cluster} onValueChange={setCluster}>
        <TabsList className="h-8">
          {CLUSTERS.map(c => (
            <TabsTrigger key={c.value} value={c.value} className="text-xs px-3 py-1">
              {c.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-44 rounded-xl" />)}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={<Building2 className="h-12 w-12" />}
          title="Build your preparation library"
          description="Add a company to organize its research and preparation checklist. Track roles separately in Applications."
          actionLabel="Add Company"
          onAction={() => setAddOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {data?.items.map(tc => (
            <CompanyCard key={tc.id} tc={tc} navigate={navigate} />
          ))}
        </div>
      )}

      {/* Add Company Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Add Company</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="name">Company name</Label>
              <Input id="name" placeholder="e.g. Google" {...register('name')} aria-invalid={!!errors.name} />
              {errors.name && <p className="text-xs text-[var(--danger)]">{errors.name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Cluster</Label>
              <Select onValueChange={(v) => setValue('cluster', v as Cluster)} value={selectedCluster}>
                <SelectTrigger><SelectValue placeholder="Select cluster" /></SelectTrigger>
                <SelectContent>
                  {(['FAANG', 'Product-based', 'Service-based', 'FinTech', 'Startups'] as const).map(c => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.cluster && <p className="text-xs text-[var(--danger)]">{errors.cluster.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => { setAddOpen(false); reset() }}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting || addMutation.isPending}>
                {addMutation.isPending ? 'Adding…' : 'Add to library'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Company card ─────────────────────────────────────────────────────────────
function CompanyCard({ tc, navigate }: { tc: TrackedCompany; navigate: ReturnType<typeof useNavigate> }) {

  const daysLeft = tc.deadline
    ? differenceInCalendarDays(new Date(tc.deadline), new Date())
    : null

  return (
    <Card
      className={`cursor-pointer transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg relative ${
        tc.checklist_progress_pct === 100 ? 'border-[var(--success)]/40' : ''
      }`}
      onClick={() => navigate(`/companies/${tc.company_id}`)}
    >
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between mb-3 pr-5">
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)] leading-tight truncate max-w-[160px]">
              {tc.company_name}
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{tc.cluster}</p>
          </div>

        </div>

        {/* Progress */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[var(--text-muted)]">Preparation</span>
            <span className={`text-xs font-medium ${
              tc.checklist_progress_pct === 100
                ? 'text-[var(--success)]'
                : tc.checklist_progress_pct >= 50
                ? 'text-[var(--warning)]'
                : 'text-[var(--text-muted)]'
            }`}>
              {tc.checklist_progress_pct.toFixed(0)}%
            </span>
          </div>
          <Progress value={tc.checklist_progress_pct} className="h-1.5" />
        </div>

        {/* Days left */}
        <div className="flex items-center justify-between text-xs">
          {daysLeft !== null ? (
            <span className={`${daysLeft < 0 ? 'text-[var(--danger)]' : daysLeft <= 7 ? 'text-[var(--warning)]' : 'text-[var(--text-muted)]'}`}>
              {daysLeft < 0
                ? `${Math.abs(daysLeft)}d overdue`
                : daysLeft === 0
                ? 'Due today'
                : `${daysLeft}d left`}
            </span>
          ) : (
            <span className="text-[var(--text-muted)]">No deadline</span>
          )}
          <ChevronRight className="h-3 w-3 text-[var(--text-muted)]" />
        </div>
      </CardContent>
    </Card>
  )
}
