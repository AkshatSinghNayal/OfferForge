import { CheckCircle2, CircleAlert, Lightbulb, MinusCircle, Sparkles, Target, TrendingUp } from 'lucide-react'
import type { JobMatchAnalysis, JobRequirementAssessment, JobRequirementStatus } from '@/api/resumes'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface JobMatchResultsDialogProps {
  analysis: JobMatchAnalysis | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const STATUS_META = {
  matched: { label: 'Matched', icon: CheckCircle2, badge: 'success' as const, color: 'var(--success)' },
  partial: { label: 'Partial', icon: MinusCircle, badge: 'warning' as const, color: 'var(--warning)' },
  missing: { label: 'Missing', icon: CircleAlert, badge: 'destructive' as const, color: 'var(--danger)' },
}

function scoreColor(score: number) {
  if (score >= 75) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
}

function ScoreRing({ score }: { score: number }) {
  const radius = 48
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score / 100)
  const color = scoreColor(score)
  return (
    <div className="relative h-32 w-32 shrink-0" role="img" aria-label={`Estimated job match ${score}%`}>
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--border)" strokeWidth="9" />
        <circle
          cx="60" cy="60" r={radius} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 5px color-mix(in srgb, ${color} 45%, transparent))` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tracking-tight text-[var(--text-primary)]">{score}%</span>
        <span className="text-[10px] uppercase tracking-widest text-[var(--text-muted)]">match</span>
      </div>
    </div>
  )
}

function RequirementRow({ item }: { item: JobRequirementAssessment }) {
  const meta = STATUS_META[item.status]
  const Icon = meta.icon
  return (
    <article className="rounded-xl border border-[var(--border)] bg-[var(--bg)]/45 p-4">
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 shrink-0" style={{ color: meta.color }} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-sm font-medium leading-snug text-[var(--text-primary)]">{item.requirement}</p>
            <div className="flex gap-1.5">
              {item.importance === 'required' && <Badge variant="outline" className="text-[10px]">Required</Badge>}
              <Badge variant={meta.badge} className="text-[10px]">{meta.label}</Badge>
            </div>
          </div>
          {item.evidence.length > 0 && (
            <div className="mt-2 rounded-lg border-l-2 border-[var(--success)]/60 bg-[var(--success)]/5 px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--success)]">Resume evidence</p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">{item.evidence.join(' · ')}</p>
            </div>
          )}
          {item.gap && <p className="mt-2 text-xs leading-relaxed text-[var(--text-muted)]"><span className="font-medium text-[var(--text-secondary)]">Gap:</span> {item.gap}</p>}
          {item.recommendation && <p className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]"><span className="font-medium text-[var(--text-secondary)]">Next step:</span> {item.recommendation}</p>}
        </div>
      </div>
    </article>
  )
}

function RequirementList({ requirements, status }: { requirements: JobRequirementAssessment[]; status?: JobRequirementStatus }) {
  const filtered = status ? requirements.filter(item => item.status === status) : requirements
  if (filtered.length === 0) return <p className="py-10 text-center text-sm text-[var(--text-muted)]">No requirements in this group.</p>
  return <div className="space-y-2">{filtered.map((item, index) => <RequirementRow key={`${item.requirement}-${index}`} item={item} />)}</div>
}

export function JobMatchResultsDialog({ analysis, open, onOpenChange }: JobMatchResultsDialogProps) {
  if (!analysis) return null
  const counts = analysis.requirements.reduce((acc, item) => ({ ...acc, [item.status]: acc[item.status] + 1 }), { matched: 0, partial: 0, missing: 0 })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[92vh] max-w-5xl flex-col overflow-hidden p-0">
        <DialogHeader className="sr-only">
          <DialogTitle>Resume job match results</DialogTitle>
          <DialogDescription>Evidence-based comparison of your resume and job description.</DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto">
          <section className="border-b border-[var(--border)] bg-gradient-to-br from-[var(--accent)]/12 via-[var(--card)] to-violet-500/10 px-6 py-6 sm:px-8">
            <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
              <ScoreRing score={analysis.overall_score} />
              <div className="min-w-0 flex-1 text-center sm:text-left">
                <div className="mb-2 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                  <Badge className="gap-1"><Sparkles className="h-3 w-3" /> AI analysis</Badge>
                  <Badge variant="outline" className="capitalize">{analysis.confidence} confidence</Badge>
                </div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)] sm:text-2xl">
                  {analysis.job_title || 'Job match analysis'}
                </h2>
                {analysis.company_name && <p className="mt-0.5 text-sm text-[var(--text-muted)]">at {analysis.company_name}</p>}
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                  Analyzed {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(analysis.created_at))}
                </p>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">{analysis.summary}</p>
                <p className="mt-3 text-[11px] text-[var(--text-muted)]">Estimated alignment based only on evidence found in your resume—not a hiring probability.</p>
              </div>
            </div>
          </section>

          <div className="space-y-6 px-6 py-6 sm:px-8">
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Target className="h-4 w-4 text-[var(--accent)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Match breakdown</h3>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {analysis.breakdown.map(item => (
                  <div key={item.category} className="rounded-xl border border-[var(--border)] bg-[var(--bg)]/45 p-3.5">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-medium text-[var(--text-secondary)]">{item.label}</span>
                      <span className="text-sm font-semibold" style={{ color: scoreColor(item.score) }}>{item.score}%</span>
                    </div>
                    <Progress value={item.score} className="h-1.5" />
                    <p className="mt-2 text-[10px] text-[var(--text-muted)]">{item.matched} matched · {item.partial} partial · {item.missing} missing</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-[var(--success)]/20 bg-[var(--success)]/5 p-4">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><TrendingUp className="h-4 w-4 text-[var(--success)]" /> Resume strengths</h3>
                {analysis.strengths.length > 0 ? (
                  <ul className="space-y-2">
                    {analysis.strengths.map((item, index) => <li key={index} className="flex gap-2 text-xs leading-relaxed text-[var(--text-secondary)]"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--success)]" />{item}</li>)}
                  </ul>
                ) : <p className="text-xs text-[var(--text-muted)]">No clear strengths were supported by resume evidence for this role.</p>}
              </div>
              <div className="rounded-xl border border-[var(--accent)]/20 bg-[var(--accent)]/5 p-4">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><Lightbulb className="h-4 w-4 text-[var(--accent)]" /> Highest-impact improvements</h3>
                {analysis.recommendations.length > 0 ? (
                  <ol className="space-y-2">
                    {analysis.recommendations.map((item, index) => <li key={index} className="flex gap-2 text-xs leading-relaxed text-[var(--text-secondary)]"><span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[var(--accent)]/15 text-[9px] font-semibold text-[var(--accent)]">{index + 1}</span>{item}</li>)}
                  </ol>
                ) : <p className="text-xs text-[var(--text-muted)]">No additional improvements were returned.</p>}
              </div>
            </section>

            <section>
              <Tabs defaultValue="all">
                <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">Requirement evidence</h3>
                  <TabsList className="h-auto w-full justify-start overflow-x-auto sm:w-auto">
                    <TabsTrigger value="all">All {analysis.requirements.length}</TabsTrigger>
                    <TabsTrigger value="matched">Matched {counts.matched}</TabsTrigger>
                    <TabsTrigger value="partial">Partial {counts.partial}</TabsTrigger>
                    <TabsTrigger value="missing">Missing {counts.missing}</TabsTrigger>
                  </TabsList>
                </div>
                <TabsContent value="all"><RequirementList requirements={analysis.requirements} /></TabsContent>
                <TabsContent value="matched"><RequirementList requirements={analysis.requirements} status="matched" /></TabsContent>
                <TabsContent value="partial"><RequirementList requirements={analysis.requirements} status="partial" /></TabsContent>
                <TabsContent value="missing"><RequirementList requirements={analysis.requirements} status="missing" /></TabsContent>
              </Tabs>
            </section>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
