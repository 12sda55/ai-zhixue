/** SSE 连接封装 */
interface SseOptions {
  url: string
  onMessage: (data: string) => void
  onError?: (error: Event) => void
  onComplete?: () => void
}

export function createSseConnection(options: SseOptions): EventSource {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const fullURL = `${baseURL}${options.url}`

  const eventSource = new EventSource(fullURL)

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close()
      options.onComplete?.()
      return
    }
    options.onMessage(event.data)
  }

  eventSource.onerror = (error) => {
    console.error('[SSE Error]', error)
    eventSource.close()
    options.onError?.(error)
  }

  return eventSource
}

/** POST 方式 SSE（用于需要 body 的流式请求） */
export async function postSseConnection(
  url: string,
  body: Record<string, unknown>,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void,
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const fullURL = `${baseURL}${url}`

  try {
    const response = await fetch(fullURL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = '' // 缓冲跨 chunk 的部分行

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 保留最后一个可能不完整的行
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6)
          if (data === '[DONE]') {
            onComplete?.()
            return
          }
          onMessage(data)
        }
      }
    }

    // 处理 buffer 中剩余的数据
    if (buffer.trim().startsWith('data: ')) {
      const data = buffer.trim().slice(6)
      if (data !== '[DONE]') {
        onMessage(data)
      }
    }

    onComplete?.()
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error(String(err)))
  }
}