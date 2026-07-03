import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import axios from 'axios'
import { Plus, ExternalLink, Trash2, Edit2, Code2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState } from '@/components/shared/EmptyState'
import { dsaApi, type Platform, type Difficulty, type DSAStatus, type ProblemCreate } from '@/api/dsa'

// ─── Schemas ──────────────────────────────────────────────────────────────────
const problemSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255),
  platform: z.enum(['LeetCode', 'GFG', 'Codeforces'] as const),
  external_url: z.string().min(1, 'URL is required').max(2048),
  difficulty: z.enum(['Easy', 'Medium', 'Hard'] as const),
  status: z.enum(['Not Started', 'In Progress', 'Solved', 'Skipped', 'Marked for Revision'] as const).optional(),
  tag_names: z.string().optional(), // comma-separated
  notes: z.string().max(10000).optional(),
})
type ProblemForm = z.infer<typeof problemSchema>

// ─── Difficulty badge ─────────────────────────────────────────────────────────
function DiffBadge({ d }: { d: Difficulty }) {
  const cls = d === 'Easy'
    ? 'text-[var(--success)] bg-[var(--success)]/10 border-transparent'
    : d === 'Medium'
    ? 'text-[var(--warning)] bg-[var(--warning)]/10 border-transparent'
    : 'text-[var(--danger)] bg-[var(--danger)]/10 border-transparent'
  return <Badge className={cls}>{d}</Badge>
}

// ─── Status badge ─────────────────────────────────────────────────────────────
const STATUS_VARIANT: Record<string, 'success' | 'warning' | 'secondary' | 'destructive'> = {
  Solved: 'success',
  'In Progress': 'warning',
  'Marked for Revision': 'warning',
  'Not Started': 'secondary',
  Skipped: 'destructive',
}

