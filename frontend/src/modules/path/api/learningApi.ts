/**学习行为记录 API - 记录学员学习行为，用于动态更新画像 */

import type { ApiResponse } from '../../../shared/types'

const API_BASE = '/api/v1/learning'

/** 开始学习 */
export async function startLearning(data: {
  resource_id: string
  resource_type: string
  resource_name: string
  stage_id: string
}): Promise<ApiResponse<{ record_id: string; message: string }>> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })
  return res.json()
}

/** 完成学习 */
export async function completeLearning(data: {
  resource_id: string
  reading_time: number
  scroll_depth: number
  quiz_score?: number
  feedback?: string
}): Promise<ApiResponse<{ record_id: string; message: string }>> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })
  return res.json()
}

/** 保存资源内容 */
export async function saveContent(data: {
  resource_id: string
  content: string
  generated_by?: string
  generation_time?: number
}): Promise<ApiResponse<{ message: string }>> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/content`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })
  return res.json()
}

/** 获取资源内容 */
export async function getContent(resourceId: string): Promise<ApiResponse<{
  content: string
  generated_by: string
  created_at: string
}>> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/content/${resourceId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  if (!res.ok) {
    return { success: false, message: '内容不存在' }
  }
  return res.json()
}

/** 获取学习记录 */
export async function getLearningRecords(): Promise<ApiResponse<{
  records: Array<{
    id: string
    resource_id: string
    resource_type: string
    resource_name: string
    reading_time: number
    scroll_depth: float
    is_completed: number
    completed_at: string | null
    created_at: string
  }>
}>> {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/records`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  return res.json()
}