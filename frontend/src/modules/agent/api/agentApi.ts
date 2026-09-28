import request from '../../../shared/utils/request'
import { postSseConnection } from '../../../shared/utils/sse'

export function startTask() {
  return request.post('/agent/start')
}

export function getStatusSSE(
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void,
) {
  return postSseConnection('/agent/status', {}, onMessage, onError, onComplete)
}

/** 调用 Agent 生成资源内容（流式） */
export function generateResourceContent(
  resourceId: string,
  resourceInfo: {
    title: string
    type: string
    description?: string
    difficulty?: string
    duration?: string
  },
  onContent: (content: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void,
): () => void {
  const token = localStorage.getItem('token')
  const baseUrl = import.meta.env.DEV ? '/api/v1' : 'http://localhost:8000/api/v1'
  
  const controller = new AbortController()
  
  // 将资源信息作为查询参数传递
  const params = new URLSearchParams({
    resource_id: resourceId,
    title: resourceInfo.title,
    type: resourceInfo.type,
    description: resourceInfo.description || '',
    difficulty: resourceInfo.difficulty || 'basic',
    duration: resourceInfo.duration || '30分钟',
  })
  
  fetch(`${baseUrl}/agent/generate-content?${params.toString()}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      onError?.(new Error(`HTTP error: ${response.status}`))
      return
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      onError?.(new Error('No response body'))
      return
    }
    
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') {
            onComplete?.()
            return
          }
          try {
            const data = JSON.parse(dataStr)
            if (data.content) {
              onContent(data.content)
            }
            if (data.error) {
              onError?.(new Error(data.error))
            }
          } catch {
            // 忽略解析错误
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError?.(err)
    }
  })
  
  return () => controller.abort()
}