import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  CalendarDays,
  CheckCheck,
  Code2,
  FileText,
  Flame,
  Target,
} from 'lucide-react'
import {
  differenceInCalendarDays,
  format,
  formatDistanceToNow,
  parseISO,
} from 'date-fns'
import { useAuth } from '@/context/AuthContext'
import { dashboardApi } from '@/api/dashboard'
import { workspaceApi } from '@/api/workspace'
import { Button } from '@/components/ui/button'
import { TaskPlan } from '@/components/workspace/TaskPlan'

function activityLabel(action: string) {
  const labels: Record<string, string> = {
    resource_added: 'Saved a learning resource',
    resource_created: 'Saved a learning resource',
    note_created: 'Added a preparation note',
    dsa_problem_created: 'Added a practice problem',
    dsa_solved: 'Solved a practice problem',
    resume_uploaded: 'Uploaded a resume',
    resume_job_match_analyzed: 'Reviewed a resume against a role',
    application_created: 'Added an application',
    application_updated: 'Updated an application',
    preparation_task_completed: 'Completed a preparation task',
    checklist_item_completed: 'Completed a checklist item',
  }
  return (
    labels[action] ??
    action.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase())
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const summary = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.getSummary,
  })
  const streak = useQuery({
    queryKey: ['dashboard-streak'],
    queryFn: dashboardApi.getStreak,
  })
  const applications = useQuery({
    queryKey: ['applications'],
    queryFn: workspaceApi.applications,
  })
  const tasks = useQuery({
    queryKey: ['preparation-tasks'],
    queryFn: workspaceApi.tasks,
  })
  const active = (applications.data ?? []).filter(
    (a) => !['Closed', 'Offer'].includes(a.stage),
  )
  const deadlines = active
    .filter((a) => a.deadline)
    .sort((a, b) => a.deadline!.localeCompare(b.deadline!))
  const next = deadlines[0] ?? active.find((a) => a.is_pinned) ?? active[0]
  const remaining = next?.deadline
    ? differenceInCalendarDays(parseISO(next.deadline), new Date())
    : null
  const pending = tasks.data?.filter((t) => !t.is_done) ?? []
  const progress = Math.round(summary.data?.overall_progress ?? 0)
  const ready = !applications.isPending && !applications.isError
  return (
    <div className="workspace-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">
            {format(new Date(), 'EEEE, MMMM d').toUpperCase()}
          </p>
          <h1>
            A little closer, {user?.full_name?.split(' ')[0] || 'there'}
            <span className="heading-dot">.</span>
          </h1>
          <p>Your next opportunity starts with what you do today.</p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/applications?new=1">
            <PlusIcon />
            Add application
          </Link>
        </Button>
      </header>
      <div className="today-hero-grid">
        <section className="focus-card">
          <div className="focus-orbit" aria-hidden="true">
            <div />
            <div />
            <Target />
          </div>
          <div className="relative z-10 max-w-lg">
            <p className="eyebrow text-[var(--accent)] flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />{' '}
              YOUR NEXT MOVE
            </p>
            <h2>
              {applications.isPending
                ? 'Finding your next step…'
                : applications.isError
                  ? 'Your workspace is taking a moment.'
                  : next
                    ? next.next_action ||
                      `Move forward with ${next.company_name}.`
                    : 'Make space for your next chapter.'}
            </h2>
            <p>
              {next
                ? `${next.role} at ${next.company_name}${remaining !== null ? (remaining < 0 ? ` · Deadline passed ${Math.abs(remaining)} days ago. Review the status.` : remaining === 0 ? ' · Due today.' : ` · ${remaining} days until your deadline.`) : ' · One focused step at a time.'}`
                : applications.isError
                  ? 'We couldn’t load your applications. Try again to see your next step.'
                  : 'Save an opportunity, prepare with intention, and build momentum one day at a time.'}
            </p>
            {applications.isError ? (
              <Button variant="outline" onClick={() => applications.refetch()}>
                Try again
              </Button>
            ) : (
              <Button disabled={!ready} asChild>
                <Link
                  to={
                    next
                      ? `/applications?application=${next.id}`
                      : '/applications'
                  }
                >
                  {next ? 'Review application' : 'Explore your pipeline'}
                  <ArrowRight />
                </Link>
              </Button>
            )}
          </div>
        </section>
        <section className="progress-card">
          <div className="flex items-center justify-between">
            <p className="eyebrow">PREPARATION PROGRESS</p>
            <Target size={16} className="text-[var(--text-muted)]" />
          </div>
          <div className="flex items-baseline gap-2 mt-5">
            <strong className="text-5xl font-semibold tracking-tight">
              {summary.isPending || summary.isError ? '—' : progress}
              <span className="text-xl text-[var(--text-muted)]">%</span>
            </strong>
          </div>
          <div className="mt-5 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-[var(--text-muted)]">
            A blend of practice completion, resume readiness, and company
            checklists. A guide to your preparation, not a hiring prediction.
          </p>
          <Link
            to="/analytics"
            className="mt-5 inline-flex gap-2 items-center text-sm font-medium"
          >
            View breakdown <ArrowUpRight size={15} />
          </Link>
        </section>
      </div>
      <div className="today-metrics">
        {[
          {
            icon: BriefcaseBusiness,
            label: 'Active applications',
            value:
              applications.isError || applications.isPending
                ? '—'
                : active.length,
          },
          {
            icon: CalendarDays,
            label: 'Interviews in progress',
            value:
              applications.isError || applications.isPending
                ? '—'
                : active.filter((a) => a.stage === 'Interview').length,
          },
          {
            icon: CheckCheck,
            label: 'Tasks in your plan',
            value: tasks.isError || tasks.isPending ? '—' : pending.length,
          },
          {
            icon: Flame,
            label: 'Day streak',
            value:
              streak.isError || streak.isPending
                ? '—'
                : (streak.data?.current_streak ?? 0),
          },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label}>
            <Icon size={17} className="text-[var(--text-muted)]" />
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <div className="today-content-grid">
        <div className="space-y-6">
          <TaskPlan />
          <section className="workspace-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">KEEP YOUR MOMENTUM</p>
                <h2>A focused session</h2>
              </div>
            </div>
            <div className="quick-actions">
              <Link to="/dsa">
                <div className="action-icon">
                  <Code2 size={20} />
                </div>
                <div>
                  <h3>Practice with purpose</h3>
                  <p>Revisit a problem or log a new solution.</p>
                </div>
                <ArrowUpRight size={17} />
              </Link>
              <Link to="/resumes">
                <div className="action-icon violet">
                  <FileText size={20} />
                </div>
                <div>
                  <h3>Find your next improvement</h3>
                  <p>Match your resume to the role you want.</p>
                </div>
                <ArrowUpRight size={17} />
              </Link>
            </div>
          </section>
        </div>
        <aside className="space-y-6">
          <section className="workspace-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">ON THE HORIZON</p>
                <h2>Upcoming deadlines</h2>
              </div>
              <CalendarDays size={17} className="text-[var(--text-muted)]" />
            </div>
            {applications.isError ? (
              <p className="empty-inline">Deadlines couldn’t load.</p>
            ) : deadlines.length ? (
              <div className="px-5 pb-3">
                {deadlines.slice(0, 4).map((a) => (
                  <Link
                    key={a.id}
                    to={`/applications?application=${a.id}`}
                    className="deadline-row"
                  >
                    <div className="date-tile">
                      <span>{format(parseISO(a.deadline!), 'MMM')}</span>
                      <strong>{format(parseISO(a.deadline!), 'dd')}</strong>
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-sm font-medium">
                        {a.company_name}
                      </h3>
                      <p className="truncate text-xs text-[var(--text-muted)] mt-1">
                        {a.role}
                      </p>
                    </div>
                    <ArrowUpRight size={15} />
                  </Link>
                ))}
              </div>
            ) : (
              <p className="empty-inline">
                {applications.isPending
                  ? 'Loading deadlines…'
                  : 'No deadlines yet. Add one to an application to see it here.'}
              </p>
            )}
          </section>
          <section className="workspace-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">SMALL STEPS ADD UP</p>
                <h2>Recent activity</h2>
              </div>
            </div>
            {summary.isError ? (
              <div className="empty-inline">
                <p>Activity couldn’t load.</p>
                <Button variant="link" onClick={() => summary.refetch()}>
                  Retry
                </Button>
              </div>
            ) : summary.data?.recent_activity.length ? (
              <div className="activity-list">
                {summary.data.recent_activity.slice(0, 5).map((a) => (
                  <div key={a.id}>
                    <span className="activity-dot" />
                    <div>
                      <p>{activityLabel(a.action)}</p>
                      <time>
                        {formatDistanceToNow(new Date(a.created_at), {
                          addSuffix: true,
                        })}
                      </time>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-inline">
                {summary.isPending
                  ? 'Loading activity…'
                  : 'Your progress will appear here as you go.'}
              </p>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
function PlusIcon() {
  return (
    <span aria-hidden="true" className="text-lg leading-none">
      +
    </span>
  )
}
