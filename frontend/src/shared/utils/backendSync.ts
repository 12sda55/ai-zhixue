/**
 * 后端数据同步工具
 *
 * - backendOnline: 后端在线状态（响应式）
 * - syncToServer: 防抖保存数据到后端
 * - loadFromServer: 从后端加载数据
 * - 离线降级：后端不可用时自动使用 localStorage
 */

import { ref } from 'vue'

export const backendOnline = ref(true)

const API_BASE = import.meta.env.DEV
  ? '/api/v1'
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1')

/** 防抖定时器 */
const debounceTimers: Record<string, ReturnType<typeof setTimeout>> = {}

/** 检查 token 是否是后端 JWT */
function isJwtToken(token: string | null): boolean {
  if (!token) return false
  // JWT 格式: header.payload.signature（3 段 base64）
  return token.split('.').length === 3
}

/** 检查 JWT 是否过期 */
function isJwtExpired(token: string | null): boolean {
  if (!token || !isJwtToken(token)) return true
  try {
    // JWT 格式: header.payload.signature
    const payload = token.split('.')[1]
    // Base64 解码（可能需要补齐 padding）
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
    const decoded = JSON.parse(atob(padded))
    // exp 是秒级时间戳
    if (decoded.exp && decoded.exp * 1000 < Date.now()) {
      return true
    }
    return false
  } catch {
    // 解析失败，视为过期
    return true
  }
}

/**
 * 保存数据到后端（防抖 1s）
 */
export function syncToServer(storeName: string, data: unknown, debounceMs = 1000) {
  const key = `sync_${storeName}`
  if (debounceTimers[key]) clearTimeout(debounceTimers[key])

  debounceTimers[key] = setTimeout(async () => {
    const token = localStorage.getItem('token')
    // 只有有效的 JWT token 才发后端请求（过期则跳过）
    if (!isJwtToken(token) || isJwtExpired(token)) return
    if (!backendOnline.value) return

    try {
      const res = await fetch(`${API_BASE}/data/${storeName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ data }),
      })

      if (res.ok) {
        backendOnline.value = true
      } else if (res.status === 401) {
        // JWT 过期或无效 — 不标记后端离线，但静默跳过
        console.warn(`[Sync] ${storeName}: JWT 无效或过期，跳过后端同步`)
      } else {
        backendOnline.value = false
        console.warn(`[Sync] 保存 ${storeName} 失败: ${res.status}`)
      }
    } catch {
      backendOnline.value = false
      console.warn(`[Sync] 后端不可达，${storeName} 保存跳过`)
    }
  }, debounceMs)
}

/**
 * 从后端加载数据
 * @returns 数据对象或 null
 */
export async function loadFromServer(storeName: string): Promise<unknown | null> {
  const token = localStorage.getItem('token')
  // 只有有效的 JWT token 才发后端请求（过期则跳过）
  if (!isJwtToken(token) || isJwtExpired(token)) return null

  try {
    const res = await fetch(`${API_BASE}/data/${storeName}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })

    if (res.ok) {
      backendOnline.value = true
      const json = await res.json()
      return json.data
    }

    if (res.status === 401) {
      // JWT 过期，静默跳过
      console.warn(`[Sync] ${storeName}: JWT 无效或过期，使用本地数据`)
      return null
    }

    if (res.status === 404) {
      // 后端没有该路由或数据不存在，静默跳过（首次使用时正常）
      return null
    }

    backendOnline.value = false
    return null
  } catch {
    backendOnline.value = false
    return null
  }
}

/**
 * 检测后端健康状态
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
    const online = res.ok
    backendOnline.value = online
    return online
  } catch {
    backendOnline.value = false
    return false
  }
}
