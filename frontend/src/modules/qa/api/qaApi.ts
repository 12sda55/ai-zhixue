import { postSseConnection } from '../../../shared/utils/sse'

export function chatSSE(
  body: Record<string, unknown>,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void,
) {
  return postSseConnection('/qa/chat', body, onMessage, onError, onComplete)
}