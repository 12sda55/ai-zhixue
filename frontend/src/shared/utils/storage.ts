/**
 * 安全的 localStorage 操作工具
 * 统一处理 QuotaExceededError 和 JSON 解析错误
 */

/** 安全读取字符串 */
export function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    console.warn(`[Storage] 读取 ${key} 失败，localStorage 可能被禁用`)
    return null
  }
}

/** 安全写入字符串 */
export function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value)
    return true
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn(`[Storage] 写入 ${key} 失败，存储空间已满`)
    } else {
      console.warn(`[Storage] 写入 ${key} 失败`, e)
    }
    return false
  }
}

/** 安全删除 */
export function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    // 删除失败不需要警告
  }
}

/** 安全读取并解析 JSON */
export function safeGetJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return fallback
    return JSON.parse(raw) as T
  } catch {
    console.warn(`[Storage] 解析 ${key} 的 JSON 失败，使用默认值`)
    safeRemoveItem(key) // 清除损坏的数据
    return fallback
  }
}

/** 安全写入 JSON */
export function safeSetJSON(key: string, value: unknown): boolean {
  try {
    return safeSetItem(key, JSON.stringify(value))
  } catch {
    console.warn(`[Storage] 序列化 ${key} 失败`)
    return false
  }
}
