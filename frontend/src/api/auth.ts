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

export const authApi = {
  signup: (body: SignupRequest) =>
    apiPost<TokenResponse>('/auth/signup', body),

  login: (body: LoginRequest) =>
    apiPost<TokenResponse>('/auth/login', body),

  refresh: () =>
    apiPost<TokenResponse>('/auth/refresh'),

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
    window.location.href = `${import.meta.env.VITE_API_URL || ''}/api/v1/auth/google/login`
  },
}