export default function DSAPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const qc = useQueryClient()

  // Filters from URL
  const platform = searchParams.get('platform') ?? ''
  const difficulty = searchParams.get('difficulty') ?? ''
  const status = searchParams.get('status') ?? ''
  const topic = searchParams.get('topic') ?? ''
  const revision = searchParams.get('revision') ?? ''

  const setFilter = (key: string, val: string) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      if (val) next.set(key, val)
      else next.delete(key)
      return next
    })
  }

  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  // Stats
  const { data: stats } = useQuery({
    queryKey: ['dsa-stats'],
    queryFn: dsaApi.getStats,
  })

  // Problems list
  const params = {
    platform: platform || undefined,
    difficulty: difficulty || undefined,
    status: status || undefined,
    topic: topic || undefined,
    limit: 100,
  }
  const { data, isLoading } = useQuery({
    queryKey: ['dsa-problems', params],
    queryFn: () => dsaApi.listProblems(params),
  })

  // Add/edit form
  const form = useForm<ProblemForm>({ resolver: zodResolver(problemSchema) })
  const editProblem = data?.items.find(p => p.id === editTarget)

  useEffect(() => {
    if (editTarget && editProblem) {
      form.reset({
        title: editProblem.title,
        platform: editProblem.platform,
        external_url: editProblem.external_url,
        difficulty: editProblem.difficulty,
        status: editProblem.status,
        tag_names: editProblem.tags.map(t => t.name).join(', '),
        notes: editProblem.notes ?? '',
      })
    } else if (!editTarget) {
      form.reset({ status: 'Not Started' })
    }
  }, [editTarget, editProblem])

  const toBody = (f: ProblemForm): ProblemCreate => ({
    title: f.title,
    platform: f.platform as Platform,
    external_url: f.external_url,
    difficulty: f.difficulty as Difficulty,
    status: (f.status as DSAStatus) ?? 'Not Started',
    tag_names: f.tag_names ? f.tag_names.split(',').map(t => t.trim()).filter(Boolean) : [],
    notes: f.notes || null,
  })

  const createMutation = useMutation({
    mutationFn: (f: ProblemForm) => dsaApi.createProblem(toBody(f)),
    onSuccess: () => {
      toast.success('Problem added')
      qc.invalidateQueries({ queryKey: ['dsa-problems'] })
      qc.invalidateQueries({ queryKey: ['dsa-stats'] })
      setAddOpen(false)
      form.reset()
    },
    onError: (err) => {
      toast.error(axios.isAxiosError(err) ? (err.response?.data?.detail ?? 'Failed') : 'Failed to add problem')
    },
  })

  const editMutation = useMutation({
    mutationFn: (f: ProblemForm) => dsaApi.updateProblem(editTarget!, toBody(f)),
    onSuccess: () => {
      toast.success('Problem updated')
      qc.invalidateQueries({ queryKey: ['dsa-problems'] })
      qc.invalidateQueries({ queryKey: ['dsa-stats'] })
      setEditTarget(null)
    },
    onError: () => toast.error('Failed to update problem'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => dsaApi.deleteProblem(id),
    onSuccess: () => {
      toast.success('Problem deleted')
      qc.invalidateQueries({ queryKey: ['dsa-problems'] })
      qc.invalidateQueries({ queryKey: ['dsa-stats'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Failed to delete problem'),
  })

  const toggleStatus = (id: string, current: DSAStatus) => {
    const next: DSAStatus = current === 'Solved' ? 'Not Started' : 'Solved'
    dsaApi.updateProblem(id, { status: next }).then(() => {
      qc.invalidateQueries({ queryKey: ['dsa-problems'] })
      qc.invalidateQueries({ queryKey: ['dsa-stats'] })
    })
  }

  const toggleRevision = (id: string, current: string) => {
    const next = current === 'None' ? 'Due' : current === 'Due' ? 'Done' : 'None'
    dsaApi.updateProblem(id, { revision_status: next as 'None' | 'Due' | 'Done' }).then(() => {
      qc.invalidateQueries({ queryKey: ['dsa-problems'] })
    })
  }

  const ProblemFormDialog = ({ open, onClose, title }: { open: boolean; onClose: () => void; title: string }) => (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <form onSubmit={form.handleSubmit(f => editTarget ? editMutation.mutate(f) : createMutation.mutate(f))} className="space-y-3 pt-2">
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input {...form.register('title')} placeholder="Two Sum" />
            {form.formState.errors.title && <p className="text-xs text-[var(--danger)]">{form.formState.errors.title.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Platform</Label>
              <Select value={form.watch('platform')} onValueChange={v => form.setValue('platform', v as Platform)}>
                <SelectTrigger><SelectValue placeholder="Platform" /></SelectTrigger>
                <SelectContent>
                  {(['LeetCode', 'GFG', 'Codeforces'] as const).map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                </SelectContent>
              </Select>
              {form.formState.errors.platform && <p className="text-xs text-[var(--danger)]">Required</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Difficulty</Label>
              <Select value={form.watch('difficulty')} onValueChange={v => form.setValue('difficulty', v as Difficulty)}>
                <SelectTrigger><SelectValue placeholder="Difficulty" /></SelectTrigger>
                <SelectContent>
                  {(['Easy', 'Medium', 'Hard'] as const).map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                </SelectContent>
              </Select>
              {form.formState.errors.difficulty && <p className="text-xs text-[var(--danger)]">Required</p>}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>URL</Label>
            <Input {...form.register('external_url')} placeholder="https://leetcode.com/problems/..." />
            {form.formState.errors.external_url && <p className="text-xs text-[var(--danger)]">{form.formState.errors.external_url.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select value={form.watch('status') ?? 'Not Started'} onValueChange={v => form.setValue('status', v as DSAStatus)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {(['Not Started', 'In Progress', 'Solved', 'Skipped', 'Marked for Revision'] as const).map(s => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Tags (comma-separated)</Label>
            <Input {...form.register('tag_names')} placeholder="arrays, dp, greedy" />
          </div>
          <div className="space-y-1.5">
            <Label>Notes</Label>
            <Textarea {...form.register('notes')} placeholder="Approach, edge cases…" className="h-20" />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={createMutation.isPending || editMutation.isPending}>
              {editTarget ? 'Save' : 'Add Problem'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">DSA Tracker</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            {stats?.overall_solved ?? 0} / {stats?.overall_total ?? 0} solved
          </p>
        </div>
        <Button size="sm" onClick={() => { setEditTarget(null); setAddOpen(true) }}>
          <Plus className="h-4 w-4 mr-1" /> Add Problem
        </Button>
      </div>

      {/* Topic progress bars */}
      {stats && stats.topic_wise.length > 0 && (
        <div className="flex gap-4 overflow-x-auto pb-2">
          {[...stats.topic_wise].sort((a, b) => b.pct - a.pct).slice(0, 8).map(t => (
            <div key={t.tag} className="min-w-[120px]">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[var(--text-secondary)] truncate">{t.tag}</span>
                <span className="text-[var(--text-muted)] ml-1">{t.pct.toFixed(0)}%</span>
              </div>
              <Progress value={t.pct} className="h-1.5" />
              <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{t.solved}/{t.total}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <FilterSelect value={platform} onChange={v => setFilter('platform', v)}
          options={['', 'LeetCode', 'GFG', 'Codeforces']} placeholder="All Platforms" />
        <FilterSelect value={difficulty} onChange={v => setFilter('difficulty', v)}
          options={['', 'Easy', 'Medium', 'Hard']} placeholder="All Difficulties" />
        <FilterSelect value={status} onChange={v => setFilter('status', v)}
          options={['', 'Not Started', 'In Progress', 'Solved', 'Skipped', 'Marked for Revision']}
          placeholder="All Statuses" />
        <FilterSelect value={revision} onChange={v => setFilter('revision', v)}
          options={['', 'None', 'Due', 'Done']} placeholder="All Revision" />
        {(platform || difficulty || status || topic || revision) && (
          <Button variant="ghost" size="sm" onClick={() => setSearchParams({})}>
            Clear filters
          </Button>
        )}
      </div>

      {/* Table — scrollable on mobile */}
      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)]" style={{ background: 'var(--card)' }}>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)] w-8">Done</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)]">Problem</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)] hidden sm:table-cell">Platform</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)] hidden md:table-cell">Difficulty</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)] hidden md:table-cell">Tags</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)]">Status</th>
              <th className="text-left p-3 text-xs font-medium text-[var(--text-muted)] hidden sm:table-cell">Revision</th>
              <th className="p-3 w-20"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}><td colSpan={8} className="p-3"><Skeleton className="h-5" /></td></tr>
              ))
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={8}>
                <EmptyState
                  icon={<Code2 className="h-10 w-10" />}
                  title="No problems yet"
                  description="Add your first DSA problem to start tracking."
                  actionLabel="Add Problem"
                  onAction={() => { setEditTarget(null); setAddOpen(true) }}
                />
              </td></tr>
            ) : (
              data?.items.map(p => (
                <tr
                  key={p.id}
                  className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--card)] transition-colors"
                  style={{ background: 'var(--bg)' }}
                >
                  <td className="p-3">
                    <Checkbox
                      checked={p.status === 'Solved'}
                      onCheckedChange={() => toggleStatus(p.id, p.status)}
                    />
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--text-primary)] font-medium truncate max-w-[200px]">{p.title}</span>
                      <a
                        href={p.external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={e => e.stopPropagation()}
                        className="text-[var(--text-muted)] hover:text-[var(--accent)]"
                        aria-label="Open problem"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </td>
                  <td className="p-3 hidden sm:table-cell">
                    <Badge variant="secondary" className="text-[10px]">{p.platform}</Badge>
                  </td>
                  <td className="p-3 hidden md:table-cell"><DiffBadge d={p.difficulty} /></td>
                  <td className="p-3 hidden md:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {p.tags.slice(0, 3).map(t => (
                        <Badge key={t.id} variant="outline" className="text-[10px] py-0">{t.name}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="p-3">
                    <Badge variant={STATUS_VARIANT[p.status] ?? 'secondary'} className="text-[10px]">
                      {p.status}
                    </Badge>
                  </td>
                  <td className="p-3 hidden sm:table-cell">
                    <button
                      onClick={() => toggleRevision(p.id, p.revision_status)}
                      className={`text-xs px-2 py-0.5 rounded-lg border transition-colors ${
                        p.revision_status === 'Due'
                          ? 'border-[var(--warning)] text-[var(--warning)]'
                          : p.revision_status === 'Done'
                          ? 'border-[var(--success)] text-[var(--success)]'
                          : 'border-[var(--border)] text-[var(--text-muted)]'
                      }`}
                    >
                      {p.revision_status}
                    </button>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => { setEditTarget(p.id); }}
                        aria-label="Edit"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-[var(--text-muted)] hover:text-[var(--danger)]"
                        onClick={() => setDeleteTarget(p.id)}
                        aria-label="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add dialog */}
      <ProblemFormDialog open={addOpen} onClose={() => { setAddOpen(false); form.reset() }} title="Add Problem" />

      {/* Edit dialog */}
      <ProblemFormDialog open={!!editTarget} onClose={() => setEditTarget(null)} title="Edit Problem" />

      {/* Delete confirm dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null) }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Delete Problem?</DialogTitle></DialogHeader>
          <p className="text-sm text-[var(--text-secondary)]">This cannot be undone.</p>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function FilterSelect({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  options: string[]
  placeholder: string
}) {
  return (
    <Select value={value || '__all__'} onValueChange={v => onChange(v === '__all__' ? '' : v)}>
      <SelectTrigger className="h-8 text-xs w-36">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__all__">{placeholder}</SelectItem>
        {options.filter(Boolean).map(o => <SelectItem key={o} value={o} className="text-xs">{o}</SelectItem>)}
      </SelectContent>
    </Select>
  )
}
