/**
 * ProtectedRoute — redirects unauthenticated users to /login.
 *
 * Renders nothing (null) while the initial auth check is in progress,
 * so users never see broken/protected UI before the redirect.
 */
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  // Still checking auth state — show nothing to prevent UI flash.
  if (isLoading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
