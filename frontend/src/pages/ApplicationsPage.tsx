import { ApplicationCard } from '@/components/workspace/ApplicationCard'
import { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  BriefcaseBusiness,
  Columns3,
  List,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { toast } from 'sonner'
import {
  workspaceApi,
  STAGES,
  type Application,
  type ApplicationInput,
  type Stage,
} from '@/api/workspace'
import { resumesApi } from '@/api/resumes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const EMPTY: ApplicationInput = {
  company_name: '',
  role: '',
  stage: 'Saved',
  deadline: null,
  next_action: '',
  notes: '',
  is_pinned: false,
  resume_id: null,
}
const STAGE_COLORS: Record<Stage, string> = {
  Saved: '#94a3b8',
  Applied: '#60a5fa',
  Assessment: '#a78bfa',
  Interview: '#fbbf24',
  Offer: '#34d399',
  Closed: '#94a3b8',
}

export default function ApplicationsPage() {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [view, setView] = useState<'board' | 'table'>('board')
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('All stages')
  const [editing, setEditing] = useState<Application | null>(null)
  const [draft, setDraft] = useState<ApplicationInput>(EMPTY)
  const [open, setOpen] = useState(false)
  const openedFromUrl = useRef('')
  const query = useQuery({
    queryKey: ['applications'],
    queryFn: workspaceApi.applications,
  })
  const resumes = useQuery({ queryKey: ['resumes'], queryFn: resumesApi.list })
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ['applications'] })
    void qc.invalidateQueries({ queryKey: ['dashboard-summary'] })
  }
  const save = useMutation({
    mutationFn: () =>
      editing
        ? workspaceApi.updateApplication(editing.id, draft)
        : workspaceApi.createApplication(draft),
    onSuccess: () => {
      refresh()
      setOpen(false)
      setParams({}, { replace: true })
      toast.success(editing ? 'Application updated' : 'Application added')
    },
    onError: () =>
      toast.error(
        'Could not save. Your changes are still here—please try again.',
      ),
  })
  const update = useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: Partial<ApplicationInput>
    }) => workspaceApi.updateApplication(id, body),
    onSuccess: refresh,
    onError: () => toast.error('Could not update application. Try again.'),
  })
  const remove = useMutation({
    mutationFn: workspaceApi.deleteApplication,
    onSuccess: () => {
      refresh()
      setOpen(false)
      setParams({}, { replace: true })
      toast.success('Application removed')
    },
    onError: () => toast.error('Could not remove application'),
  })
  const begin = (app: Application | null) => {
    setEditing(app)
    setDraft(
      app
        ? {
            company_name: app.company_name,
            role: app.role,
            stage: app.stage,
            deadline: app.deadline,
            next_action: app.next_action,
            notes: app.notes,
            is_pinned: app.is_pinned,
            resume_id: app.resume_id,
          }
        : { ...EMPTY },
    )
    setOpen(true)
  }
  const selected = query.data?.find((a) => a.id === params.get('application'))
  const newFromUrl = params.get('new') === '1'
  const companyFromUrl = params.get('company') ?? ''
  useEffect(() => {
    const key = selected?.id ?? (newFromUrl ? 'new' : '')
    if (!key) {
      openedFromUrl.current = ''
      return
    }
    if (openedFromUrl.current === key) return
    openedFromUrl.current = key
    setEditing(selected ?? null)
    setDraft(
      selected
        ? {
            company_name: selected.company_name,
            role: selected.role,
            stage: selected.stage,
            deadline: selected.deadline,
            next_action: selected.next_action,
            notes: selected.notes,
            is_pinned: selected.is_pinned,
            resume_id: selected.resume_id,
          }
        : { ...EMPTY, company_name: companyFromUrl },
    )
    setOpen(true)
  }, [selected, newFromUrl, companyFromUrl])
  const visible = (query.data ?? []).filter(
    (a) =>
      `${a.company_name} ${a.role}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (stageFilter === 'All stages' || a.stage === stageFilter),
  )
  const active =
    query.data?.filter((a) => !['Offer', 'Closed'].includes(a.stage)).length ??
    0

  return (
    <div className="workspace-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">YOUR NEXT CHAPTER</p>
          <h1>
            Applications<span className="heading-dot">.</span>
          </h1>
          <p>Every opportunity, with a clear next step.</p>
        </div>
        <Button onClick={() => begin(null)}>
          <Plus />
          Add application
        </Button>
      </header>
      <div className="pipeline-summary">
        <span>
          <strong>{active}</strong> in progress
        </span>
        <span>
          <strong>
            {query.data?.filter((a) => a.stage === 'Interview').length ?? 0}
          </strong>{' '}
          interviews
        </span>
        <span>
          <strong>
            {query.data?.filter((a) => a.stage === 'Offer').length ?? 0}
          </strong>{' '}
          offers
        </span>
        <Link
          to="/companies"
          className="ml-auto flex items-center gap-1 text-[var(--accent)]"
        >
          Company library <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="workspace-toolbar">
        <div className="relative flex-1 min-w-40 max-w-sm">
          <Search
            size={16}
            className="absolute left-3 top-3 text-[var(--text-muted)]"
          />
          <Input
            className="pl-9"
            aria-label="Search applications"
            placeholder="Search company or role…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="workspace-select"
          aria-label="Filter by stage"
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
        >
          <option>All stages</option>
          {STAGES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <div className="segmented-control">
          <button
            aria-pressed={view === 'board'}
            onClick={() => setView('board')}
          >
            <Columns3 size={15} />
            Board
          </button>
          <button
            aria-pressed={view === 'table'}
            onClick={() => setView('table')}
          >
            <List size={15} />
            Table
          </button>
        </div>
      </div>
      {query.isPending ? (
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-64 animate-pulse rounded-xl bg-[var(--card)]"
            />
          ))}
        </div>
      ) : query.isError ? (
        <div className="workspace-panel empty-inline">
          <h3>We couldn’t load your applications.</h3>
          <Button variant="outline" onClick={() => query.refetch()}>
            Try again
          </Button>
        </div>
      ) : !query.data?.length ? (
        <div className="workspace-panel empty-inline py-20">
          <BriefcaseBusiness
            className="mx-auto mb-4 text-[var(--accent)]"
            size={36}
          />
          <h3>Your next opportunity starts here.</h3>
          <p>
            Save a role, attach a resume, and keep track of what comes next.
          </p>
          <Button className="mt-5" onClick={() => begin(null)}>
            <Plus />
            Add your first application
          </Button>
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-inline">No applications match your filters.</div>
      ) : view === 'board' ? (
        <div className="pipeline-board">
          {STAGES.filter(
            (s) => stageFilter === 'All stages' || s === stageFilter,
          ).map((stage) => (
            <section
              key={stage}
              className="pipeline-column"
              aria-label={`${stage} applications`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const id = e.dataTransfer.getData('text/plain')
                if (query.data?.some((a) => a.id === id) && !update.isPending)
                  update.mutate({ id, body: { stage } })
              }}
            >
              <div className="column-heading">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: STAGE_COLORS[stage] }}
                />
                <h2>{stage}</h2>
                <span className="count-pill">
                  {visible.filter((a) => a.stage === stage).length}
                </span>
              </div>
              <div className="space-y-3">
                {visible
                  .filter((a) => a.stage === stage)
                  .map((app) => (
                    <ApplicationCard
                      key={app.id}
                      app={app}
                      pending={update.isPending}
                      onOpen={begin}
                      onUpdate={(id, body) => update.mutate({ id, body })}
                    />
                  ))}
                {!visible.some((a) => a.stage === stage) && (
                  <div className="column-empty">No applications here yet</div>
                )}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="workspace-panel overflow-x-auto">
          <table className="workspace-table">
            <thead>
              <tr>
                <th>Company & role</th>
                <th>Stage</th>
                <th>Next action</th>
                <th>Deadline</th>
                <th>
                  <span className="sr-only">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((app) => (
                <tr key={app.id}>
                  <td>
                    <button className="text-left" onClick={() => begin(app)}>
                      <span className="font-medium">{app.company_name}</span>
                      <span className="block text-xs text-[var(--text-muted)] mt-1">
                        {app.role}
                      </span>
                    </button>
                  </td>
                  <td>
                    <span
                      className="stage-badge"
                      style={{ color: STAGE_COLORS[app.stage] }}
                    >
                      {app.stage}
                    </span>
                  </td>
                  <td data-label="Next action">{app.next_action || 'Set a next step'}</td>
                  <td data-label="Deadline" className="whitespace-nowrap">
                    {app.deadline
                      ? format(parseISO(app.deadline), 'MMM d, yyyy')
                      : '—'}
                  </td>
                  <td>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => begin(app)}
                    >
                      Open <ArrowUpRight />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Dialog
        open={open}
        onOpenChange={(v) => {
          if (!save.isPending && !remove.isPending) {
            setOpen(v)
            if (!v) setParams({}, { replace: true })
          }
        }}
      >
        <DialogContent className="max-w-xl max-h-[90dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editing ? 'Application details' : 'A new opportunity'}
            </DialogTitle>
            <DialogDescription>
              {editing
                ? 'Keep the role, resume, and next step in one place.'
                : 'You can track multiple roles at the same company.'}
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              save.mutate()
            }}
          >
            <div className="grid sm:grid-cols-2 gap-4">
              <label className="field-label">
                Company
                <Input
                  required
                  maxLength={160}
                  value={draft.company_name}
                  onChange={(e) =>
                    setDraft({ ...draft, company_name: e.target.value })
                  }
                  placeholder="e.g. Atlassian"
                />
              </label>
              <label className="field-label">
                Role
                <Input
                  required
                  maxLength={160}
                  value={draft.role}
                  onChange={(e) => setDraft({ ...draft, role: e.target.value })}
                  placeholder="e.g. Software Engineer Intern"
                />
              </label>
              <label className="field-label">
                Stage
                <select
                  className="workspace-select w-full"
                  value={draft.stage}
                  onChange={(e) =>
                    setDraft({ ...draft, stage: e.target.value as Stage })
                  }
                >
                  {STAGES.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Next deadline · optional
                <Input
                  type="date"
                  value={draft.deadline ?? ''}
                  onChange={(e) =>
                    setDraft({ ...draft, deadline: e.target.value || null })
                  }
                />
              </label>
            </div>
            <label className="field-label">
              Next action
              <Input
                maxLength={300}
                value={draft.next_action}
                onChange={(e) =>
                  setDraft({ ...draft, next_action: e.target.value })
                }
                placeholder="Tailor resume and submit the application"
              />
            </label>
            <label className="field-label">
              Resume version
              <select
                className="workspace-select w-full"
                value={draft.resume_id ?? ''}
                disabled={resumes.isPending || resumes.isError}
                onChange={(e) =>
                  setDraft({ ...draft, resume_id: e.target.value || null })
                }
              >
                <option value="">No resume attached</option>
                {resumes.data?.items.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.version_label}
                    {r.is_active ? ' · active' : ''}
                  </option>
                ))}
              </select>
              {resumes.isError && (
                <span className="text-[var(--danger)]">
                  Resumes couldn’t load. Your existing attachment will be
                  preserved.
                </span>
              )}
            </label>
            <label className="field-label">
              Notes
              <Textarea
                maxLength={10000}
                rows={3}
                value={draft.notes}
                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
                placeholder="Interview details, contacts, or things to remember…"
              />
            </label>
            {editing && editing.history.length > 0 && (
              <div className="application-history">
                <p className="eyebrow mb-3">TIMELINE</p>
                {editing.history
                  .slice()
                  .reverse()
                  .map((event, i) => (
                    <div key={i} className="flex justify-between text-xs py-2">
                      <span>{event.stage}</span>
                      <span className="text-[var(--text-muted)]">
                        {format(parseISO(event.at), 'MMM d · h:mm a')}
                      </span>
                    </div>
                  ))}
              </div>
            )}
            <div className="flex justify-between border-t border-[var(--border)] pt-4">
              {editing ? (
                <Button
                  type="button"
                  variant="ghost"
                  className="text-[var(--danger)]"
                  disabled={remove.isPending || save.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        'Delete this application? This cannot be undone.',
                      )
                    )
                      remove.mutate(editing.id)
                  }}
                >
                  <Trash2 />
                  Remove
                </Button>
              ) : (
                <span />
              )}
              <Button
                type="submit"
                disabled={
                  save.isPending ||
                  remove.isPending ||
                  !draft.company_name.trim() ||
                  !draft.role.trim()
                }
              >
                {save.isPending
                  ? 'Saving…'
                  : editing
                    ? 'Save changes'
                    : 'Add application'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
