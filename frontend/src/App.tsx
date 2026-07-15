import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider } from '@/context/AuthContext'
import { ProtectedRoute } from '@/components/shared/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'

// Auth pages (lazy loaded)
const LoginPage = lazy(() => import('@/pages/LoginPage'))
const SignupPage = lazy(() => import('@/pages/SignupPage'))
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPasswordPage'))
const GoogleCallbackPage = lazy(() => import('@/pages/GoogleCallbackPage'))

// App pages (lazy loaded)
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const CompaniesPage = lazy(() => import('@/pages/CompaniesPage'))
const CompanyDetailPage = lazy(() => import('@/pages/CompanyDetailPage'))
const DSAPage = lazy(() => import('@/pages/DSAPage'))
const ResumesPage = lazy(() => import('@/pages/ResumesPage'))
const ResourcesPage = lazy(() => import('@/pages/ResourcesPage'))
const NotesPage = lazy(() => import('@/pages/NotesPage'))
const CalendarPage = lazy(() => import('@/pages/CalendarPage'))
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const MorePage = lazy(() => import('@/pages/MorePage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const status = (error as any)?.response?.status
        if (status === 401 || status === 403) return false
        return failureCount < 2
      },
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={
              <div className="flex h-screen w-screen items-center justify-center bg-[var(--background)]">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--accent)] border-t-transparent" />
                  <p className="text-sm font-medium text-[var(--text-muted)]">Loading OfferForge...</p>
                </div>
              </div>
            }>
              <Routes>
                {/* Auth routes (public) */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />

                {/* Protected app routes */}
                <Route element={<ProtectedRoute />}>
                  <Route element={<AppLayout />}>
                    <Route index element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/companies" element={<CompaniesPage />} />
                    <Route path="/companies/:id" element={<CompanyDetailPage />} />
                    <Route path="/dsa" element={<DSAPage />} />
                    <Route path="/resumes" element={<ResumesPage />} />
                    <Route path="/resources" element={<ResourcesPage />} />
                    <Route path="/notes" element={<NotesPage />} />
                    <Route path="/calendar" element={<CalendarPage />} />
                    <Route path="/analytics" element={<AnalyticsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/more" element={<MorePage />} />
                  </Route>
                </Route>

                {/* 404 */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </BrowserRouter>

          {/* Global toasts */}
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: 'var(--card)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                borderRadius: '12px',
                fontSize: '13px',
              },
            }}
            theme="system"
          />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
