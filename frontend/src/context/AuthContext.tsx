/**
 * AuthContext — tracks the authenticated user and access token state.
 *
 * On mount:
 *   - Attempt POST /auth/refresh (the httpOnly cookie is sent automatically).
 *   - If it succeeds, we have a valid access token and user → set as logged in.
 *   - If it fails (no cookie / expired), user is logged out.
 *
 * Access token lives in memory here. Never stored in localStorage.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { authApi } from '@/api/auth'
import { setAccessToken } from '@/api/client'
import type { UserPublic } from '@/api/types'

interface AuthState {
  user: UserPublic | null
  isAuthenticated: boolean
  /** True while the initial refresh check is in progress. */
  isLoading: boolean
}

interface AuthContextValue extends AuthState {
  login: (user: UserPublic, accessToken: string) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  })

  const login = useCallback((user: UserPublic, accessToken: string) => {
    setAccessToken(accessToken)
    setState({ user, isAuthenticated: true, isLoading: false })
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // Best effort — clear local state regardless.
    }
    setAccessToken(null)
    setState({ user: null, isAuthenticated: false, isLoading: false })
  }, [])

  // Bootstrap: attempt a silent refresh on first load.
  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      try {
        const data = await authApi.refresh()
        if (cancelled) return
        setAccessToken(data.access_token)
        setState({ user: data.user, isAuthenticated: true, isLoading: false })
      } catch {
        if (cancelled) return
        setAccessToken(null)
        setState({ user: null, isAuthenticated: false, isLoading: false })
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  // Listen for the 'auth:logout' event dispatched by the Axios interceptor
  // when a refresh fails mid-session.
  useEffect(() => {
    const handleForcedLogout = () => {
      setAccessToken(null)
      setState({ user: null, isAuthenticated: false, isLoading: false })
    }
    window.addEventListener('auth:logout', handleForcedLogout)
    return () => window.removeEventListener('auth:logout', handleForcedLogout)
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
