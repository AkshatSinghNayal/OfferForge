import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, Cell,
  PieChart, Pie, Tooltip, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid,
} from 'recharts'
import {
  Building2, Code2, FileText, CheckSquare,
  Flame, Plus, AlertCircle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'
import { dashboardApi } from '@/api/dashboard'
import { dsaApi } from '@/api/dsa'
import { TOOLTIP_STYLE, AXIS_TICK_STYLE } from '@/lib/chartTheme'
import { formatDistanceToNow, differenceInCalendarDays, format, subDays, eachDayOfInterval } from 'date-fns'

// ─── Readiness ring ───────────────────────────────────────────────────────────
function ReadinessRing({ pct, loading }: { pct: number; loading: boolean }) {
  const r = 44
  const circ = 2 * Math.PI * r
  const dash = loading ? 0 : (pct / 100) * circ

  return (
    <div className="flex flex-col items-center justify-center gap-1">
      <svg width="110" height="110" viewBox="0 0 110 110" aria-label={`Overall readiness: ${pct.toFixed(0)}%`}>
        {/* Track */}
        <circle cx="55" cy="55" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
        {/* Fill — animated via CSS transition on strokeDashoffset */}
        <circle
          cx="55" cy="55" r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ - dash}
          transform="rotate(-90 55 55)"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
        <text x="55" y="50" textAnchor="middle" fill="var(--text-primary)" fontSize="20" fontWeight="700">
          {loading ? '–' : `${pct.toFixed(0)}%`}
        </text>
        <text x="55" y="66" textAnchor="middle" fill="var(--text-muted)" fontSize="10">
          readiness
        </text>
      </svg>
    </div>
  )
}

// ─── Calendar heatmap (GitHub-style) ─────────────────────────────────────────
function CalendarHeatmap({ data }: { data: { date: string; count: number }[] }) {
  const today = new Date()
  const days = eachDayOfInterval({ start: subDays(today, 83), end: today }) // 12 weeks

  const countMap = new Map<string, number>()
  data.forEach(d => countMap.set(d.date, d.count))

  const maxCount = Math.max(1, ...data.map(d => d.count))

  const cellColor = (count: number) => {
    if (count === 0) return 'var(--text-muted)'
    const intensity = count / maxCount
    if (intensity > 0.75) return 'var(--accent)'
    if (intensity > 0.4) return 'var(--success)'
    return '#60A5FA'
  }

  const cellOpacity = (count: number) => {
    if (count === 0) return 0.15
    const intensity = count / maxCount
    return 0.5 + intensity * 0.5
  }

  // Group into weeks (columns)
  const weeks: Date[][] = []
  let week: Date[] = []
  days.forEach((d, i) => {
    week.push(d)
    if (week.length === 7 || i === days.length - 1) {
      weeks.push(week)
      week = []
    }
  })

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-1" style={{ minWidth: weeks.length * 14 }}>
        {weeks.map((wk, wi) => (
          <div key={wi} className="flex flex-col gap-1">
            {wk.map(day => {
              const key = format(day, 'yyyy-MM-dd')
              const count = countMap.get(key) ?? 0
              return (
                <div
                  key={key}
                  title={`${format(day, 'MMM d')}: ${count} activities`}
                  className="w-3 h-3 rounded-sm"
                  style={{
                    backgroundColor: cellColor(count),
                    opacity: cellOpacity(count),
                  }}
                />
              )
            })}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1 mt-2">
        <span className="text-[10px] text-[var(--text-muted)]">Less</span>
        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'var(--text-muted)', opacity: 0.15 }} />
        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#60A5FA', opacity: 0.7 }} />
        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'var(--success)', opacity: 0.8 }} />
        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'var(--accent)', opacity: 1 }} />
        <span className="text-[10px] text-[var(--text-muted)]">More</span>
      </div>
    </div>
  )
}

