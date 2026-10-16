import type { ReactNode } from 'react'
import { Command, Zap } from 'lucide-react'
import { AuthProductTour } from './AuthProductTour'

interface AuthCardProps {
  title: string
  description?: string
  children: ReactNode
}

export function AuthCard({ title, description, children }: AuthCardProps) {
  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="About OfferForge">
        <a href="/login" className="auth-wordmark"><span><Zap size={20} fill="currentColor" /></span>OfferForge<span className="auth-wordmark-tag">YOUR CAREER WORKSPACE</span></a>
        <div className="auth-story-content">
          <p className="auth-kicker"><span /> A LITTLE MORE INTENTION. A LOT MORE PROGRESS.</p>
          <h2>Your next chapter.<br /><span>Already in motion.</span></h2>
          <p className="auth-story-description">Bring your applications, preparation, and progress together. Make room for the work that moves you forward.</p>
          <AuthProductTour />
          <div className="auth-story-features"><span>Track opportunities</span><i /><span>Prepare with purpose</span><i /><span>See your progress</span></div>
        </div>
        <footer className="auth-story-footer"><span>Less scattered. More focused.</span><Command size={15} /></footer>
      </section>
      <section className="auth-form-panel" aria-labelledby="auth-title">
        <div className="auth-form-content">
          <div className="auth-form-mark" aria-hidden="true"><Zap size={22} /></div>
          <header className="auth-form-heading"><p className="auth-kicker">YOUR NEXT STEP STARTS HERE</p><h1 id="auth-title">{title}<span>.</span></h1>{description && <p>{description}</p>}</header>
          {children}
          <p className="auth-form-footnote">Your applications. Your preparation. Your pace.</p>
        </div>
        <div className="auth-form-footer">Built for your next opportunity <span>OfferForge</span></div>
      </section>
    </main>
  )
}
