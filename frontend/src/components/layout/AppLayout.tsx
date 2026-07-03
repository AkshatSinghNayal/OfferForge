import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Code2, StickyNote, Grid3x3,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { CommandPalette } from './CommandPalette'

const SIDEBAR_KEY = 'sidebar_collapsed'

const BOTTOM_NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Home' },
  { to: '/dsa',       icon: Code2,           label: 'DSA' },
  { to: '/companies', icon: Building2,       label: 'Companies' },
  { to: '/notes',     icon: StickyNote,      label: 'Notes' },
  { to: '/more',      icon: Grid3x3,         label: 'More' },
]

export function AppLayout() {
  const [cmdOpen, setCmdOpen] = useState(false)

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try { return localStorage.getItem(SIDEBAR_KEY) === 'true' } catch { return false }
  })

  // Persist preference
  useEffect(() => {
    try { localStorage.setItem(SIDEBAR_KEY, String(collapsed)) } catch { /* ignore */ }
  }, [collapsed])

  // Update the CSS custom property on :root so .topbar-push and .content-push
  // both respond to sidebar collapse/expand at any breakpoint via pure CSS.
  useEffect(() => {
    const w = collapsed ? '56px' : '208px'
    document.documentElement.style.setProperty('--sidebar-width', w)
  }, [collapsed])

  // Global ⌘K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCmdOpen(o => !o)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />
      </div>

      {/* Main area */}
      <div className="content-push flex-1 flex flex-col min-w-0 transition-[margin] duration-200">
        <Topbar
          onCommandPalette={() => setCmdOpen(true)}
        />

        <main className="flex-1 mt-14 overflow-y-auto overflow-x-hidden pb-16 md:pb-0">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-30 border-t border-[var(--border)] flex items-center justify-around px-1 h-16"
        style={{ background: 'var(--card)' }}
        aria-label="Mobile navigation"
      >
        {BOTTOM_NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 px-2 py-1 rounded-xl transition-colors duration-150 flex-1',
                isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]',
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className={cn(
                  'h-8 w-8 flex items-center justify-center rounded-xl transition-all duration-150',
                  isActive ? 'bg-[var(--accent)]/15' : '',
                )}>
                  <Icon style={{ width: 18, height: 18 }} />
                </div>
                <span className="text-[10px] font-medium leading-none">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  )
}