// ─── Error state ──────────────────────────────────────────────────────────────
function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="border-[var(--danger)]/30">
      <CardContent className="pt-4 flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-[var(--danger)] shrink-0" />
        <p className="text-sm text-[var(--text-secondary)]">{message}</p>
      </CardContent>
    </Card>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function NewUserEmpty() {
  return (
    <Card className="border-dashed">
      <CardContent className="py-10 flex flex-col items-center gap-5 text-center">
        <div className="flex gap-3">
          <div className="h-12 w-12 rounded-2xl bg-[var(--accent)]/10 flex items-center justify-center ring-1 ring-[var(--accent)]/20">
            <Building2 className="h-5 w-5 text-[var(--accent)]" />
          </div>
          <div className="h-12 w-12 rounded-2xl bg-[var(--success)]/10 flex items-center justify-center ring-1 ring-[var(--success)]/20">
            <Code2 className="h-5 w-5 text-[var(--success)]" />
          </div>
        </div>
        <div>
          <h3 className="text-base font-semibold text-[var(--text-primary)] mb-1.5">
            Welcome! Let's get started
          </h3>
          <p className="text-sm text-[var(--text-muted)] max-w-xs leading-relaxed">
            Track companies, solve DSA problems, and monitor your placement readiness.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-center">
          <Button asChild size="sm">
            <Link to="/companies"><Plus className="h-4 w-4" />Add Company</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to="/dsa"><Code2 className="h-4 w-4" />Log DSA Problem</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user } = useAuth()
  const firstName = user?.full_name?.split(' ')[0] ?? 'there'

  const {
    data: summary, isLoading: loadingSummary, isError: errorSummary,
  } = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.getSummary })

  const {
    data: streak, isLoading: loadingStreak,
  } = useQuery({ queryKey: ['dashboard-streak'], queryFn: dashboardApi.getStreak })

  const {
    data: weekly, isLoading: loadingWeekly,
  } = useQuery({ queryKey: ['dashboard-weekly'], queryFn: () => dashboardApi.getWeeklyProductivity(12) })

  const {
    data: dsaStats,
  } = useQuery({ queryKey: ['dsa-stats'], queryFn: dsaApi.getStats })

  const isNewUser = !loadingSummary && !errorSummary &&
    summary?.overall_progress === 0 &&
    summary?.active_companies_count === 0 &&
    (dsaStats?.overall_total ?? 0) === 0

  // Derived: deadline badge variant only
  const deadlineBadgeVariant = (deadline: string): 'destructive' | 'warning' | 'secondary' => {
    const days = differenceInCalendarDays(new Date(deadline), new Date())
    if (days < 3) return 'destructive'
    if (days < 7) return 'warning'
    return 'secondary'
  }

  // Donut data for topics
  const donutData = useMemo(() =>
    (summary?.charts.topic_distribution ?? []).slice(0, 6).map(t => ({
      name: t.tag,
      value: t.solved,
      total: t.total,
    })),
    [summary]
  )

  const donutColors = [
    'var(--accent)', 'var(--success)', 'var(--warning)',
    'var(--danger)', 'var(--text-muted)', 'var(--accent)',
  ]

  if (errorSummary) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Dashboard</h1>
        <ErrorCard message="Could not load dashboard data. Check your connection or try refreshing." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
            Hey, {firstName} 👋
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            Here's your placement prep overview
          </p>
        </div>
      </div>

      {/* New user empty state */}
      {isNewUser && <NewUserEmpty />}

      {/* Top row: readiness ring + stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Readiness ring */}
        <Card className="sm:col-span-1 flex items-center justify-center py-2">
          <CardContent className="pt-4 pb-2">
            {loadingSummary
              ? <Skeleton className="h-28 w-28 rounded-full mx-auto" />
              : <ReadinessRing pct={summary?.overall_progress ?? 0} loading={loadingSummary} />
            }
          </CardContent>
        </Card>

        {/* 4 stat cards */}
        {loadingSummary
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
          : (
            <>
              <StatCard
                icon={<Code2 className="h-4 w-4" />}
                label="Problems Solved"
                value={dsaStats?.overall_solved ?? 0}
                sub={`of ${dsaStats?.overall_total ?? 0} total`}
                color="var(--accent)"
              />
              <StatCard
                icon={<CheckSquare className="h-4 w-4" />}
                label="Checklist Done"
                value={`${(summary?.checklist_completion_pct ?? 0).toFixed(0)}%`}
                sub="across all companies"
                color="var(--success)"
              />
              <StatCard
                icon={<Building2 className="h-4 w-4" />}
                label="Companies"
                value={summary?.active_companies_count ?? 0}
                sub="being tracked"
                color="var(--warning)"
              />
              <StatCard
                icon={<FileText className="h-4 w-4" />}
                label="Resume Score"
                value={`${(summary?.resume_readiness_score ?? 0).toFixed(0)}%`}
                sub="readiness"
                color="var(--danger)"
              />
            </>
          )
        }
      </div>

      {/* Charts row 1: heatmap + weekly bar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">DSA Activity (12 weeks)</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <Skeleton className="h-24" />
              : <CalendarHeatmap data={summary?.charts.dsa_solved_over_time ?? []} />
            }
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Weekly Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingWeekly
              ? <Skeleton className="h-32" />
              : weekly && weekly.weeks.length > 0
              ? (
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={weekly.weeks} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="iso_week" tick={AXIS_TICK_STYLE} tickFormatter={w => w.split('-W')[1] ? `W${w.split('-W')[1]}` : w} interval="preserveStartEnd" />
                    <YAxis tick={AXIS_TICK_STYLE} allowDecimals={false} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="activity_count" fill="var(--accent)" radius={[4, 4, 0, 0]} name="Activities" />
                  </BarChart>
                </ResponsiveContainer>
              )
              : <p className="text-xs text-[var(--text-muted)] py-4 text-center">No activity data yet</p>
            }
          </CardContent>
        </Card>
      </div>

      {/* Charts row 2: topics donut + company readiness bars */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Topics donut */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">DSA Topics</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <Skeleton className="h-36" />
              : donutData.length > 0
              ? (
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width={140} height={140}>
                    <PieChart>
                      <Pie
                        data={donutData}
                        cx="50%" cy="50%"
                        innerRadius={42} outerRadius={62}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {donutData.map((_, i) => (
                          <Cell key={i} fill={donutColors[i % donutColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, name) => [`${v} solved`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-1.5 flex-1 min-w-0">
                    {donutData.map((d, i) => (
                      <div key={d.name} className="flex items-center gap-2 text-xs">
                        <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: donutColors[i % donutColors.length] }} />
                        <span className="truncate text-[var(--text-secondary)]">{d.name}</span>
                        <span className="ml-auto text-[var(--text-muted)] shrink-0">{d.value}/{d.total}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No DSA topics yet</p>
            }
          </CardContent>
        </Card>

        {/* Company readiness bars */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Company Readiness</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <Skeleton className="h-36" />
              : (summary?.charts.company_readiness ?? []).length > 0
              ? (
                <div className="space-y-2.5">
                  {summary!.charts.company_readiness.slice(0, 5).map(c => (
                    <div key={c.company_id}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--text-secondary)] truncate">{c.company_name}</span>
                        <span className="text-[var(--text-muted)] ml-2 shrink-0">{c.checklist_progress_pct.toFixed(0)}%</span>
                      </div>
                      <Progress value={c.checklist_progress_pct} className="h-1.5" />
                    </div>
                  ))}
                </div>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No tracked companies yet</p>
            }
          </CardContent>
        </Card>
      </div>

      {/* Bottom row: deadlines + streak + recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Streak */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Flame className="h-4 w-4 text-[var(--warning)]" />
              Daily Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingStreak
              ? <Skeleton className="h-14" />
              : (
                <div className="space-y-1">
                  <p className="text-3xl font-bold text-[var(--text-primary)]">
                    {streak?.current_streak ?? 0}
                    <span className="text-base font-normal text-[var(--text-muted)] ml-1">days</span>
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    Longest: {streak?.longest_streak ?? 0} days
                    {streak?.today_active && (
                      <Badge variant="success" className="ml-2 text-[10px] py-0">Active today</Badge>
                    )}
                  </p>
                  {streak?.last_active_date && (
                    <p className="text-xs text-[var(--text-muted)]">
                      Last active: {format(new Date(streak.last_active_date), 'MMM d')}
                    </p>
                  )}
                </div>
              )
            }
          </CardContent>
        </Card>

        {/* Upcoming deadlines */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Upcoming Deadlines</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loadingSummary
              ? <Skeleton className="h-16" />
              : (summary?.upcoming_deadlines ?? []).length === 0
              ? <p className="text-xs text-[var(--text-muted)]">No upcoming deadlines</p>
              : summary!.upcoming_deadlines.slice(0, 4).map(d => {
                  const days = differenceInCalendarDays(new Date(d.deadline), new Date())
                  return (
                    <div key={d.user_company_id} className="flex items-center justify-between text-xs">
                      <span className="text-[var(--text-primary)] truncate flex-1">{d.company_name}</span>
                      <Badge variant={deadlineBadgeVariant(d.deadline)} className="ml-2 text-[10px] py-0 shrink-0">
                        {days < 0 ? `${Math.abs(days)}d late` : days === 0 ? 'today' : `${days}d`}
                      </Badge>
                    </div>
                  )
                })
            }
          </CardContent>
        </Card>

        {/* Recent activity */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-5" />)}</div>
              : (summary?.recent_activity ?? []).length === 0
              ? <p className="text-xs text-[var(--text-muted)]">No activity yet — start tracking!</p>
              : (
                <div className="space-y-2">
                  {summary!.recent_activity.slice(0, 6).map(a => (
                    <div key={a.id} className="flex items-start gap-2 text-xs">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />
                      <span className="text-[var(--text-primary)] flex-1 leading-snug">{a.action}</span>
                      <span className="text-[var(--text-muted)] shrink-0 whitespace-nowrap">
                        {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  ))}
                </div>
              )
            }
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({
  icon, label, value, sub, color,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  sub: string
  color: string
}) {
  return (
    <Card className="hover:shadow-[0_4px_16px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.05)] transition-shadow duration-200">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-2.5 mb-3">
          <div
            className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${color}18`, color }}
          >
            {icon}
          </div>
          <span className="text-xs font-medium text-[var(--text-muted)]">{label}</span>
        </div>
        <p className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">{value}</p>
        <p className="text-xs text-[var(--text-muted)] mt-0.5">{sub}</p>
      </CardContent>
    </Card>
  )
}
