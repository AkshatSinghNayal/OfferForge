/** API response types — derived from the real backend Pydantic schemas.
 *  Never invent shapes here; keep in sync with backend/app/schemas/.
 */

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface UserPublic {
  id: string
  email: string
  full_name: string
  is_active: boolean
  has_google_linked: boolean
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: UserPublic
}

export interface MessageResponse {
  message: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SignupRequest {
  email: string
  password: string
  full_name: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  new_password: string
}

// ─── API Error shape ──────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
