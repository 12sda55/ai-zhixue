import type { LoginResponse, UserRole } from '../../../shared/types'

const API_BASE = import.meta.env.DEV
  ? '/api/v1'
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1')

/** 登录失败计数 */
const LOGIN_LOCK_THRESHOLD = 5
const LOGIN_LOCK_DURATION = 15 * 60 * 1000 // 15分钟

function getFailCount(username: string): number {
  const count = localStorage.getItem(`login_fail_count_${username}`)
  return count ? parseInt(count) : 0
}

function setFailCount(username: string, count: number) {
  localStorage.setItem(`login_fail_count_${username}`, String(count))
}

function clearFailCount(username: string) {
  localStorage.removeItem(`login_fail_count_${username}`)
  localStorage.removeItem(`login_lock_${username}`)
}

export function isAccountLocked(username: string): { locked: boolean; remainingSeconds: number } {
  const lockTimestamp = localStorage.getItem(`login_lock_${username}`)
  if (!lockTimestamp) return { locked: false, remainingSeconds: 0 }

  const lockTime = parseInt(lockTimestamp)
  const unlockTime = lockTime + LOGIN_LOCK_DURATION
  const remaining = Math.max(0, Math.ceil((unlockTime - Date.now()) / 1000))

  if (remaining <= 0) {
    localStorage.removeItem(`login_lock_${username}`)
    setFailCount(username, 0)
    return { locked: false, remainingSeconds: 0 }
  }

  return { locked: true, remainingSeconds: remaining }
}

function lockAccount(username: string) {
  localStorage.setItem(`login_lock_${username}`, String(Date.now()))
}

function parseLoginResponse(data: any): LoginResponse {
  return {
    token: data.token || data.access_token,
    user: {
      id: String(data.user.id),
      username: data.user.username,
      email: data.user.email || '',
      role: data.user.role || 'student',
      createdAt: data.user.created_at || new Date().toISOString().slice(0, 10),
      status: data.user.status || 'active',
    },
  }
}

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const { locked, remainingSeconds } = isAccountLocked(username)
  if (locked) {
    throw new Error(`账户已锁定，请等待 ${Math.floor(remainingSeconds / 60)} 分 ${remainingSeconds % 60} 秒后重试`)
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
  } catch (e: any) {
    throw new Error('无法连接服务器，请检查网络或后端服务是否启动')
  }

  if (res.ok) {
    clearFailCount(username)
    const data = await res.json()
    return parseLoginResponse(data)
  }

  if (res.status === 401 || res.status === 403) {
    const failCount = getFailCount(username) + 1
    setFailCount(username, failCount)
    if (failCount >= LOGIN_LOCK_THRESHOLD) {
      lockAccount(username)
      throw new Error('登录失败次数过多，账户已被锁定15分钟')
    }
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '用户名或密码错误')
  }

  const err = await res.json().catch(() => ({}))
  throw new Error(err.detail || `登录失败 (${res.status})`)
}

/** 管理员邀请码（可配置） */
const ADMIN_INVITE_CODES = ['ADM2026', 'ZHIXUE2026', 'ADMIN001']

export async function registerApi(data: { username: string; password: string; email?: string; role: UserRole; inviteCode?: string }): Promise<LoginResponse> {
  if (data.role === 'admin') {
    if (!data.inviteCode || !ADMIN_INVITE_CODES.includes(data.inviteCode.trim().toUpperCase())) {
      throw new Error('邀请码无效，无法注册管理员账户')
    }
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: data.username, password: data.password, email: data.email, role: data.role, invite_code: data.inviteCode }),
    })
  } catch (e: any) {
    throw new Error('无法连接服务器，请检查网络或后端服务是否启动')
  }

  if (res.ok) {
    const regData = await res.json()
    return parseLoginResponse(regData)
  }

  if (res.status === 400) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '用户名已存在')
  }

  if (res.status === 403) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '邀请码无效')
  }

  const err = await res.json().catch(() => ({}))
  throw new Error(err.detail || `注册失败 (${res.status})`)
}

export async function refreshTokenApi(token: string): Promise<LoginResponse> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
    })
  } catch (e: any) {
    throw new Error('无法连接服务器')
  }

  if (res.ok) {
    const data = await res.json()
    return parseLoginResponse(data)
  }

  throw new Error('Token 已过期，请重新登录')
}

export async function resetPasswordApi(username: string, newPassword: string): Promise<{ success: boolean }> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, new_password: newPassword }),
    })
  } catch (e: any) {
    throw new Error('无法连接服务器')
  }

  if (res.ok) {
    return { success: true }
  }

  const err = await res.json().catch(() => ({}))
  throw new Error(err.detail || '重置密码失败')
}

/** 检查密码强度 */
export function checkPasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (!password || password.length < 6) return 'weak'
  if (/^(?=.*[0-9])(?=.*[a-zA-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/.test(password)) {
    return 'strong'
  }
  if (/^(?=.*[0-9])(?=.*[a-zA-Z]).{6,}$/.test(password)) {
    return 'medium'
  }
  return 'weak'
}

/** 验证密码格式 */
export function validatePassword(password: string): { valid: boolean; message: string } {
  if (!password || password.length < 6) {
    return { valid: false, message: '密码至少需要6位' }
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, message: '密码必须包含数字' }
  }
  if (!/[a-zA-Z]/.test(password)) {
    return { valid: false, message: '密码必须包含字母' }
  }
  return { valid: true, message: '' }
}

/** 验证用户名格式 */
export function validateUsername(username: string): { valid: boolean; message: string } {
  if (!username || username.length < 3) {
    return { valid: false, message: '用户名至少需要3个字符' }
  }
  if (!/^[a-zA-Z0-9_一-龥]+$/.test(username)) {
    return { valid: false, message: '用户名只能包含字母、数字、下划线或中文' }
  }
  return { valid: true, message: '' }
}

/** 验证邮箱格式 */
export function validateEmail(email: string): { valid: boolean; message: string } {
  if (!email) return { valid: true, message: '' }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email)) {
    return { valid: false, message: '请输入有效的邮箱地址' }
  }
  return { valid: true, message: '' }
}
