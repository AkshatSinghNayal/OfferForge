/**
 * Command palette — ⌘K / Ctrl+K.
 *
 * Search is debounced and wired to GET /api/v1/search?q= for queries ≥ 2
 * characters. Results span companies, DSA problems, notes, and resources in
 * one call. Nav shortcut items are always shown when the query is empty.
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Building2, Code2, FileText, BookOpen,
  StickyNote, Calendar, Settings, Search, Loader2,
} from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { searchApi, type SearchResponse } from '@/api/search'

// ─── Static nav items ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Companies', to: '/companies', icon: Building2 },
  { label: 'DSA Tracker', to: '/dsa', icon: Code2 },
  { label: 'Resumes', to: '/resumes', icon: FileText },
  { label: 'Resources', to: '/resources', icon: BookOpen },
  { label: 'Notes', to: '/notes', icon: StickyNote },
  { label: 'Calendar', to: '/calendar', icon: Calendar },
  { label: 'Analytics', to: '/analytics', icon: Code2 },
  { label: 'Settings', to: '/settings', icon: Settings },
]

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchError, setSearchError] = useState(false)

  // Reset state when closed
  useEffect(() => {
    if (!open) {
      setQuery('')
      setResults(null)
      setSearchError(false)
    }
  }, [open])

  // Debounced real search
  useEffect(() => {
    if (query.length < 2) {
      setResults(null)
      setSearchError(false)
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      setSearchError(false)
      try {
        const data = await searchApi.search(query, 8)
        setResults(data)
      } catch {
        setSearchError(true)
        setResults(null)
      } finally {
        setLoading(false)
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [query])

  const goTo = useCallback((to: string) => {
    navigate(to)
    onClose()
  }, [navigate, onClose])

  const q = query.toLowerCase()
  const navMatches = NAV_ITEMS.filter(n => n.label.toLowerCase().includes(q || ''))
  const hasApiResults = results && (
    results.companies.length > 0 ||
    results.dsa_problems.length > 0 ||
    results.notes.length > 0 ||
    results.resources.length > 0
  )

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="p-0 max-w-lg overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border)]">
          {loading
            ? <Loader2 className="h-4 w-4 text-[var(--text-muted)] shrink-0 animate-spin" />
            : <Search className="h-4 w-4 text-[var(--text-muted)] shrink-0" />
          }
          <input
            autoFocus
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search pages, companies, problems, notes…"
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none"
            onKeyDown={e => { if (e.key === 'Escape') onClose() }}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            >
              Clear
            </button>
          )}
        </div>

        {/* Results */}
        <div className="max-h-[360px] overflow-y-auto py-2">
          {/* Error */}
          {searchError && (
            <p className="px-4 py-3 text-xs text-[var(--danger)]">Search failed. Check your connection.</p>
          )}

          {/* API results (query ≥ 2 chars) */}
          {!loading && query.length >= 2 && results && (
            <>
              {results.companies.length > 0 && (
                <Section label="Companies">
                  {results.companies.map(c => (
                    <ResultRow
                      key={c.id}
                      icon={<Building2 className="h-4 w-4" />}
                      label={c.name}
                      sublabel={c.cluster}
                      onClick={() => goTo(`/companies/${c.id}`)}
                    />
                  ))}
                </Section>
              )}
              {results.dsa_problems.length > 0 && (
                <Section label="DSA Problems">
                  {results.dsa_problems.map(p => (
                    <ResultRow
                      key={p.id}
                      icon={<Code2 className="h-4 w-4" />}
                      label={p.title}
                      sublabel={p.difficulty}
                      onClick={() => goTo('/dsa')}
                    />
                  ))}
                </Section>
              )}
              {results.notes.length > 0 && (
                <Section label="Notes">
                  {results.notes.map(n => (
                    <ResultRow
                      key={n.id}
                      icon={<StickyNote className="h-4 w-4" />}
                      label={n.title}
                      sublabel={n.type}
                      onClick={() => goTo('/notes')}
                    />
                  ))}
                </Section>
              )}
              {results.resources.length > 0 && (
                <Section label="Resources">
                  {results.resources.map(r => (
                    <ResultRow
                      key={r.id}
                      icon={<BookOpen className="h-4 w-4" />}
                      label={r.title}
                      sublabel={r.category}
                      onClick={() => goTo('/resources')}
                    />
                  ))}
                </Section>
              )}
              {!hasApiResults && !loading && (
                <p className="px-4 py-6 text-center text-sm text-[var(--text-muted)]">
                  No results for &quot;{query}&quot;
                </p>
              )}
            </>
          )}

          {/* Nav shortcuts — always shown, filtered by query */}
          {(query.length < 2 || navMatches.length > 0) && (
            <Section label={query.length >= 2 ? 'Pages' : 'Navigation'}>
              {navMatches.map(item => (
                <ResultRow
                  key={item.to}
                  icon={<item.icon className="h-4 w-4" />}
                  label={item.label}
                  sublabel="Page"
                  onClick={() => goTo(item.to)}
                />
              ))}
            </Section>
          )}
        </div>

        <div className="border-t border-[var(--border)] px-4 py-2 flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
          <span><kbd className="rounded border border-[var(--border)] px-1">↵</kbd> select</span>
          <span><kbd className="rounded border border-[var(--border)] px-1">Esc</kbd> close</span>
          {query.length >= 2 && results && (
            <span className="ml-auto">{results.total} result{results.total !== 1 ? 's' : ''}</span>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{label}</p>
      {children}
    </div>
  )
}

function ResultRow({
  icon, label, sublabel, onClick,
}: {
  icon: React.ReactNode
  label: string
  sublabel: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--card)] transition-colors text-left"
    >
      <span className="text-[var(--text-muted)] shrink-0">{icon}</span>
      <span className="flex-1 truncate">{label}</span>
      <span className="text-xs text-[var(--text-muted)] shrink-0">{sublabel}</span>
    </button>
  )
}
