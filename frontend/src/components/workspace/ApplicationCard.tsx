import { ArrowUpRight, CalendarDays, FileText, Pin } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import {
  STAGES,
  type Application,
  type ApplicationInput,
  type Stage,
} from '@/api/workspace'

export function ApplicationCard({
  app,
  pending,
  onOpen,
  onUpdate,
}: {
  app: Application
  pending: boolean
  onOpen: (app: Application) => void
  onUpdate: (id: string, body: Partial<ApplicationInput>) => void
}) {
  return (
    <article
      key={app.id}
      className="application-card"
      draggable={!pending}
      onDragStart={(e) => e.dataTransfer.setData('text/plain', app.id)}
    >
      <div className="flex items-center justify-between">
        <span className="company-monogram">
          {app.company_name.slice(0, 2).toUpperCase()}
        </span>
        <button
          className={`quiet-icon ${app.is_pinned ? 'text-[var(--accent)]' : ''}`}
          aria-label={`${app.is_pinned ? 'Unpin' : 'Pin'} ${app.company_name} ${app.role}`}
          disabled={pending}
          onClick={() => onUpdate(app.id, { is_pinned: !app.is_pinned })}
        >
          <Pin size={15} fill={app.is_pinned ? 'currentColor' : 'none'} />
        </button>
      </div>
      <button
        className="mt-4 block text-left w-full"
        onClick={() => onOpen(app)}
      >
        <h3 className="font-semibold text-sm">{app.role}</h3>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          {app.company_name}
        </p>
      </button>
      {app.next_action && (
        <p className="next-action">
          <ArrowUpRight size={13} />
          {app.next_action}
        </p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
        {app.deadline && (
          <span className="flex items-center gap-1">
            <CalendarDays size={12} />
            {format(parseISO(app.deadline), 'MMM d')}
          </span>
        )}
        {app.resume_id && (
          <span className="flex items-center gap-1">
            <FileText size={12} />
            Resume attached
          </span>
        )}
      </div>
      <select
        className="stage-select mt-4"
        aria-label={`Stage for ${app.company_name} ${app.role}`}
        value={app.stage}
        disabled={pending}
        onChange={(e) => onUpdate(app.id, { stage: e.target.value as Stage })}
      >
        {STAGES.map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
    </article>
  )
}
