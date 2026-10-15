import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  Code2,
  Flame,
  Target,
  BriefcaseBusiness,
  ArrowRight,
} from "lucide-react";
import { eachDayOfInterval, format, subDays } from "date-fns";
import { dashboardApi } from "@/api/dashboard";
import { dsaApi } from "@/api/dsa";
import { STAGES, workspaceApi } from "@/api/workspace";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AXIS_TICK_STYLE, TOOLTIP_STYLE } from "@/lib/chartTheme";

function LoadState({
  pending,
  error,
  retry,
  children,
}: {
  pending: boolean;
  error: boolean;
  retry: () => void;
  children: React.ReactNode;
}) {
  if (pending) return <Skeleton className="h-40 rounded-xl" />;
  if (error)
    return (
      <div className="analytics-empty" role="status">
        <p>This section couldn’t load.</p>
        <Button variant="outline" size="sm" onClick={retry}>
          Try again
        </Button>
      </div>
    );
  return children;
}
function Meter({ value, label }: { value: number; label: string }) {
  return (
    <div
      className="analytics-meter"
      role="progressbar"
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(28);
  const [allTopics, setAllTopics] = useState(false);
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardApi.getSummary,
  });
  const streak = useQuery({
    queryKey: ["dashboard-streak"],
    queryFn: dashboardApi.getStreak,
  });
  const dsa = useQuery({ queryKey: ["dsa-stats"], queryFn: dsaApi.getStats });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: workspaceApi.applications,
  });
  const counts = new Map(
    (summary.data?.charts.dsa_solved_over_time ?? []).map((p) => [
      p.date,
      p.count,
    ]),
  );
  const practice = eachDayOfInterval({
    start: subDays(new Date(), days - 1),
    end: new Date(),
  }).map((date) => ({
    date: format(date, "yyyy-MM-dd"),
    count: counts.get(format(date, "yyyy-MM-dd")) ?? 0,
  }));
  const solved = practice.reduce((sum, day) => sum + day.count, 0);
  const activeDays = practice.filter((day) => day.count > 0).length;
  const topics = [...(summary.data?.charts.topic_distribution ?? [])].sort(
    (a, b) =>
      (a.total ? a.solved / a.total : 0) - (b.total ? b.solved / b.total : 0),
  );
  const components = [
    {
      label: "Practice completion",
      value: summary.data?.dsa_completion_pct ?? 0,
      weight: 50,
      to: "/dsa",
      action: "Open practice",
    },
    {
      label: "Resume readiness",
      value: summary.data?.resume_readiness_score ?? 0,
      weight: 30,
      to: "/resumes",
      action: "Review resume",
    },
    {
      label: "Company checklists",
      value: summary.data?.checklist_completion_pct ?? 0,
      weight: 20,
      to: "/companies",
      action: "Open checklists",
    },
  ];
  const focus = [...components].sort((a, b) => a.value - b.value)[0];
  const progress = Math.round(summary.data?.overall_progress ?? 0);
  const metric = (
    query: { isPending: boolean; isError: boolean },
    value: number,
  ) => (query.isPending || query.isError ? "—" : value);
  return (
    <div className="workspace-page analytics-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">YOUR PROGRESS, IN PERSPECTIVE</p>
          <h1>
            See how far you’ve come<span className="heading-dot">.</span>
          </h1>
          <p>
            Find your rhythm, spot the gaps, and make your next session count.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/dsa">
            Continue practicing <ArrowUpRight size={16} />
          </Link>
        </Button>
      </header>

      <div className="analytics-overview">
        <section className="workspace-panel analytics-score">
          <p className="eyebrow">PREPARATION SNAPSHOT · ALL TIME</p>
          <LoadState
            pending={summary.isPending}
            error={summary.isError}
            retry={() => void summary.refetch()}
          >
            <div className="analytics-score-body">
              <div
                className="analytics-ring"
                style={{
                  background: `conic-gradient(var(--accent) ${progress * 3.6}deg, var(--border) 0deg)`,
                }}
              >
                <div>
                  <strong>
                    {progress}
                    <small>%</small>
                  </strong>
                  <span>Overall progress</span>
                </div>
              </div>
              <div className="analytics-score-copy">
                <h2>Small steps. Lasting progress.</h2>
                <p>
                  Your tracked practice, resume readiness, and checklists in one
                  view. This is a preparation guide, not a hiring prediction.
                </p>
                <a href="#progress-breakdown">
                  How this is calculated <ArrowRight size={14} />
                </a>
              </div>
            </div>
          </LoadState>
        </section>
        <section className="analytics-focus">
          <Target size={22} />
          <p className="eyebrow">WHERE TO FOCUS</p>
          <h2>
            {summary.isPending
              ? "Finding your next step…"
              : summary.isError
                ? "Your next step starts here."
                : focus.value >= 100
                  ? "Keep your preparation fresh."
                  : focus.label}
          </h2>
          <p>
            {summary.isError
              ? "Reload your preparation snapshot to see a suggested focus."
              : focus.value >= 100
                ? "Revisit a challenge or tailor your resume to a new role."
                : "Your lowest completion area is a useful place to start your next focused session."}
          </p>
          <Link to={summary.isError ? "/dashboard" : focus.to}>
            {summary.isError ? "Back to Today" : focus.action}
            <ArrowUpRight size={16} />
          </Link>
        </section>
      </div>

      <div className="analytics-metrics">
        {[
          {
            icon: Code2,
            label: "Problems solved",
            value: metric(dsa, dsa.data?.overall_solved ?? 0),
            detail: "All-time practice",
          },
          {
            icon: Flame,
            label: "Current streak",
            value: metric(streak, streak.data?.current_streak ?? 0),
            detail: `Days of tracked activity · best ${metric(streak, streak.data?.longest_streak ?? 0)}`,
          },
          {
            icon: BriefcaseBusiness,
            label: "Active applications",
            value: metric(
              applications,
              (applications.data ?? []).filter(
                (a) => !["Offer", "Closed"].includes(a.stage),
              ).length,
            ),
            detail: "Saved through interview",
          },
        ].map(({ icon: Icon, ...item }) => (
          <div className="workspace-panel analytics-stat" key={item.label}>
            <div>
              <span>{item.label}</span>
              <Icon size={18} />
            </div>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </div>
        ))}
      </div>

      <section className="workspace-panel analytics-section">
        <div className="analytics-section-heading">
          <div>
            <p className="eyebrow">BUILD A CONSISTENT HABIT</p>
            <h2>Practice momentum</h2>
            <p>Problems solved per day, including days with no solves.</p>
          </div>
          <div
            className="analytics-range"
            role="group"
            aria-label="Practice date range"
          >
            {[7, 28, 90].map((range) => (
              <button
                key={range}
                aria-pressed={days === range}
                onClick={() => setDays(range)}
              >
                {range} days
              </button>
            ))}
          </div>
        </div>
        <LoadState
          pending={summary.isPending}
          error={summary.isError}
          retry={() => void summary.refetch()}
        >
          <div className="analytics-chart-summary">
            <strong>
              {solved} <span>solved</span>
            </strong>
            <span>
              {activeDays} of {days} days with practice
            </span>
            <span>
              {format(subDays(new Date(), days - 1), "MMM d")} –{" "}
              {format(new Date(), "MMM d, yyyy")}
            </span>
          </div>
          {solved ? (
            <div
              className="analytics-chart"
              role="img"
              aria-label={`${solved} problems solved across ${activeDays} practice days in the last ${days} days`}
            >
              <ResponsiveContainer width="100%" height={230}>
                <AreaChart
                  data={practice}
                  margin={{ top: 12, right: 12, left: -24, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="analytics-practice-fill"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="var(--accent)"
                        stopOpacity={0.25}
                      />
                      <stop
                        offset="100%"
                        stopColor="var(--accent)"
                        stopOpacity={0.01}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    vertical={false}
                    stroke="var(--border)"
                    strokeDasharray="4 4"
                  />
                  <XAxis
                    dataKey="date"
                    tick={AXIS_TICK_STYLE}
                    tickFormatter={(date) =>
                      format(new Date(`${date}T12:00:00`), "MMM d")
                    }
                    minTickGap={32}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={AXIS_TICK_STYLE}
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(date) =>
                      format(new Date(`${date}T12:00:00`), "EEE, MMM d")
                    }
                  />
                  <Area
                    type="linear"
                    dataKey="count"
                    name="Problems solved"
                    stroke="var(--accent)"
                    strokeWidth={2.5}
                    fill="url(#analytics-practice-fill)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="analytics-empty">
              <Code2 size={24} />
              <h3>A fresh window to build momentum</h3>
              <p>
                No problems solved in these {days} days. Your next solution
                starts the chart.
              </p>
              <Link to="/dsa">
                Start a practice session <ArrowUpRight size={14} />
              </Link>
            </div>
          )}
        </LoadState>
      </section>

      <div className="analytics-two-column">
        <section
          id="progress-breakdown"
          className="workspace-panel analytics-section"
        >
          <div className="analytics-section-heading">
            <div>
              <p className="eyebrow">THE BIGGER PICTURE</p>
              <h2>What makes up your progress</h2>
              <p>Completion in each area, weighted into your overall score.</p>
            </div>
          </div>
          <LoadState
            pending={summary.isPending}
            error={summary.isError}
            retry={() => void summary.refetch()}
          >
            <div className="analytics-breakdown">
              {components.map((item) => (
                <Link key={item.label} to={item.to}>
                  <div>
                    <span>{item.label}</span>
                    <strong>
                      {Math.round(item.value)}% <ArrowUpRight size={14} />
                    </strong>
                  </div>
                  <Meter label={item.label} value={item.value} />
                  <p>
                    {item.weight}% weight ·{" "}
                    {((item.value * item.weight) / 100).toFixed(1)} points
                    contributed
                  </p>
                </Link>
              ))}
            </div>
          </LoadState>
        </section>
        <section className="workspace-panel analytics-section">
          <div className="analytics-section-heading">
            <div>
              <p className="eyebrow">OPPORTUNITIES IN MOTION</p>
              <h2>Your application pipeline</h2>
              <p>Current stages across all saved roles.</p>
            </div>
            <Link to="/applications" aria-label="Open applications">
              <ArrowUpRight size={18} />
            </Link>
          </div>
          <LoadState
            pending={applications.isPending}
            error={applications.isError}
            retry={() => void applications.refetch()}
          >
            {applications.data?.length ? (
              <div className="analytics-stages">
                {STAGES.map((stage) => {
                  const count = applications.data.filter(
                    (a) => a.stage === stage,
                  ).length;
                  return (
                    <div key={stage}>
                      <span>{stage}</span>
                      <Meter
                        label={`${stage} share of applications`}
                        value={(count / applications.data.length) * 100}
                      />
                      <strong>{count}</strong>
                    </div>
                  );
                })}
                <p>
                  Stage counts show where roles are now, not conversion rates.
                </p>
              </div>
            ) : (
              <div className="analytics-empty">
                <BriefcaseBusiness size={24} />
                <h3>Your pipeline starts with one role</h3>
                <Link to="/applications?new=1">
                  Add an application <ArrowUpRight size={14} />
                </Link>
              </div>
            )}
          </LoadState>
        </section>
      </div>

      <div className="analytics-two-column">
        <section className="workspace-panel analytics-section">
          <div className="analytics-section-heading">
            <div>
              <p className="eyebrow">PRACTICE WITH PURPOSE</p>
              <h2>Topic coverage</h2>
              <p>Lowest completion first, so gaps are easier to spot.</p>
            </div>
          </div>
          <LoadState
            pending={summary.isPending}
            error={summary.isError}
            retry={() => void summary.refetch()}
          >
            {topics.length ? (
              <>
                <div className="analytics-topics">
                  {topics.slice(0, allTopics ? undefined : 6).map((topic) => (
                    <div key={topic.tag}>
                      <div>
                        <span>{topic.tag}</span>
                        <span>
                          {topic.solved} / {topic.total} solved
                        </span>
                      </div>
                      <Meter
                        value={
                          topic.total ? (topic.solved / topic.total) * 100 : 0
                        }
                        label={topic.tag}
                      />
                    </div>
                  ))}
                </div>
                {topics.length > 6 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-4"
                    onClick={() => setAllTopics(!allTopics)}
                  >
                    {allTopics
                      ? "Show fewer topics"
                      : `Show all ${topics.length} topics`}
                  </Button>
                )}
                <p className="analytics-footnote">
                  A problem can contribute to more than one topic.
                </p>
              </>
            ) : (
              <div className="analytics-empty">
                <p>Add tagged problems to see your topic coverage.</p>
                <Link to="/dsa">
                  Explore practice <ArrowUpRight size={14} />
                </Link>
              </div>
            )}
          </LoadState>
        </section>
        <section className="workspace-panel analytics-section">
          <div className="analytics-section-heading">
            <div>
              <p className="eyebrow">BUILD YOUR RANGE</p>
              <h2>Practice by difficulty</h2>
              <p>Solved problems out of your tracked collection.</p>
            </div>
          </div>
          <LoadState
            pending={dsa.isPending}
            error={dsa.isError}
            retry={() => void dsa.refetch()}
          >
            {dsa.data?.difficulty_wise.some((item) => item.total > 0) ? (
              <div className="analytics-difficulty">
                {dsa.data.difficulty_wise.map((item) => (
                  <div key={item.difficulty}>
                    <div>
                      <span
                        className={`analytics-difficulty-label difficulty-${item.difficulty.toLowerCase()}`}
                      >
                        {item.difficulty}
                      </span>
                      <strong>
                        {item.solved}
                        <small> / {item.total}</small>
                      </strong>
                    </div>
                    <Meter
                      label={`${item.difficulty} completion`}
                      value={item.total ? (item.solved / item.total) * 100 : 0}
                    />
                    <p>{Math.max(0, item.total - item.solved)} remaining</p>
                  </div>
                ))}
                <Link to="/dsa">
                  Choose your next challenge <ArrowUpRight size={15} />
                </Link>
              </div>
            ) : (
              <div className="analytics-empty">
                <p>
                  Your difficulty mix will appear as you add practice problems.
                </p>
                <Link to="/dsa">
                  Add your first problem <ArrowUpRight size={14} />
                </Link>
              </div>
            )}
          </LoadState>
        </section>
      </div>
      <section className="workspace-panel analytics-section">
        <div className="analytics-section-heading">
          <div>
            <p className="eyebrow">PREPARE FOR THE COMPANY</p>
            <h2>Company checklist progress</h2>
            <p>Completed checklist items for each tracked company.</p>
          </div>
          <Link to="/companies" aria-label="Open company library">
            <ArrowUpRight size={18} />
          </Link>
        </div>
        <LoadState
          pending={summary.isPending}
          error={summary.isError}
          retry={() => void summary.refetch()}
        >
          {summary.data?.charts.company_readiness.length ? (
            <div className="analytics-company-grid">
              {summary.data.charts.company_readiness.map((company) => (
                <Link
                  to={`/companies/${company.company_id}`}
                  key={company.user_company_id}
                >
                  <div>
                    <span>{company.company_name}</span>
                    <strong>
                      {Math.round(company.checklist_progress_pct)}%{" "}
                      <ArrowUpRight size={14} />
                    </strong>
                  </div>
                  <Meter
                    value={company.checklist_progress_pct}
                    label={`${company.company_name} checklist`}
                  />
                </Link>
              ))}
            </div>
          ) : (
            <div className="analytics-empty">
              <p>
                Track a company and complete checklist items to see progress
                here.
              </p>
              <Link to="/companies">
                Explore companies <ArrowUpRight size={14} />
              </Link>
            </div>
          )}
        </LoadState>
      </section>
    </div>
  );
}
