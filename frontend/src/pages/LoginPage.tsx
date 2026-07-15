import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import axios from 'axios'
import { AuthCard } from '@/components/shared/AuthCard'
import { GoogleIcon } from '@/components/shared/GoogleIcon'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/context/AuthContext'
import { authApi } from '@/api/auth'
import { loginSchema, type LoginFormData } from '@/lib/schemas'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Handle OAuth error redirects from backend
  useEffect(() => {
    const error = searchParams.get('error')
    if (error) {
      const messages: Record<string, string> = {
        oauth_declined: 'Google sign-in was cancelled.',
        oauth_failed: 'Google sign-in failed. Please try again.',
        oauth_state_mismatch: 'Security check failed. Please try again.',
        oauth_missing_params: 'OAuth response was incomplete. Please try again.',
      }
      toast.error(messages[error] ?? 'Authentication failed.')
    }
  }, [searchParams])

  // Already logged in → go to dashboard
  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) })

  const [loadingMethod, setLoadingMethod] = useState<'demo' | 'google' | 'email' | null>(null)

  const onSubmit = async (data: LoginFormData) => {
    setLoadingMethod('email')
    try {
      const res = await authApi.login(data)
      login(res.user, res.access_token)
      toast.success(`Welcome back, ${res.user.full_name.split(' ')[0]}!`)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setLoadingMethod(null)
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail
        toast.error(
          typeof detail === 'string'
            ? detail
            : 'Invalid email or password.',
        )
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      description="Sign in to your account"
    >
      {/* Demo Login — same outline style as Google button */}
      <Button
        variant="outline"
        className="w-full mb-4 gap-2"
        type="button"
        disabled={loadingMethod !== null}
        onClick={async () => {
          setLoadingMethod('demo')
          try {
            const res = await authApi.demoLogin()
            login(res.user, res.access_token)
            toast.success('Welcome to the demo!')
            navigate('/dashboard', { replace: true })
          } catch {
            toast.error('Demo login failed. Please try again.')
            setLoadingMethod(null)
          }
        }}
      >
        {loadingMethod === 'demo' ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
            Logging in to Demo...
          </>
        ) : (
          <>
            <span className="text-base leading-none">🔑</span>
            Access with Demo Account
          </>
        )}
      </Button>

      {/* Google OAuth */}
      <Button
        variant="outline"
        className="w-full mb-4 gap-2"
        type="button"
        disabled={loadingMethod !== null}
        onClick={() => {
          setLoadingMethod('google')
          authApi.googleLogin()
        }}
      >
        {loadingMethod === 'google' ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
            Redirecting to Google...
          </>
        ) : (
          <>
            <GoogleIcon />
            Continue with Google
          </>
        )}
      </Button>

      {/* Divider */}
      <div className="relative mb-4">
        <Separator />
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--card)] px-2 text-xs text-[var(--text-muted)]">
          or
        </span>
      </div>

      {/* Email/password form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={!!errors.email}
            {...register('email')}
          />
          {errors.email && (
            <p className="text-xs text-[var(--danger)]" role="alert">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link
              to="/forgot-password"
              className="text-xs text-[var(--accent)] hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={!!errors.password}
            {...register('password')}
          />
          {errors.password && (
            <p className="text-xs text-[var(--danger)]" role="alert">
              {errors.password.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full gap-2" disabled={loadingMethod !== null}>
          {loadingMethod === 'email' ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </Button>
      </form>

      <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
        Don't have an account?{' '}
        <Link to="/signup" className="text-[var(--accent)] hover:underline">
          Sign up
        </Link>
      </p>
    </AuthCard>
  )
}
