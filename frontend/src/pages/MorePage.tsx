import { NavLink } from 'react-router-dom'
import {
  FileText, BookOpen, Calendar, BarChart2, Settings,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

const MORE_ITEMS = [
  { to: '/resumes',   icon: FileText,   label: 'Resumes' },
  { to: '/resources', icon: BookOpen,   label: 'Resources' },
  { to: '/calendar',  icon: Calendar,   label: 'Calendar' },
  { to: '/analytics', icon: BarChart2,  label: 'Analytics' },
  { to: '/settings',  icon: Settings,   label: 'Settings' },
]

export default function MorePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">More</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">All sections</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {MORE_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            <Card className="cursor-pointer transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
              <CardContent className="flex flex-col items-center justify-center gap-3 py-8">
                <div className="h-12 w-12 rounded-2xl bg-[var(--accent)]/10 flex items-center justify-center ring-1 ring-[var(--accent)]/20">
                  <Icon className="h-5 w-5 text-[var(--accent)]" />
                </div>
                <span className="text-sm font-medium text-[var(--text-primary)]">{label}</span>
              </CardContent>
            </Card>
          </NavLink>
        ))}
      </div>
    </div>
  )
}
