import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { safeGetItem, safeRemoveItem, safeSetItem } from './storage'

/**
 * 认证拦截器配置
 */
export interface AuthInterceptorConfig {
  /** Token在localStorage中的key */
  tokenKey?: string
  /** 用户信息在localStorage中的key */
  userKey?: string
  /** Token刷新阈值（毫秒），默认为1天 */
  refreshThreshold?: number
  /** 登录页路径 */
  loginPath?: string
  /** 是否启用自动Token刷新 */
  enableAutoRefresh?: boolean
}

const DEFAULT_CONFIG: Required<AuthInterceptorConfig> = {
  tokenKey: 'token',
  userKey: 'user',
  refreshThreshold: 24 * 60 * 60 * 1000, // 1天
  loginPath: '/login',
  enableAutoRefresh: true,
}

/**
 * 解析JWT Token的payload部分
 */
function parseJwtPayload(token: string): any | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

/**
 * 检查Token是否即将过期
 */
function isTokenExpiringSoon(token: string, threshold: number): boolean {
  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return false

  const expiresAt = payload.exp * 1000
  const now = Date.now()
  return expiresAt - now < threshold
}

/**
 * 刷新Token（调用刷新API）
 */
async function refreshAccessToken(token: string): Promise<{ token: string; user: any } | null> {
  const API_BASE = import.meta.env.DEV
    ? '/api/v1'
    : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1')

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
    })

    if (res.ok) {
      const data = await res.json()
      return {
        token: data.token || data.access_token,
        user: data.user,
      }
    }
  } catch (error) {
    console.warn('[AuthInterceptor] Token刷新失败:', error)
  }

  return null
}

/**
 * 清除认证信息并跳转登录页
 */
function clearAuthAndRedirect(loginPath: string): void {
  safeRemoveItem('token')
  safeRemoveItem('user')
  // 避免在登录页重复跳转
  if (window.location.pathname !== loginPath) {
    window.location.href = loginPath
  }
}

/**
 * 安装认证拦截器
 */
export function setupAuthInterceptor(
  instance: AxiosInstance,
  config: AuthInterceptorConfig = {}
): void {
  const finalConfig = { ...DEFAULT_CONFIG, ...config }
  const {
    tokenKey,
    refreshThreshold,
    loginPath,
    enableAutoRefresh
  } = finalConfig

  // 防止并发刷新Token
  let isRefreshing = false
  let refreshSubscribers: ((token: string) => void)[] = []

  function subscribeTokenRefresh(cb: (token: string) => void) {
    refreshSubscribers.push(cb)
  }

  function onTokenRefreshed(token: string) {
    refreshSubscribers.forEach(cb => cb(token))
    refreshSubscribers = []
  }

  // 请求拦截器：添加Authorization header并自动刷新Token
  instance.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      const token = safeGetItem(tokenKey)

      if (token) {
        // 自动刷新即将过期的Token
        if (enableAutoRefresh && isTokenExpiringSoon(token, refreshThreshold)) {
          if (!isRefreshing) {
            isRefreshing = true
            try {
              const result = await refreshAccessToken(token)
              if (result) {
                safeSetItem(tokenKey, result.token)
                if (result.user) {
                  safeSetItem('user', JSON.stringify(result.user))
                }
                onTokenRefreshed(result.token)
                config.headers.Authorization = `Bearer ${result.token}`
              }
            } catch (error) {
              console.warn('[AuthInterceptor] Token自动刷新失败:', error)
            } finally {
              isRefreshing = false
            }
          } else {
            // 等待Token刷新完成
            return new Promise((resolve) => {
              subscribeTokenRefresh((newToken) => {
                config.headers.Authorization = `Bearer ${newToken}`
                resolve(config)
              })
            })
          }
        } else {
          config.headers.Authorization = `Bearer ${token}`
        }
      }

      return config
    },
    (error) => Promise.reject(error)
  )

  // 响应拦截器：处理401/403错误
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      // 网络错误（后端不可达）
      if (!error.response) {
        return Promise.reject(error)
      }

      const status = error.response.status
      const config = error.config

      // 401 未授权：清除登录态并跳转登录页
      if (status === 401) {
        console.warn('[AuthInterceptor] 401未授权，跳转登录页')
        clearAuthAndRedirect(loginPath)
        return Promise.reject(error)
      }

      // 403 禁止访问：权限不足
      if (status === 403) {
        const errorMsg = (error.response?.data as any)?.message || '权限不足，无法访问'
        console.warn('[AuthInterceptor] 403禁止访问:', errorMsg)

        // 如果是API请求且不是静默模式，显示错误提示
        if (!config?.headers?.['X-Silent']) {
          // 可以在这里集成全局提示组件，比如Toast
          console.error('权限错误:', errorMsg)
        }

        return Promise.reject(error)
      }

      // 其他业务错误
      if (!config?.headers?.['X-Silent']) {
        const msg = (error.response?.data as any)?.message ||
                    error.response?.statusText ||
                    '请求失败'
        console.warn(`[API] ${config?.url}: ${msg}`)
      }

      return Promise.reject(error)
    }
  )
}

/**
 * 导出工具函数供外部使用
 */
export { parseJwtPayload, isTokenExpiringSoon, refreshAccessToken }