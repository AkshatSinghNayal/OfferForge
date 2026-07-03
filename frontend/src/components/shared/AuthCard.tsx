import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import logo from '@/assets/logo.png'

interface AuthCardProps {
  title: string
  description?: string
  children: ReactNode
}

export function AuthCard({ title, description, children }: AuthCardProps) {
  return (
    <div
      className="relative flex min-h-screen items-center justify-center p-4 overflow-hidden bg-dot-grid"
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

      <div className="relative w-full max-w-sm animate-scale-in">
        {/* Brand */}
        <div className="flex flex-col items-center mb-8 gap-3">
          <div className="relative">
            <img
              src={logo}
              alt="OfferForge"
              className="h-16 w-16 rounded-2xl object-cover shadow-[0_0_24px_rgba(59,130,246,0.35)]"
            />
          </div>
          <div className="text-center">
            <span className="text-xl font-bold gradient-text tracking-tight">OfferForge</span>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">Placement prep, organised.</p>
          </div>
        </div>

        <Card className="glass border-[var(--border)] shadow-[0_8px_32px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.06)]">
          <CardHeader className="space-y-1 text-center pb-4">
            <CardTitle className="text-xl">{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
      </div>
    </div>
  )
}
