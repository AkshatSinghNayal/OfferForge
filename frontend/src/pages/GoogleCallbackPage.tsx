/**
 * GoogleCallbackPage — handles the redirect from the backend after OAuth.
 *
 * The backend redirects to /auth/google/callback?success=1 with the
 * refresh token already set as an httpOnly cookie. We just need to call
 * POST /auth/refresh to exchange the cookie for an access token.
 */
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Skeleton } from '@/components/ui/skeleton'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'

export default function GoogleCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()

  useEffect(() => {
    const success = searchParams.get('success')

    if (success !== '1') {
      toast.error('Google sign-in failed.')
      navigate('/login', { replace: true })
      return
    }

    let cancelled = false

    const finish = async () => {
      try {
        const data = await authApi.refresh()
        if (cancelled) return
        login(data.user, data.access_token)
        toast.success(`Welcome, ${data.user.full_name.split(' ')[0]}!`)
        navigate('/dashboard', { replace: true })
      } catch {
        if (cancelled) return
        toast.error('Failed to complete sign-in. Please try again.')
        navigate('/login', { replace: true })
      }
    }

    void finish()
    return () => {
      cancelled = true
    }
  }, [searchParams, navigate, login])

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ background: 'var(--bg)' }}
    >
      <div className="flex flex-col items-center gap-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-32" />
        <p className="text-sm text-[var(--text-muted)] mt-2">
          Completing sign-in…
        </p>
      </div>
    </div>
  )
}
