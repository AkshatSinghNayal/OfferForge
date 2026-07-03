import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { Sun, Moon, AlertTriangle } from 'lucide-react'

const passwordSchema = z.object({
  new_password: z.string().min(8, 'Password must be at least 8 characters').max(128),
  confirm: z.string(),
}).refine(d => d.new_password === d.confirm, {
  message: "Passwords don't match",
  path: ['confirm'],
})
type PasswordForm = z.infer<typeof passwordSchema>

export default function SettingsPage() {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  })

  const onPasswordChange = async (_form: PasswordForm) => {
    // Backend requires a reset token flow — navigate to forgot-password
    // as there's no direct "change password" endpoint for authenticated users.
    // Wire this properly if the backend exposes an authenticated password-change endpoint.
    toast.info('To change your password, use the forgot-password flow.')
    reset()
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const handleDeleteAccount = () => {
    if (deleteConfirm !== 'DELETE') {
      toast.error('Type DELETE to confirm')
      return
    }
    // No delete-account endpoint in Phase 1–7 backend.
    toast.error('Account deletion is not yet supported by the backend API.')
    setDeleteOpen(false)
    setDeleteConfirm('')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Settings</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Profile</CardTitle>
          {user?.has_google_linked && (
            <CardDescription>
              <Badge variant="secondary" className="text-xs">Google Linked</Badge>
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label>Full name</Label>
            <Input value={user?.full_name ?? ''} readOnly className="opacity-60 cursor-not-allowed" />
            <p className="text-xs text-[var(--text-muted)]">
              {user?.has_google_linked ? 'Name is managed by Google and cannot be changed here.' : 'Contact support to change your name.'}
            </p>
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input value={user?.email ?? ''} readOnly className="opacity-60 cursor-not-allowed" />
            {user?.has_google_linked && (
              <p className="text-xs text-[var(--text-muted)]">Email is read-only — managed by Google OAuth.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Theme */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Theme</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              variant={theme === 'dark' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTheme('dark')}
              className="flex items-center gap-2"
            >
              <Moon className="h-3.5 w-3.5" /> Dark
            </Button>
            <Button
              variant={theme === 'light' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTheme('light')}
              className="flex items-center gap-2"
            >
              <Sun className="h-3.5 w-3.5" /> Light
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Password change */}
      {!user?.has_google_linked && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onPasswordChange)} className="space-y-3">
              <div className="space-y-1.5">
                <Label>New password</Label>
                <Input type="password" {...register('new_password')} aria-invalid={!!errors.new_password} />
                {errors.new_password && <p className="text-xs text-[var(--danger)]">{errors.new_password.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Confirm new password</Label>
                <Input type="password" {...register('confirm')} aria-invalid={!!errors.confirm} />
                {errors.confirm && <p className="text-xs text-[var(--danger)]">{errors.confirm.message}</p>}
              </div>
              <Button type="submit" size="sm" disabled={isSubmitting}>Update password</Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Logout */}
      <div>
        <Button variant="outline" onClick={handleLogout}>Log out</Button>
      </div>

      {/* Danger zone */}
      <Card className="border-[var(--danger)]/30">
        <CardHeader>
          <CardTitle className="text-sm text-[var(--danger)] flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-[var(--text-muted)] mb-3">
            Permanently delete your account and all associated data. This cannot be undone.
          </p>
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
            Delete Account
          </Button>
        </CardContent>
      </Card>

      {/* Delete confirm dialog */}
      <Dialog open={deleteOpen} onOpenChange={v => { if (!v) { setDeleteOpen(false); setDeleteConfirm('') } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-[var(--danger)]">Delete Account</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-[var(--text-secondary)]">
            This will permanently delete your account. Type <strong>DELETE</strong> to confirm.
          </p>
          <Input
            value={deleteConfirm}
            onChange={e => setDeleteConfirm(e.target.value)}
            placeholder="DELETE"
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setDeleteOpen(false); setDeleteConfirm('') }}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteAccount}>
              Delete Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
