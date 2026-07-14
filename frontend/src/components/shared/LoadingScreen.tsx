import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import logo from '@/assets/logo.png'

export function LoadingScreen() {
  const [showWarning, setShowWarning] = useState(false)

  useEffect(() => {
    // Show a helper message if it takes longer than 5 seconds (potential cold start)
    const timer = setTimeout(() => {
      setShowWarning(true)
    }, 5000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div
      className="relative flex min-h-screen flex-col items-center justify-center p-4 overflow-hidden bg-dot-grid"
      style={{ background: 'var(--bg)' }}
    >
      {/* Ambient glow orbs */}
      <div
        className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full opacity-20 blur-3xl"
        style={{ background: 'radial-gradient(circle, #3b82f6, transparent 70%)' }}
      />
      <div
        className="pointer-events-none absolute -bottom-32 -right-32 h-80 w-80 rounded-full opacity-15 blur-3xl"
        style={{ background: 'radial-gradient(circle, #a78bfa, transparent 70%)' }}
      />

      <div className="relative flex flex-col items-center max-w-md w-full text-center animate-scale-in">
        {/* Brand Logo & Glowing Ring */}
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-[#3b82f6] to-[#a78bfa] opacity-30 blur-md animate-pulse" />
          <img
            src={logo}
            alt="OfferForge"
            className="relative h-20 w-20 rounded-2xl object-cover shadow-[0_0_24px_rgba(59,130,246,0.35)]"
          />
        </div>

        {/* Brand Name */}
        <span className="text-2xl font-bold gradient-text tracking-tight mb-1">
          OfferForge
        </span>
        <p className="text-xs text-[var(--text-muted)] mb-8">
          Placement prep, organised.
        </p>

        {/* Loading Spinner and Status */}
        <div className="flex flex-col items-center justify-center gap-3 min-h-[80px]">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--accent)]" />
          <span className="text-sm font-medium text-[var(--text-secondary)] animate-pulse">
            Connecting to server...
          </span>

          {showWarning && (
            <div className="mt-4 px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--card)]/60 glass max-w-sm animate-fade-in">
              <p className="text-xs text-[var(--warning)] leading-relaxed">
                💡 <strong>Notice:</strong> The backend server is currently waking up from sleep mode. This first load may take up to a minute. Thank you for your patience!
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
