import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, Cell,
  PieChart, Pie, Tooltip, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts'
import { AlertCircle, Code2, Building2, CheckSquare, Flame } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { dashboardApi } from '@/api/dashboard'
import { dsaApi } from '@/api/dsa'
import { TOOLTIP_STYLE, AXIS_TICK_STYLE } from '@/lib/chartTheme'
import { format, formatDistanceToNow, subDays, eachDayOfInterval } from 'date-fns'

// ─── Streak graph — shows consecutive-day breaks visually ─────────────────────
function StreakGraph({ data }: { data: { date: string; count: number }[] }) {
  const today = new Date()
  const days = eachDayOfInterval({ start: subDays(today, 27), end: today }) // 4 weeks

  const countMap = new Map(data.map(d => [d.date, d.count]))

  const chartData = days.map(d => ({
    date: format(d, 'MMM d'),
    fullDate: format(d, 'yyyy-MM-dd'),
    count: countMap.get(format(d, 'yyyy-MM-dd')) ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="date" tick={AXIS_TICK_STYLE} interval={6} />
        <YAxis tick={AXIS_TICK_STYLE} allowDecimals={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v) => [v ?? 0, 'Activities'] as [number, string]}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]} name="Activities">
          {chartData.map((d, i) => (
            <Cell
              key={i}
              fill={d.count === 0 ? 'var(--border)' : 'var(--accent)'}
              opacity={d.count === 0 ? 0.4 : 1}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
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

// ─── Timeline feed ────────────────────────────────────────────────────────────
const EVENT_COLORS: Record<string, string> = {
  dsa_solved: 'var(--success)',
  checklist_item_completed: 'var(--accent)',
  company_status_changed: 'var(--warning)',
}
const EVENT_ICONS: Record<string, React.ReactNode> = {
  dsa_solved: <Code2 className="h-3 w-3" />,
  checklist_item_completed: <CheckSquare className="h-3 w-3" />,
  company_status_changed: <Building2 className="h-3 w-3" />,
}

export default function AnalyticsPage() {
  const {
    data: summary, isLoading: loadingSummary, isError: errorSummary,
  } = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.getSummary })

  const {
    data: streak, isLoading: loadingStreak,
  } = useQuery({ queryKey: ['dashboard-streak'], queryFn: dashboardApi.getStreak })

  const {
    data: weekly, isLoading: loadingWeekly,
  } = useQuery({ queryKey: ['dashboard-weekly'], queryFn: () => dashboardApi.getWeeklyProductivity(16) })

  const {
    data: timeline, isLoading: loadingTimeline,
  } = useQuery({ queryKey: ['dashboard-timeline'], queryFn: () => dashboardApi.getTimeline(50) })

  const {
    data: dsaStats, isLoading: loadingDsa,
  } = useQuery({ queryKey: ['dsa-stats'], queryFn: dsaApi.getStats })

  // Donut: topic distribution
  const topicData = useMemo(() =>
    (summary?.charts.topic_distribution ?? []).slice(0, 8).map(t => ({
      name: t.tag,
      solved: t.solved,
      total: t.total,
      pct: t.total > 0 ? Math.round((t.solved / t.total) * 100) : 0,
    })),
    [summary]
  )

  const donutColors = [
    'var(--accent)', 'var(--success)', 'var(--warning)',
    'var(--danger)', 'var(--text-secondary)', 'var(--accent)',
    'var(--success)', 'var(--warning)',
  ]

  // Difficulty breakdown
  const diffData = dsaStats?.difficulty_wise.map(d => ({
    name: d.difficulty,
    solved: d.solved,
    total: d.total - d.solved,
  })) ?? []
  const diffColors: Record<string, string> = {
    Easy: 'var(--success)',
    Medium: 'var(--warning)',
    Hard: 'var(--danger)',
  }

  // Solved-over-time area chart
  const solvedOverTime = useMemo(() => {
    const raw = summary?.charts.dsa_solved_over_time ?? []
    // Compute cumulative
    let running = 0
    return raw.map(p => ({ date: p.date, count: p.count, cumulative: (running += p.count) }))
  }, [summary])

  if (errorSummary) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Analytics</h1>
        <ErrorCard message="Could not load analytics data. Check your connection or try refreshing." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Analytics</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">Deep-dive into your preparation progress</p>
      </div>

      {/* Streak summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {loadingStreak
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
          : (
            <>
              <Card><CardContent className="pt-4 pb-4 text-center">
                <Flame className="h-5 w-5 text-[var(--warning)] mx-auto mb-1" />
                <p className="text-2xl font-bold text-[var(--text-primary)]">{streak?.current_streak ?? 0}</p>
                <p className="text-xs text-[var(--text-muted)]">Current streak</p>
              </CardContent></Card>
              <Card><CardContent className="pt-4 pb-4 text-center">
                <p className="text-2xl font-bold text-[var(--text-primary)]">{streak?.longest_streak ?? 0}</p>
                <p className="text-xs text-[var(--text-muted)]">Longest streak</p>
              </CardContent></Card>
              <Card><CardContent className="pt-4 pb-4 text-center">
                <p className="text-2xl font-bold text-[var(--text-primary)]">{dsaStats?.overall_solved ?? 0}</p>
                <p className="text-xs text-[var(--text-muted)]">Problems solved</p>
              </CardContent></Card>
              <Card><CardContent className="pt-4 pb-4 text-center">
                <p className="text-2xl font-bold text-[var(--text-primary)]">{weekly?.total_activities ?? 0}</p>
                <p className="text-xs text-[var(--text-muted)]">Total activities</p>
              </CardContent></Card>
            </>
          )
        }
      </div>

      {/* Streak graph — shows gaps as grey bars */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Flame className="h-4 w-4 text-[var(--warning)]" />
            Daily Activity (last 28 days)
            <span className="text-[10px] text-[var(--text-muted)] font-normal ml-1">— gaps are missing days</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSummary
            ? <Skeleton className="h-32" />
            : <StreakGraph data={summary?.charts.dsa_solved_over_time ?? []} />
          }
        </CardContent>
      </Card>

      {/* Solved over time area + weekly productivity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Solved Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <Skeleton className="h-36" />
              : solvedOverTime.length > 0
              ? (
                <ResponsiveContainer width="100%" height={140}>
                  <AreaChart data={solvedOverTime} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="accentGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" tick={AXIS_TICK_STYLE} interval="preserveStartEnd" />
                    <YAxis tick={AXIS_TICK_STYLE} allowDecimals={false} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Area type="monotone" dataKey="cumulative" stroke="var(--accent)" fill="url(#accentGrad)" strokeWidth={2} name="Total solved" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No solved problems yet</p>
            }
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Weekly Productivity</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingWeekly
              ? <Skeleton className="h-36" />
              : weekly && weekly.weeks.length > 0
              ? (
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={weekly.weeks} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="iso_week" tick={AXIS_TICK_STYLE} tickFormatter={w => `W${w.split('-W')[1] ?? w}`} interval="preserveStartEnd" />
                    <YAxis tick={AXIS_TICK_STYLE} allowDecimals={false} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [v, 'Activities']} />
                    <Bar dataKey="activity_count" fill="var(--success)" radius={[4, 4, 0, 0]} name="Activities" />
                  </BarChart>
                </ResponsiveContainer>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No activity data yet</p>
            }
          </CardContent>
        </Card>
      </div>

      {/* Topic distribution + difficulty breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">DSA Topic Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingSummary
              ? <Skeleton className="h-48" />
              : topicData.length > 0
              ? (
                <div className="flex gap-4">
                  <ResponsiveContainer width={140} height={160}>
                    <PieChart>
                      <Pie data={topicData} cx="50%" cy="50%" innerRadius={40} outerRadius={62} dataKey="solved" strokeWidth={0}>
                        {topicData.map((_, i) => <Cell key={i} fill={donutColors[i % donutColors.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, name) => [`${v} solved`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-2 min-w-0">
                    {topicData.map((t, i) => (
                      <div key={t.name}>
                        <div className="flex items-center gap-1.5 text-xs mb-0.5">
                          <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: donutColors[i % donutColors.length] }} />
                          <span className="truncate text-[var(--text-secondary)]">{t.name}</span>
                          <span className="ml-auto text-[var(--text-muted)] shrink-0">{t.pct}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-[var(--border)] overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${t.pct}%`, backgroundColor: donutColors[i % donutColors.length] }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No DSA topics yet</p>
            }
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Difficulty Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingDsa
              ? <Skeleton className="h-48" />
              : diffData.length > 0
              ? (
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={diffData} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                    <XAxis type="number" tick={AXIS_TICK_STYLE} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" tick={AXIS_TICK_STYLE} width={50} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text-muted)' }} />
                    <Bar dataKey="solved" name="Solved" stackId="a" radius={[0, 0, 0, 0]}>
                      {diffData.map((d) => (
                        <Cell key={d.name} fill={diffColors[d.name] ?? 'var(--accent)'} />
                      ))}
                    </Bar>
                    <Bar dataKey="total" name="Remaining" stackId="a" fill="var(--border)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )
              : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No problems logged yet</p>
            }
          </CardContent>
        </Card>
      </div>

      {/* Company readiness comparison */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Company Readiness Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSummary
            ? <Skeleton className="h-48" />
            : (summary?.charts.company_readiness ?? []).length > 0
            ? (
              <ResponsiveContainer width="100%" height={Math.min(200, 40 * summary!.charts.company_readiness.length + 40)}>
                <BarChart
                  data={summary!.charts.company_readiness.map(c => ({ name: c.company_name, pct: c.checklist_progress_pct }))}
                  layout="vertical"
                  margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={AXIS_TICK_STYLE} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="name" tick={AXIS_TICK_STYLE} width={80} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${Number(v ?? 0).toFixed(0)}%`, 'Readiness'] as [string, string]} />
                  <Bar dataKey="pct" fill="var(--accent)" radius={[0, 4, 4, 0]} name="Readiness" />
                </BarChart>
              </ResponsiveContainer>
            )
            : <p className="text-xs text-[var(--text-muted)] py-8 text-center">No tracked companies yet</p>
          }
        </CardContent>
      </Card>

      {/* Merged timeline */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Preparation Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingTimeline
            ? <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8" />)}</div>
            : (timeline?.entries ?? []).length === 0
            ? <p className="text-xs text-[var(--text-muted)] py-4 text-center">No timeline entries yet — start solving problems and tracking companies.</p>
            : (
              <div className="space-y-3">
                {timeline!.entries.map((e, i) => (
                  <div key={i} className="flex items-start gap-3 text-xs">
                    <div
                      className="mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor: (EVENT_COLORS[e.event_type] ?? 'var(--accent)') + '20',
                        color: EVENT_COLORS[e.event_type] ?? 'var(--accent)',
                      }}
                    >
                      {EVENT_ICONS[e.event_type] ?? <Code2 className="h-3 w-3" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[var(--text-primary)] leading-snug">{e.action}</p>
                      <p className="text-[var(--text-muted)]">{e.entity_type}</p>
                    </div>
                    <Badge
                      variant="secondary"
                      className="text-[10px] py-0 shrink-0"
                      style={{ color: EVENT_COLORS[e.event_type] ?? 'var(--accent)' }}
                    >
                      {e.event_type.replace(/_/g, ' ')}
                    </Badge>
                    <span className="text-[var(--text-muted)] shrink-0 whitespace-nowrap">
                      {formatDistanceToNow(new Date(e.timestamp), { addSuffix: true })}
                    </span>
                  </div>
                ))}
              </div>
            )
          }
        </CardContent>
      </Card>
    </div>
  )
}
