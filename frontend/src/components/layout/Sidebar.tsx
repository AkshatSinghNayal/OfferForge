import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  Code2,
  FileText,
  BookOpen,
  StickyNote,
  Calendar,
  BarChart2,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'

export const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/companies', icon: Building2,       label: 'Companies' },
  { to: '/dsa',       icon: Code2,           label: 'DSA Tracker' },
  { to: '/resumes',   icon: FileText,        label: 'Resumes' },
  { to: '/resources', icon: BookOpen,        label: 'Resources' },
  { to: '/notes',     icon: StickyNote,      label: 'Notes' },
  { to: '/calendar',  icon: Calendar,        label: 'Calendar' },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics' },
  { to: '/settings',  icon: Settings,        label: 'Settings' },
]

interface SidebarProps {
  collapsed: boolean
  onCollapse: (c: boolean) => void
  onNavigate?: () => void
}

export function Sidebar({ collapsed, onCollapse, onNavigate }: SidebarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
    : '?'

  return (
    <TooltipProvider delayDuration={150}>
      <aside
        className={cn(
          'fixed left-0 top-0 h-screen flex flex-col z-40',
          'transition-[width] duration-200 ease-out',
          'border-r border-[var(--border)]',
          collapsed ? 'w-14' : 'w-52',
        )}
        style={{ background: 'var(--sidebar)' }}
        aria-label="Main navigation"
      >
        {/* Brand + collapse toggle */}
        <div
          className={cn(
            'flex items-center h-14 border-b border-[var(--border)] px-3 flex-shrink-0',
            collapsed ? 'justify-center' : 'justify-between',
          )}
        >
          {!collapsed && (
            <div className="flex items-center gap-2 min-w-0">
              <div className="h-6 w-6 rounded-lg bg-[var(--accent)] flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(59,130,246,0.5)]">
                <Zap className="h-3.5 w-3.5 text-white" fill="currentColor" />
              </div>
              <span className="text-sm font-bold gradient-text truncate tracking-tight">
                OfferForge
              </span>
            </div>
          )}
          {collapsed && (
            <div className="h-6 w-6 rounded-lg bg-[var(--accent)] flex items-center justify-center shadow-[0_0_10px_rgba(59,130,246,0.5)]">
              <Zap className="h-3.5 w-3.5 text-white" fill="currentColor" />
            </div>
          )}
          {!collapsed && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onCollapse(true)}
                  aria-label="Collapse sidebar"
                  className="h-7 w-7 shrink-0 ml-1"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Collapse</TooltipContent>
            </Tooltip>
          )}
          {collapsed && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onCollapse(false)}
                  aria-label="Expand sidebar"
                  className="absolute -right-3 top-1/2 -translate-y-1/2 h-5 w-5 rounded-full border border-[var(--border)] bg-[var(--sidebar)] flex items-center justify-center hover:bg-[var(--card)] transition-colors z-50 md:flex"
                >
                  <ChevronRight className="h-3 w-3 text-[var(--text-muted)]" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Expand</TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 flex-1 px-2 py-3 overflow-y-auto overflow-x-hidden">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <Tooltip key={to}>
              <TooltipTrigger asChild>
                <NavLink
                  to={to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      'relative flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-all duration-150',
                      isActive
                        ? 'nav-active-bar bg-[var(--accent)]/10 text-[var(--accent)] font-medium'
                        : 'text-[var(--text-muted)] hover:bg-[var(--card)] hover:text-[var(--text-primary)]',
                    )
                  }
                  aria-label={collapsed ? label : undefined}
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={cn(
                          'h-4 w-4 shrink-0 transition-colors',
                          isActive ? 'text-[var(--accent)]' : '',
                        )}
                      />
                      {!collapsed && <span className="truncate">{label}</span>}
                    </>
                  )}
                </NavLink>
              </TooltipTrigger>
              {collapsed && <TooltipContent side="right">{label}</TooltipContent>}
            </Tooltip>
          ))}
        </nav>

        {/* Footer: avatar + user info + logout */}
        <div
          className={cn(
            'flex items-center border-t border-[var(--border)] px-2 py-3 gap-2',
            collapsed ? 'flex-col' : 'flex-row',
          )}
        >
          <Avatar className="h-7 w-7 shrink-0 ring-2 ring-[var(--border)]">
            <AvatarFallback className="text-xs bg-[var(--accent)]/15 text-[var(--accent)] font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--text-primary)] truncate leading-tight">
                {user?.full_name}
              </p>
              <p className="text-[10px] text-[var(--text-muted)] truncate leading-tight mt-0.5">
                {user?.email}
              </p>
            </div>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                aria-label="Log out"
                className="h-7 w-7 shrink-0 text-[var(--text-muted)] hover:text-[var(--danger)] hover:bg-[var(--danger)]/10"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Log out</TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  )
}
