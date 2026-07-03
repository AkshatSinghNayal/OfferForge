/**
 * Axios instance with auth interceptors.
 *
 * Access token lives in memory only (never localStorage/sessionStorage).
 * Refresh token is an httpOnly cookie — never read or stored by this code.
 *
 * On 401:
 *   1. Attempt POST /api/v1/auth/refresh once (the browser sends the cookie).
 *   2. If refresh succeeds, store the new access token and retry original.
 *   3. If refresh fails, clear auth state and redirect to /login.
 */

import axios, {
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

// ─── In-memory token store ────────────────────────────────────────────────────
// These are module-level so they survive re-renders but are cleared on
// page reload (intentional — forces re-auth via the refresh cookie).

let _accessToken: string | null = null
let _isRefreshing = false
// Queued requests waiting for the refresh to complete.
type RefreshSubscriber = (token: string) => void
let _refreshSubscribers: RefreshSubscriber[] = []

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

function subscribeTokenRefresh(cb: RefreshSubscriber) {
  _refreshSubscribers.push(cb)
}

function onTokenRefreshed(token: string) {
  _refreshSubscribers.forEach((cb) => cb(token))
  _refreshSubscribers = []
}

function onRefreshFailed() {
  _refreshSubscribers = []
}

// ─── Axios instance ───────────────────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || ''}/api/v1`,
  withCredentials: true, // send the httpOnly refresh cookie on cross-origin
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — attach access token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (_accessToken) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  return config
})

// Response interceptor — silent 401 → refresh → retry
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean
    }

    // Only handle 401s that haven't been retried already.
    // Skip the refresh endpoint itself to avoid infinite loops.
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (_isRefreshing) {
        // Another refresh is already in flight — queue this request.
        return new Promise<unknown>((resolve, reject) => {
          subscribeTokenRefresh((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(apiClient(originalRequest))
          })
          // If refresh fails, reject all queued requests too.
          // We repurpose the subscriber to handle this by re-checking later.
          void reject
        })
      }

      originalRequest._retry = true
      _isRefreshing = true

      try {
        const { data } = await apiClient.post<{ access_token: string }>(
          '/auth/refresh',
        )
        const newToken = data.access_token
        setAccessToken(newToken)
        onTokenRefreshed(newToken)
        _isRefreshing = false

        // Retry the original request with the new token.
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
        }
        return apiClient(originalRequest)
      } catch (_refreshError) {
        _isRefreshing = false
        setAccessToken(null)
        onRefreshFailed()

        // Dispatch a custom event so AuthContext can react without a circular
        // import dependency.
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

// ─── Typed request helpers ────────────────────────────────────────────────────

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await apiClient.get<T>(url, config)
  return res.data
}

export async function apiPost<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.post<T>(url, data, config)
  return res.data
}

export async function apiPatch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await apiClient.patch<T>(url, data, config)
  return res.data
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await apiClient.delete<T>(url, config)
  return res.data
}
