import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import axios from 'axios'
import { Plus, ExternalLink, Trash2, BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState } from '@/components/shared/EmptyState'
import { resourcesApi, type ResourceCategory } from '@/api/resources'

const CATEGORIES: ResourceCategory[] = [
  'Career Portal', 'Referral', 'Coding Sheet', 'Interview Prep', 'YouTube', 'Notes', 'Article',
]

const schema = z.object({
  title: z.string().min(1, 'Title required').max(255),
  url: z.string().url('Must be a valid URL').max(2048),
  category: z.enum(['Career Portal', 'Referral', 'Coding Sheet', 'Interview Prep', 'YouTube', 'Notes', 'Article'] as const),
  description: z.string().max(10000).optional(),
})
type ResourceForm = z.infer<typeof schema>

export default function ResourcesPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<string>('all')
  const [addOpen, setAddOpen] = useState(false)

  const params = tab === 'all' ? {} : { category: tab }
  const { data, isLoading } = useQuery({
    queryKey: ['resources', tab],
    queryFn: () => resourcesApi.list({ ...params, limit: 100 }),
  })

  const { register, handleSubmit, setValue, watch, reset, formState: { errors } } = useForm<ResourceForm>({
    resolver: zodResolver(schema),
  })
  const selectedCat = watch('category')

  const createMutation = useMutation({
    mutationFn: (f: ResourceForm) => resourcesApi.create({
      title: f.title,
      url: f.url,
      category: f.category as ResourceCategory,
      description: f.description || null,
    }),
    onSuccess: () => {
      toast.success('Resource added')
      qc.invalidateQueries({ queryKey: ['resources'] })
      setAddOpen(false)
      reset()
    },
    onError: (err) => {
      toast.error(axios.isAxiosError(err) ? (err.response?.data?.detail ?? 'Failed') : 'Failed to add resource')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resourcesApi.delete(id),
    onSuccess: () => {
      toast.success('Resource deleted')
      qc.invalidateQueries({ queryKey: ['resources'] })
    },
    onError: () => toast.error('Failed to delete resource'),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Resources</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">{data?.total ?? 0} resources</p>
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4 mr-1" /> Add Resource
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-8 flex-wrap">
          <TabsTrigger value="all" className="text-xs px-3">All</TabsTrigger>
          {CATEGORIES.map(c => (
            <TabsTrigger key={c} value={c} className="text-xs px-3">{c}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={<BookOpen className="h-12 w-12" />}
          title="No resources yet"
          description="Add links to career portals, coding sheets, interview prep materials, and more."
          actionLabel="Add Resource"
          onAction={() => setAddOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data?.items.map(r => (
            <Card key={r.id} className="group relative">
              <CardContent className="pt-3 pb-3">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate flex-1">{r.title}</p>
                  <div className="flex items-center gap-1 shrink-0">
                    <a href={r.url} target="_blank" rel="noopener noreferrer" aria-label="Open resource">
                      <ExternalLink className="h-3.5 w-3.5 text-[var(--text-muted)] hover:text-[var(--accent)]" />
                    </a>
                    <button
                      onClick={() => deleteMutation.mutate(r.id)}
                      className="text-[var(--text-muted)] hover:text-[var(--danger)] opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label="Delete resource"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <Badge variant="secondary" className="text-[10px] mb-1.5">{r.category}</Badge>
                {r.description && (
                  <p className="text-xs text-[var(--text-muted)] line-clamp-2">{r.description}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={addOpen} onOpenChange={v => { if (!v) { setAddOpen(false); reset() } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Add Resource</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(f => createMutation.mutate(f))} className="space-y-3 pt-2">
            <div className="space-y-1.5">
              <Label>Title</Label>
              <Input {...register('title')} placeholder="LeetCode 75" aria-invalid={!!errors.title} />
              {errors.title && <p className="text-xs text-[var(--danger)]">{errors.title.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>URL</Label>
              <Input {...register('url')} placeholder="https://..." aria-invalid={!!errors.url} />
              {errors.url && <p className="text-xs text-[var(--danger)]">{errors.url.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select value={selectedCat} onValueChange={v => setValue('category', v as ResourceCategory)}>
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
              {errors.category && <p className="text-xs text-[var(--danger)]">Category is required</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Description (optional)</Label>
              <Textarea {...register('description')} placeholder="Brief description…" className="h-16" />
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => { setAddOpen(false); reset() }}>Cancel</Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Adding…' : 'Add'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
