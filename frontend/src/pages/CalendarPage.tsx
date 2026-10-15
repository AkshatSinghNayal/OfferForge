import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  format, startOfMonth, endOfMonth, eachDayOfInterval,
  isSameDay, addMonths, subMonths, isToday, parseISO, startOfDay,
} from 'date-fns'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { workspaceApi, type Application } from '@/api/workspace'

export default function CalendarPage() {
  const [month, setMonth] = useState(new Date())
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['applications'],
    queryFn: workspaceApi.applications,
  })

  // Build a map of date-string → companies with deadlines on that day
  const deadlineMap = new Map<string, Application[]>()
  data?.filter(a => !['Closed', 'Offer'].includes(a.stage)).forEach(tc => {
    if (!tc.deadline) return
    const key = tc.deadline
    const existing = deadlineMap.get(key) ?? []
    deadlineMap.set(key, [...existing, tc])
  })

  const days = eachDayOfInterval({ start: startOfMonth(month), end: endOfMonth(month) })
  const selectedItems = selectedDay
    ? (deadlineMap.get(format(selectedDay, 'yyyy-MM-dd')) ?? [])
    : []

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Calendar</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">Your application deadlines, in one place</p>
      </div>

      {isError && <div role="alert">Deadlines couldn’t load. <Button variant="link" onClick={() => refetch()}>Try again</Button></div>}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Month grid */}
        <Card className="flex-1">
          <CardContent className="pt-4">
            {/* Month navigation */}
            <div className="flex items-center justify-between mb-4">
              <Button variant="ghost" size="icon" aria-label="Previous month" onClick={() => setMonth(m => subMonths(m, 1))}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                {format(month, 'MMMM yyyy')}
              </h2>
              <Button variant="ghost" size="icon" aria-label="Next month" onClick={() => setMonth(m => addMonths(m, 1))}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Day-of-week headers */}
            <div className="grid grid-cols-7 mb-1">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                <div key={d} className="text-center text-[10px] text-[var(--text-muted)] pb-1">{d}</div>
              ))}
            </div>

            {/* Day cells */}
            {isLoading ? (
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: 35 }).map((_, i) => <Skeleton key={i} className="h-10 rounded-xl" />)}
              </div>
            ) : (
              <div className="grid grid-cols-7 gap-1">
                {/* Leading empty cells for the first row */}
                {Array.from({ length: days[0].getDay() }).map((_, i) => <div key={`e${i}`} />)}
                {days.map(day => {
                  const key = format(day, 'yyyy-MM-dd')
                  const events = deadlineMap.get(key) ?? []
                  const isSelected = selectedDay && isSameDay(day, selectedDay)
                  const todayDay = isToday(day)
                  return (
                    <button
                      key={key}
                      onClick={() => setSelectedDay(isSameDay(day, selectedDay ?? new Date(0)) ? null : day)}
                      className={`relative h-10 rounded-xl text-xs flex flex-col items-center justify-center transition-colors ${
                        isSelected
                          ? 'bg-[var(--accent)] text-white'
                          : todayDay
                          ? 'bg-[var(--accent)]/15 text-[var(--accent)]'
                          : 'hover:bg-[var(--card)] text-[var(--text-primary)]'
                      }`}
                    >
                      {day.getDate()}
                      {events.length > 0 && (
                        <span className={`absolute bottom-1 h-1 w-1 rounded-full ${isSelected ? 'bg-white' : 'bg-[var(--warning)]'}`} />
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Side panel */}
        <div className="lg:w-64">
          {selectedDay ? (
            <Card>
              <CardContent className="pt-4">
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                  {format(selectedDay, 'MMMM d, yyyy')}
                </h3>
                {selectedItems.length === 0 ? (
                  <p className="text-xs text-[var(--text-muted)]">No deadlines on this day.</p>
                ) : (
                  <div className="space-y-2">
                    {selectedItems.map(tc => (
                      <Link to={`/applications?application=${tc.id}`} key={tc.id} className="block border border-[var(--border)] rounded-xl p-2">
                        <p className="text-sm font-medium text-[var(--text-primary)]">{tc.company_name}</p>
                        <Badge variant="secondary" className="text-[10px] mt-1">{tc.stage}</Badge><p className="text-xs text-[var(--text-muted)] mt-1">{tc.role}</p>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-[var(--text-muted)]">Click a date to see deadlines.</p>
                <div className="mt-3 space-y-1">
                  <p className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">Upcoming</p>
                  {data?.filter(tc => tc.deadline && parseISO(tc.deadline) >= startOfDay(new Date()) && !['Closed', 'Offer'].includes(tc.stage))
                    .sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
                    .slice(0, 5)
                    .map(tc => (
                      <div key={tc.id} className="flex items-center justify-between text-xs">
                        <span className="text-[var(--text-secondary)] truncate">{tc.company_name}</span>
                        <span className="text-[var(--warning)] ml-1 shrink-0">
                          {format(parseISO(tc.deadline!), 'MMM d')}
                        </span>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
