import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFoundPage() {
  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ background: 'var(--bg)' }}
    >
      <div className="text-center space-y-4">
        <p className="text-6xl font-bold text-[var(--border)]">404</p>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Page not found</h1>
        <p className="text-sm text-[var(--text-muted)]">
          The page you're looking for doesn't exist.
        </p>
        <Button asChild>
          <Link to="/dashboard">Go to Dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
