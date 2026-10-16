/**
 * GoogleCallbackPage — handles the redirect from the backend after OAuth.
 *
 * The backend supplies an access token and sets an httpOnly refresh cookie.
 * This page owns session establishment; AuthProvider skips its bootstrap here.
 * Older callbacks without an access token use the refresh cookie instead.
 */
import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Skeleton } from '@/components/ui/skeleton'
import { authApi } from '@/api/auth'
import { setAccessToken } from '@/api/client'
import { useAuth } from '@/context/AuthContext'

export default function GoogleCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const calledRef = useRef(false)

  useEffect(() => {
    if (calledRef.current) return
    calledRef.current = true

    const token = searchParams.get('token')
    const success = searchParams.get('success')
    // Remove the credential before loading profile data or navigating elsewhere.
    window.history.replaceState(null, '', window.location.pathname)

    if (success !== '1' && !token) {
      toast.error('Google sign-in failed.')
      navigate('/login', { replace: true })
      return
    }

    if (token) {
      setAccessToken(token)
      authApi
        .me()
        .then((user) => {
          login(user, token)
          toast.success(`Welcome, ${(user.full_name || 'User').split(' ')[0]}!`)
          navigate('/dashboard', { replace: true })
        })
        .catch(() => {
          setAccessToken(null)
          toast.error('Failed to complete sign-in. Please try again.')
          navigate('/login', { replace: true })
        })
      return
    }

    authApi
      .refresh()
      .then((data) => {
        login(data.user, data.access_token)
        toast.success(`Welcome, ${(data.user.full_name || 'User').split(' ')[0]}!`)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        toast.error('Failed to complete sign-in. Please try again.')
        navigate('/login', { replace: true })
      })
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
