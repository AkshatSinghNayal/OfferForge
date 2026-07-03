import { Sun, Moon, Search, Settings } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/companies': 'Companies',
  '/dsa': 'DSA Tracker',
  '/resumes': 'Resumes',
  '/resources': 'Resources',
  '/notes': 'Notes',
  '/calendar': 'Calendar',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
  '/search': 'Search',
}

interface TopbarProps {
  onCommandPalette: () => void
}

export function Topbar({ onCommandPalette }: TopbarProps) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  const initials = user?.full_name
    ? user.full_name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
    : '?'

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  // Match /companies/some-id → "Companies"
  const pageTitle = Object.entries(PAGE_TITLES).find(([path]) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
  )?.[1] ?? ''

  return (
    <TooltipProvider delayDuration={200}>
      <header
        className="topbar-push fixed top-0 right-0 left-0 h-14 flex items-center justify-between px-3 z-30 border-b border-[var(--border)] transition-[left] duration-200"
        style={{ background: 'var(--card)' }}
      >
        {/* Left: page title */}
        <div className="flex items-center gap-2">
          {pageTitle && (
            <span className="block text-sm font-semibold text-[var(--text-primary)]">
              {pageTitle}
            </span>
          )}
        </div>

        {/* Right: search + theme + avatar */}
        <div className="flex items-center gap-1">
          {/* Command palette trigger */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={onCommandPalette}
                className="hidden sm:flex items-center gap-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs rounded-lg border border-[var(--border)] bg-[var(--input-bg)] hover:bg-[var(--border)]/60 px-3 h-8"
                aria-label="Open command palette"
              >
                <Search className="h-3.5 w-3.5" />
                <span>Search</span>
                <kbd className="ml-1 rounded border border-[var(--border)] px-1.5 py-0.5 text-[10px] font-sans opacity-70">⌘K</kbd>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Command palette (⌘K)</TooltipContent>
          </Tooltip>

          {/* Theme toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8" aria-label="Toggle theme">
                {theme === 'dark'
                  ? <Sun className="h-4 w-4 text-[var(--text-muted)]" />
                  : <Moon className="h-4 w-4 text-[var(--text-muted)]" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</TooltipContent>
          </Tooltip>

          {/* User avatar → dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" aria-label="User menu">
                <Avatar className="h-7 w-7 ring-2 ring-[var(--border)]">
                  <AvatarFallback className="text-xs bg-[var(--accent)]/15 text-[var(--accent)] font-semibold">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <div className="px-3 py-2">
                <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{user?.full_name}</p>
                <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">{user?.email}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/settings" className="flex items-center gap-2 cursor-pointer">
                  <Settings className="h-3.5 w-3.5" /> Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="text-[var(--danger)] focus:text-[var(--danger)] focus:bg-[var(--danger)]/10 cursor-pointer"
              >
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
    </TooltipProvider>
  )
}
