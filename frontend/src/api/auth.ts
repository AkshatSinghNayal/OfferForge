/** Auth API calls — all wired to real backend endpoints. */

import { apiGet, apiPost } from './client'
import type {
  LoginRequest,
  MessageResponse,
  PasswordResetConfirm,
  PasswordResetRequest,
  SignupRequest,
  TokenResponse,
  UserPublic,
} from './types'

let activeRefreshPromise: Promise<TokenResponse> | null = null

export const authApi = {
  signup: (body: SignupRequest) =>
    apiPost<TokenResponse>('/auth/signup', body),

  login: (body: LoginRequest) =>
    apiPost<TokenResponse>('/auth/login', body),

  refresh: () => {
    if (!activeRefreshPromise) {
      activeRefreshPromise = apiPost<TokenResponse>('/auth/refresh').finally(() => {
        activeRefreshPromise = null
      })
    }
    return activeRefreshPromise
  },

  logout: () =>
    apiPost<MessageResponse>('/auth/logout'),

  me: () =>
    apiGet<UserPublic>('/auth/me'),

  requestPasswordReset: (body: PasswordResetRequest) =>
    apiPost<MessageResponse>('/auth/password-reset/request', body),

  confirmPasswordReset: (body: PasswordResetConfirm) =>
    apiPost<MessageResponse>('/auth/password-reset/confirm', body),

  /** Redirects to Google's consent screen (full page navigation). */
  googleLogin: () => {
    const baseUrl = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
    window.location.href = `${baseUrl}/api/v1/auth/google/login`
  },

  /** Log in as the demo user — seeds demo data on first call. */
  demoLogin: () =>
    apiPost<TokenResponse>('/auth/demo'),
}
