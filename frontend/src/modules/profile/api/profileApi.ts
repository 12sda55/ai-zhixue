import request from '../../../shared/utils/request'
import { postSseConnection } from '../../../shared/utils/sse'
import type { ProfileData } from '../../../shared/types'

/** 获取画像数据（雷达图 + 完整画像） */
export function getRadarData() {
  return request.get<ProfileData>('/data/profile')
}

/** SSE 流式对话 */
export function chatSSE(
  message: string,
  onMessage: (data: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
) {
  return postSseConnection(
    '/data/profile/chat',
    { message },
    onMessage,
    onError,
    onComplete
  )
}

/** 保存画像数据 */
export function saveProfile(data: {
  weak_points?: string[]
  base_level?: string
  study_goal?: string
  cognitive_style?: string
  study_rhythm?: string
  interest_preference?: string
  profile_data?: any
}) {
  return request.put('/data/profile', { data })
}

/** 画像历史相关 API */

export interface ProfileHistoryItem {
  id: string
  name: string
  major: string
  grade: string
  weak_points_summary: string
  base_level: string
  is_active: number
  created_at: string
  updated_at: string
}

/** 保存画像到历史记录 */
export function saveProfileHistory(data: {
  name?: string
  profile_data: any
}) {
  return request.post('/data/profile/history/save', { data })
}

/** 获取画像历史列表 */
export function getProfileHistoryList() {
  return request.get<{ success: boolean; histories: ProfileHistoryItem[]; total: number }>('/data/profile/history/list')
}

/** 获取某个历史画像详情 */
export function getProfileHistoryDetail(historyId: string) {
  return request.get(`/data/profile/history/${historyId}`)
}

/** 激活某个历史画像 */
export function activateProfileHistory(historyId: string) {
  return request.post(`/data/profile/history/${historyId}/activate`)
}

/** 删除某个历史画像 */
export function deleteProfileHistory(historyId: string) {
  return request.delete(`/data/profile/history/${historyId}`)
}

/** 获取完整画像数据 */
export function getFullProfile() {
  return request.get('/data/profile')
}
