import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
import { signupSchema, type SignupFormData } from '@/lib/schemas'

export default function SignupPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupFormData>({ resolver: zodResolver(signupSchema) })

  const [loadingMethod, setLoadingMethod] = useState<'demo' | 'google' | 'email' | null>(null)

  const onSubmit = async (data: SignupFormData) => {
    setLoadingMethod('email')
    try {
      const res = await authApi.signup({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      })
      login(res.user, res.access_token)
      toast.success('Account created! Welcome aboard.')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setLoadingMethod(null)
      if (axios.isAxiosError(err)) {
        const status = err.response?.status
        const detail = err.response?.data?.detail
        if (status === 409) {
          toast.error('An account with this email already exists.')
        } else {
          toast.error(typeof detail === 'string' ? detail : 'Signup failed. Please try again.')
        }
      } else {
        toast.error('Something went wrong. Please try again.')
      }
    }
  }

  return (
    <AuthCard title="Create an account" description="Start tracking your career goals with OfferForge">
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

      <div className="relative mb-4">
        <Separator />
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--card)] px-2 text-xs text-[var(--text-muted)]">
          or
        </span>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="full_name">Full name</Label>
          <Input
            id="full_name"
            type="text"
            autoComplete="name"
            placeholder="Your name"
            aria-invalid={!!errors.full_name}
            {...register('full_name')}
          />
          {errors.full_name && (
            <p className="text-xs text-[var(--danger)]" role="alert">
              {errors.full_name.message}
            </p>
          )}
        </div>

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
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="Min. 8 characters"
            aria-invalid={!!errors.password}
            {...register('password')}
          />
          {errors.password && (
            <p className="text-xs text-[var(--danger)]" role="alert">
              {errors.password.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            aria-invalid={!!errors.confirm_password}
            {...register('confirm_password')}
          />
          {errors.confirm_password && (
            <p className="text-xs text-[var(--danger)]" role="alert">
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        <Button type="submit" className="w-full gap-2" disabled={loadingMethod !== null}>
          {loadingMethod === 'email' ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Creating account...
            </>
          ) : (
            'Create account'
          )}
        </Button>
      </form>

      <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
        Already have an account?{' '}
        <Link to="/login" className="text-[var(--accent)] hover:underline">
          Sign in
        </Link>
      </p>
    </AuthCard>
  )
}
