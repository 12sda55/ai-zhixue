/**
 * GLM API 调用 — 通过后端代理（API Key 安全）
 *
 * 后端代理模式：前端不再直接调用 DeepSeek API，所有请求经过 /api/v1/glm/chat
 * API Key 存储在后端 .env 中，前端不暴露
 * 离线降级：后端不可用时，自动切换为直连模式（使用 localStorage 中缓存的前端 Key）
 *
 * 内置请求队列：最多同时 2 个并发请求，超出排队等候
 */

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

const MODEL = import.meta.env.VITE_GLM_MODEL || 'deepseek-v4-flash'

/** 后端代理地址 */
const PROXY_BASE = import.meta.env.DEV
  ? '/api/v1/glm'
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1') + '/glm'

/** 离线降级：直连 DeepSeek（仅在代理不可用时使用） */
const FALLBACK_BASE = import.meta.env.VITE_GLM_BASE_URL || 'https://api.deepseek.com'
const FALLBACK_KEY = import.meta.env.VITE_GLM_API_KEY || ''  // 离线降级用

/** 最大重试次数 */
const MAX_RETRIES = 2
/** 重试间隔 (ms) */
const RETRY_DELAY = 1500

/* ===== 请求并发控制 ===== */
const MAX_CONCURRENT = 2
let activeCount = 0
const pendingQueue: (() => void)[] = []

function acquire(): Promise<void> {
  if (activeCount < MAX_CONCURRENT) {
    activeCount++
    return Promise.resolve()
  }
  return new Promise<void>(resolve => {
    pendingQueue.push(() => {
      activeCount++
      resolve()
    })
  })
}

function release() {
  activeCount--
  if (pendingQueue.length > 0) {
    const next = pendingQueue.shift()!
    next()
  }
}

/* ===== 后端在线状态 ===== */
let _backendOnline = true  // 默认尝试后端

function getJwtToken(): string | null {
  const token = localStorage.getItem('token')
  if (!token) return null
  // JWT 格式: xxx.yyy.zzz（3段 base64），mock token: mock-token-xxx
  if (token.split('.').length !== 3 || token.startsWith('mock-token')) return null
  return token
}

