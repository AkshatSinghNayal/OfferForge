import { useEffect } from 'react'
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
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginFormData) => {
    try {
      const res = await authApi.login(data)
      login(res.user, res.access_token)
      toast.success(`Welcome back, ${res.user.full_name.split(' ')[0]}!`)
      navigate('/dashboard', { replace: true })
    } catch (err) {
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
      {/* Demo Login */}
      <Button
        variant="default"
        className="w-full mb-3 gap-2 bg-emerald-600 hover:bg-emerald-700"
        type="button"
        onClick={async () => {
          try {
            const res = await authApi.demoLogin()
            login(res.user, res.access_token)
            toast.success('Welcome to the demo!')
            navigate('/dashboard', { replace: true })
          } catch {
            toast.error('Demo login failed. Please try again.')
          }
        }}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" /></svg>
        Demo Login
      </Button>

      {/* Google OAuth */}
      <Button
        variant="outline"
        className="w-full mb-4 gap-2"
        type="button"
        onClick={() => authApi.googleLogin()}
      >
        <GoogleIcon />
        Continue with Google
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

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
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
