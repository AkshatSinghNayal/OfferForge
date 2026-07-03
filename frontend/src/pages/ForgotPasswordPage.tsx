import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { CheckCircle } from 'lucide-react'
import { AuthCard } from '@/components/shared/AuthCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/api/auth'
import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/lib/schemas'

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({ resolver: zodResolver(forgotPasswordSchema) })

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      await authApi.requestPasswordReset({ email: data.email })
      // Backend always returns 200 — never reveals if email exists.
      setSubmitted(true)
    } catch {
      // Show generic error but still show success UI (same as above) to not
      // leak whether the email is registered.
      toast.error('Request failed. Please try again.')
    }
  }

  if (submitted) {
    return (
      <AuthCard title="Check your email" description="">
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <CheckCircle className="h-10 w-10 text-[var(--success)]" />
          <p className="text-sm text-[var(--text-secondary)]">
            If that email is registered, a reset link has been sent.
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            The link expires in 30 minutes.
          </p>
          <Link
            to="/login"
            className="mt-2 text-sm text-[var(--accent)] hover:underline"
          >
            Back to sign in
          </Link>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Reset your password"
      description="Enter your email and we'll send you a reset link"
    >
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

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Sending…' : 'Send reset link'}
        </Button>
      </form>

      <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
        <Link to="/login" className="text-[var(--accent)] hover:underline">
          Back to sign in
        </Link>
      </p>
    </AuthCard>
  )
}