/** 检查 JWT 是否过期 */
function isJwtExpired(token: string | null): boolean {
  if (!token) return true
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

/** 检查是否有有效的 JWT token（非 mock 且未过期） */
function hasValidJwtToken(): boolean {
  const token = getJwtToken()
  return token !== null && !isJwtExpired(token)
}

/**
 * 流式调用 GLM API（后端代理优先，离线降级到直连）
 * 返回 AbortController，可取消请求
 */
export function chatGLM(
  messages: ChatMessage[],
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: Error) => void,
): AbortController {
  const controller = new AbortController()

  let attempt = 0
  let useProxy = _backendOnline && hasValidJwtToken()  // 没有 JWT token 或已过期则跳过代理

  // 如果既没有有效 JWT 也没有配置直连 API Key，直接触发错误让调用方使用本地 fallback
  if (!useProxy && !FALLBACK_KEY) {
    console.warn('[GLM] 无有效认证方式（JWT 过期且未配置直连 Key），触发本地 fallback')
    // 异步触发错误，让调用方的 onError 回调执行
    setTimeout(() => {
      onError(new Error('无有效认证方式，请使用本地生成'))
    }, 0)
    return controller
  }

  // 等待并发槽位
  acquire().then(() => {
    attemptRequest()
  })

  return controller

  async function attemptRequest() {
    attempt++

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      let url: string
      if (useProxy) {
        url = `${PROXY_BASE}/chat`
        const token = getJwtToken()
        if (token) headers['Authorization'] = `Bearer ${token}`
      } else {
        // 离线降级：直连 DeepSeek
        url = `${FALLBACK_BASE}/chat/completions`
        if (FALLBACK_KEY) headers['Authorization'] = `Bearer ${FALLBACK_KEY}`
      }

      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: MODEL,
          messages,
          stream: true,
          temperature: 0.7,
          max_tokens: 4096,
        }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const body = await res.text().catch(() => '')

        // 401 可能是 JWT 过期 — 尝试降级到直连
        if (res.status === 401 && useProxy && attempt === 1) {
          console.warn('[GLM] 后端认证失败，尝试直连降级...')
          useProxy = false
          _backendOnline = false
          return attemptRequest()
        }

        // 后端完全不可达 — 降级到直连
        if (res.status === 0 || res.status >= 500 && useProxy && attempt === 1) {
          console.warn('[GLM] 后端不可达，切换直连模式...')
          useProxy = false
          _backendOnline = false
          return attemptRequest()
        }

        // 402 余额不足 — 不重试，直接报错
        if (res.status === 402) {
          throw new Error('API 余额不足，请检查账户余额或更换 API Key')
        }

        // 429 限流 — 可重试
        if (res.status === 429 && attempt <= MAX_RETRIES) {
          await delay(RETRY_DELAY * attempt)
          return attemptRequest()
        }

        throw new Error(`API ${res.status}: ${body.slice(0, 200)}`)
      }

      // 成功 → 标记后端在线
      if (useProxy) _backendOnline = true

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data: ')) continue

          const data = trimmed.slice(6)
          if (data === '[DONE]') {
            release()
            onDone()
            return
          }

          try {
            const json = JSON.parse(data)

            if (json.error) {
              throw new Error(`流式错误: ${json.error.message || JSON.stringify(json.error)}`)
            }

            const content = json.choices?.[0]?.delta?.content
            if (content) onChunk(content)
          } catch (parseErr: any) {
            if (parseErr.message?.includes('错误') || parseErr.message?.includes('流式')) throw parseErr
          }
        }
      }

      // 流结束但没收到 [DONE]
      release()
      onDone()
    } catch (err: any) {
      // 用户主动取消 — 不触发错误
      if (err.name === 'AbortError') {
        release()
        return
      }

      // 打印完整错误信息用于诊断
      console.log('[GLM] 捕获错误:', err.name, err.message, err.type, err)

      // ERR_ABORTED 或网络层面的中止 — 触发本地 fallback（优先处理）
      // 错误可能在 err.message、err.reason 或 err 本身
      const errMsg = err.message || err.reason?.message || err.toString?.() || String(err)
      const isAbortOrNetwork = 
        err.name === 'TypeError' ||  // fetch 失败通常是 TypeError
        errMsg.includes('ERR_ABORTED') || 
        errMsg.includes('net::ERR') || 
        errMsg.includes('Failed to fetch') ||
        errMsg.includes('NetworkError') ||
        err.type === 'error'
      
      if (isAbortOrNetwork) {
        console.warn('[GLM] 网络请求失败，触发本地 fallback')
        release()
        onError(new Error('API 请求失败，请使用本地生成'))
        return
      }

      // 网络错误 — 尝试降级到直连
      if (isNetworkError(err) && useProxy && attempt === 1) {
        // 如果没有配置直连 API Key，直接触发本地 fallback
        if (!FALLBACK_KEY) {
          console.warn('[GLM] 网络错误且未配置直连 Key，触发本地 fallback')
          release()
          onError(new Error('网络错误，请使用本地生成'))
          return
        }
        console.warn('[GLM] 网络错误，切换直连模式...')
        useProxy = false
        _backendOnline = false
        return attemptRequest()
      }

      // 直连模式失败 — 触发本地 fallback
      if (!useProxy && attempt >= 1) {
        console.warn('[GLM] 直连失败，触发本地 fallback')
        release()
        onError(new Error('API 调用失败，请使用本地生成'))
        return
      }

      // 降级模式下也网络错误 — 可重试
      if (isNetworkError(err) && attempt <= MAX_RETRIES) {
        await delay(RETRY_DELAY * attempt)
        return attemptRequest()
      }

      release()
      onError(err instanceof Error ? err : new Error(String(err)))
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function isNetworkError(err: any): boolean {
  return err.name === 'TypeError' || err.name === 'NetworkError'
    || err.message?.includes('Failed to fetch')
    || err.message?.includes('NetworkError')
    || err.message?.includes('net::')
}

/** 检查后端是否在线 */
export function isBackendOnline(): boolean {
  return _backendOnline
}