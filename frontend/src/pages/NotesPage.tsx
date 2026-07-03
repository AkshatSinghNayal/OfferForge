import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Plus, Edit2, Trash2, Eye, StickyNote } from 'lucide-react'
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
import { notesApi, type NoteType, type NotePublic } from '@/api/notes'
import { formatDistanceToNow } from 'date-fns'

const NOTE_TYPES: NoteType[] = ['Interview Note', 'Revision Schedule', 'Concept', 'HR Answer', 'Personal']

const schema = z.object({
  title: z.string().min(1, 'Title required').max(255),
  content: z.string().min(1, 'Content required').max(50000),
  type: z.enum(['Interview Note', 'Revision Schedule', 'Concept', 'HR Answer', 'Personal'] as const),
})
type NoteForm = z.infer<typeof schema>

export default function NotesPage() {
  const qc = useQueryClient()
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<NotePublic | null>(null)
  const [viewTarget, setViewTarget] = useState<NotePublic | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [previewMode, setPreviewMode] = useState(false)

  const params = typeFilter === 'all' ? { limit: 100 } : { type: typeFilter, limit: 100 }
  const { data, isLoading } = useQuery({
    queryKey: ['notes', typeFilter],
    queryFn: () => notesApi.list(params),
  })

  const form = useForm<NoteForm>({ resolver: zodResolver(schema) })
  const contentValue = form.watch('content')

  const createMutation = useMutation({
    mutationFn: (f: NoteForm) => notesApi.create({ title: f.title, content: f.content, type: f.type as NoteType }),
    onSuccess: () => {
      toast.success('Note created')
      qc.invalidateQueries({ queryKey: ['notes'] })
      setAddOpen(false)
      form.reset()
    },
    onError: (err) => toast.error(axios.isAxiosError(err) ? (err.response?.data?.detail ?? 'Failed') : 'Failed to create note'),
  })

  const editMutation = useMutation({
    mutationFn: (f: NoteForm) => notesApi.update(editTarget!.id, { title: f.title, content: f.content, type: f.type as NoteType }),
    onSuccess: () => {
      toast.success('Note updated')
      qc.invalidateQueries({ queryKey: ['notes'] })
      setEditTarget(null)
    },
    onError: () => toast.error('Failed to update note'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => notesApi.delete(id),
    onSuccess: () => {
      toast.success('Note deleted')
      qc.invalidateQueries({ queryKey: ['notes'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Failed to delete note'),
  })

  const openEdit = (note: NotePublic) => {
    setEditTarget(note)
    form.reset({ title: note.title, content: note.content, type: note.type })
    setPreviewMode(false)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Notes</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">{data?.total ?? 0} notes</p>
        </div>
        <Button size="sm" onClick={() => { setAddOpen(true); form.reset(); setPreviewMode(false) }}>
          <Plus className="h-4 w-4 mr-1" /> New Note
        </Button>
      </div>

      {/* Type filter tabs */}
      <Tabs value={typeFilter} onValueChange={setTypeFilter}>
        <TabsList className="h-8">
          <TabsTrigger value="all" className="text-xs px-3">All</TabsTrigger>
          {NOTE_TYPES.map(t => (
            <TabsTrigger key={t} value={t} className="text-xs px-3 hidden sm:flex">{t}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon={<StickyNote className="h-12 w-12" />}
          title="No notes yet"
          description="Create notes for interview prep, revision schedules, concepts, and more."
          actionLabel="New Note"
          onAction={() => { setAddOpen(true); form.reset(); setPreviewMode(false) }}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data?.items.map(note => (
            <Card key={note.id} className="group cursor-pointer" onClick={() => setViewTarget(note)}>
              <CardContent className="pt-3 pb-3">
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate flex-1">{note.title}</p>
                  <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                    <button onClick={() => openEdit(note)} aria-label="Edit"><Edit2 className="h-3.5 w-3.5 text-[var(--text-muted)] hover:text-[var(--accent)]" /></button>
                    <button onClick={() => setDeleteTarget(note.id)} aria-label="Delete"><Trash2 className="h-3.5 w-3.5 text-[var(--text-muted)] hover:text-[var(--danger)]" /></button>
                  </div>
                </div>
                <Badge variant="secondary" className="text-[10px] mb-2">{note.type}</Badge>
                <p className="text-xs text-[var(--text-muted)] line-clamp-3">{note.content.slice(0, 150)}</p>
                <p className="text-[10px] text-[var(--text-muted)] mt-2">
                  {formatDistanceToNow(new Date(note.updated_at), { addSuffix: true })}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Note form dialog (add & edit) */}
      <NoteFormDialog
        open={addOpen || !!editTarget}
        onClose={() => { setAddOpen(false); setEditTarget(null) }}
        title={editTarget ? 'Edit Note' : 'New Note'}
        form={form}
        previewMode={previewMode}
        setPreviewMode={setPreviewMode}
        contentValue={contentValue}
        onSubmit={form.handleSubmit(f => editTarget ? editMutation.mutate(f) : createMutation.mutate(f))}
        isPending={createMutation.isPending || editMutation.isPending}
      />

      {/* View note dialog */}
      <Dialog open={!!viewTarget} onOpenChange={v => { if (!v) setViewTarget(null) }}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {viewTarget && (
            <>
              <DialogHeader>
                <DialogTitle>{viewTarget.title}</DialogTitle>
                <Badge variant="secondary" className="w-fit text-xs">{viewTarget.type}</Badge>
              </DialogHeader>
              <div className="prose prose-sm prose-invert max-w-none text-[var(--text-secondary)] mt-2">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewTarget.content}</ReactMarkdown>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null) }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Delete Note?</DialogTitle></DialogHeader>
          <p className="text-sm text-[var(--text-secondary)]">This cannot be undone.</p>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget)} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function NoteFormDialog({
  open, onClose, title, form, previewMode, setPreviewMode, contentValue, onSubmit, isPending,
}: {
  open: boolean
  onClose: () => void
  title: string
  form: ReturnType<typeof useForm<NoteForm>>
  previewMode: boolean
  setPreviewMode: (v: boolean) => void
  contentValue: string
  onSubmit: (e?: React.BaseSyntheticEvent) => void
  isPending: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <form onSubmit={onSubmit} className="space-y-3 pt-2">
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input {...form.register('title')} placeholder="Note title" aria-invalid={!!form.formState.errors.title} />
            {form.formState.errors.title && <p className="text-xs text-[var(--danger)]">{form.formState.errors.title.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select value={form.watch('type')} onValueChange={v => form.setValue('type', v as NoteType)}>
              <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
              <SelectContent>
                {(['Interview Note', 'Revision Schedule', 'Concept', 'HR Answer', 'Personal'] as const).map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.type && <p className="text-xs text-[var(--danger)]">Type is required</p>}
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label>Content (Markdown)</Label>
              <button
                type="button"
                onClick={() => setPreviewMode(!previewMode)}
                className="flex items-center gap-1 text-xs text-[var(--accent)] hover:underline"
              >
                <Eye className="h-3 w-3" /> {previewMode ? 'Edit' : 'Preview'}
              </button>
            </div>
            {previewMode ? (
              <div className="min-h-[160px] rounded-xl border border-[var(--border)] p-3 prose prose-sm prose-invert max-w-none text-[var(--text-secondary)]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{contentValue || '*Nothing to preview*'}</ReactMarkdown>
              </div>
            ) : (
              <Textarea
                {...form.register('content')}
                placeholder="# Notes&#10;&#10;Write in Markdown…"
                className="h-40 font-mono text-xs"
                aria-invalid={!!form.formState.errors.content}
              />
            )}
            {form.formState.errors.content && <p className="text-xs text-[var(--danger)]">{form.formState.errors.content.message}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={isPending}>{isPending ? 'Saving…' : 'Save'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
