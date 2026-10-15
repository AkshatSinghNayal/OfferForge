import { format, isToday, parseISO } from 'date-fns'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  Plus,
  Clock3,
  Trash2,
  ListTodo,
  ChevronDown,
} from 'lucide-react'
import { toast } from 'sonner'
import { workspaceApi } from '@/api/workspace'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

export function TaskPlan() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [minutes, setMinutes] = useState(25)
  const [showDone, setShowDone] = useState(false)
  const query = useQuery({
    queryKey: ['preparation-tasks'],
    queryFn: workspaceApi.tasks,
  })
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ['preparation-tasks'] })
    void qc.invalidateQueries({ queryKey: ['dashboard-summary'] })
  }
  const create = useMutation({
    mutationFn: () =>
      workspaceApi.createTask({
        title: title.trim(),
        due_date: date || null,
        minutes,
      }),
    onSuccess: () => {
      refresh()
      setOpen(false)
      setTitle('')
      setDate('')
      toast.success('Added to your plan')
    },
    onError: () =>
      toast.error('Could not save your task. Your draft is still here.'),
  })
  const toggle = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      workspaceApi.completeTask(id, done),
    onSuccess: (task) => {
      refresh()
      if (task.is_done)
        toast.success('One step closer.', {
          action: {
            label: 'Undo',
            onClick: () => toggle.mutate({ id: task.id, done: false }),
          },
        })
    },
    onError: () => toast.error('Could not update this task. Try again.'),
  })
  const remove = useMutation({
    mutationFn: workspaceApi.deleteTask,
    onSuccess: refresh,
    onError: () => toast.error('Could not remove task'),
  })
  const all = query.data ?? []
  const pending = all.filter((t) => !t.is_done)
  const visible = showDone ? all : pending
  return (
    <section className="workspace-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MAKE ROOM FOR PROGRESS</p>
          <h2>
            Your preparation plan{' '}
            <span className="count-pill">{pending.length}</span>
          </h2>
        </div>
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          <Plus /> Add task
        </Button>
      </div>
      {query.isPending ? (
        <div className="p-6 animate-pulse text-sm text-[var(--text-muted)]">
          Loading your plan…
        </div>
      ) : query.isError ? (
        <div className="empty-inline">
          Your plan couldn’t load.{' '}
          <Button variant="link" onClick={() => query.refetch()}>
            Retry
          </Button>
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-inline">
          <ListTodo className="mx-auto mb-3 h-7 w-7 text-[var(--accent)]" />
          <h3>
            {all.length
              ? 'You’re all caught up.'
              : 'A little structure goes a long way.'}
          </h3>
          <p>Add a task, or turn a resume-analysis gap into your next step.</p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {visible.map((task) => (
            <div key={task.id} className="task-row">
              <button
                type="button"
                className={`task-check ${task.is_done ? 'done' : ''}`}
                aria-label={`${task.is_done ? 'Reopen' : 'Complete'} ${task.title}`}
                aria-pressed={task.is_done}
                disabled={toggle.isPending}
                onClick={() =>
                  toggle.mutate({ id: task.id, done: !task.is_done })
                }
              >
                {task.is_done && <Check size={13} />}
              </button>
              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm font-medium ${task.is_done ? 'line-through text-[var(--text-muted)]' : ''}`}
                >
                  {task.title}
                </p>
                {task.details && (
                  <p className="mt-1 text-sm text-[var(--text-secondary)] leading-relaxed">
                    {task.details}
                  </p>
                )}
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-[var(--text-muted)]">
                  <span className="flex items-center gap-1">
                    <Clock3 size={12} />
                    {task.minutes} min
                  </span>
                  {task.source_label && (
                    <span className="text-[var(--accent)]">
                      From {task.source_label}
                    </span>
                  )}
                  {task.due_date && (
                    <span>
                      {isToday(parseISO(task.due_date))
                        ? 'Due today'
                        : `Due ${format(parseISO(task.due_date), 'MMM d')}`}
                    </span>
                  )}
                </div>
              </div>
              <button
                className="quiet-icon"
                aria-label={`Delete ${task.title}`}
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm('Remove this task from your plan?'))
                    remove.mutate(task.id)
                }}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      )}
      {all.some((t) => t.is_done) && (
        <button
          className="flex items-center gap-2 px-6 py-4 text-xs text-[var(--text-muted)]"
          onClick={() => setShowDone(!showDone)}
        >
          <ChevronDown size={14} />
          {showDone ? 'Hide' : 'Show'} completed tasks
        </button>
      )}
      <Dialog open={open} onOpenChange={(v) => !create.isPending && setOpen(v)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Make your next step concrete</DialogTitle>
            <DialogDescription>
              A small, achievable task for your preparation plan.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
          >
            <label className="field-label">
              Task
              <Input
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Review SQL joins and solve two problems"
                required
                maxLength={300}
              />
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label className="field-label">
                Due date · optional
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </label>
              <label className="field-label">
                Estimated minutes
                <Input
                  type="number"
                  min={5}
                  max={240}
                  value={minutes}
                  onChange={(e) => setMinutes(Number(e.target.value))}
                />
              </label>
            </div>
            <Button type="submit" disabled={!title.trim() || create.isPending}>
              {create.isPending ? 'Saving…' : 'Add to plan'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </section>
  )
}
