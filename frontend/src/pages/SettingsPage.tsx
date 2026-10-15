import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sun, Moon, Check, LogOut, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import axios from 'axios'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { authApi } from '@/api/auth'
import { getAccessToken } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export default function SettingsPage() {
  const { user, login, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const [name, setName] = useState(user?.full_name ?? '')
  const [saving, setSaving] = useState(false)
  const [changing, setChanging] = useState(false)
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }
  return (
    <div className="workspace-page max-w-3xl">
      <header className="page-heading">
        <div>
          <p className="eyebrow">MAKE YOURSELF AT HOME</p>
          <h1>
            Settings<span className="heading-dot">.</span>
          </h1>
          <p>A workspace that feels like yours.</p>
        </div>
      </header>
      <section className="workspace-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PERSONAL DETAILS</p>
            <h2>Your profile</h2>
          </div>
          <ShieldCheck size={20} className="text-[var(--text-muted)]" />
        </div>
        <form
          className="p-6 pt-0 space-y-4"
          onSubmit={async (e) => {
            e.preventDefault()
            setSaving(true)
            try {
              const updated = await authApi.updateProfile(name.trim())
              const token = getAccessToken()
              if (token) login(updated, token)
              toast.success('Profile saved')
            } catch {
              toast.error('Could not save your profile. Please try again.')
            } finally {
              setSaving(false)
            }
          }}
        >
          <label className="field-label">
            Full name
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={120}
              autoComplete="name"
            />
          </label>
          <label className="field-label">
            Email
            <Input value={user?.email ?? ''} readOnly autoComplete="email" />
            <span className="text-xs text-[var(--text-muted)]">
              Your sign-in email.{' '}
              {user?.has_google_linked
                ? 'Google is connected to this account.'
                : ''}
            </span>
          </label>
          <Button disabled={saving || !name.trim()} type="submit">
            {saving ? 'Saving…' : 'Save profile'}
          </Button>
        </form>
      </section>
      <section className="workspace-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">APPEARANCE</p>
            <h2>Choose your atmosphere</h2>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-6">
          {(['dark', 'light'] as const).map((mode) => (
            <button
              key={mode}
              aria-pressed={theme === mode}
              onClick={() => setTheme(mode)}
              className={`p-4 rounded-xl text-left border ${theme === mode ? 'border-[var(--accent)]' : 'border-[var(--border)]'}`}
            >
              <div
                className={`h-20 rounded-lg mb-4 flex p-3 gap-2 ${mode === 'dark' ? 'bg-[#101114]' : 'bg-[#f1f3f7]'}`}
              >
                <div
                  className={`w-5 rounded ${mode === 'dark' ? 'bg-[#24262b]' : 'bg-white'}`}
                />
                <div className="flex-1 space-y-2">
                  <div className="h-2 w-1/2 rounded bg-blue-500/60" />
                  <div
                    className={`h-9 rounded ${mode === 'dark' ? 'bg-[#24262b]' : 'bg-white'}`}
                  />
                </div>
              </div>
              <span className="flex items-center gap-2 text-sm font-medium">
                {mode === 'dark' ? <Moon size={15} /> : <Sun size={15} />}
                {mode === 'dark' ? 'Dark' : 'Light'}
                {theme === mode && (
                  <Check size={15} className="ml-auto text-[var(--accent)]" />
                )}
              </span>
            </button>
          ))}
        </div>
      </section>
      <section className="workspace-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">ACCOUNT SECURITY</p>
            <h2>Change password</h2>
          </div>
        </div>
        {user?.has_google_linked ? (
          <p className="px-6 pb-6 text-sm text-[var(--text-secondary)]">
            You can sign in with Google. Manage your Google password in your
            Google account.
          </p>
        ) : (
          <form
            className="px-6 pb-6 space-y-4"
            onSubmit={async (e) => {
              e.preventDefault()
              if (password !== confirm) {
                toast.error('Passwords do not match')
                return
              }
              setChanging(true)
              try {
                await authApi.changePassword(current, password)
                toast.success(
                  'Password updated. Sign in with your new password.',
                )
                await signOut()
              } catch (error) {
                toast.error(
                  axios.isAxiosError(error) &&
                    typeof error.response?.data?.detail === 'string'
                    ? error.response.data.detail
                    : 'Could not update your password.',
                )
              } finally {
                setChanging(false)
              }
            }}
          >
            <label className="field-label">
              Current password
              <Input
                required
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <div className="grid sm:grid-cols-2 gap-4">
              <label className="field-label">
                New password
                <Input
                  required
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label className="field-label">
                Confirm new password
                <Input
                  required
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </label>
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              At least 8 characters. You’ll sign in again after changing your
              password.
            </p>
            <Button type="submit" disabled={changing}>
              {changing ? 'Updating…' : 'Update password'}
            </Button>
          </form>
        )}
      </section>
      <div>
        <Button variant="outline" onClick={signOut}>
          <LogOut />
          Sign out
        </Button>
      </div>
    </div>
  )
}
