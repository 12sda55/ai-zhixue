/** 管理端 API */

import request from '../../../shared/utils/request'
import type {
  AdminStatsData,
  UserTrendItem,
  ResourceDistributionItem,
  AgentActivityItem,
  AdminNotificationItem,
  AdminUserListRes,
  AdminUserDetailRes,
  CourseListRes,
  ResourceListRes,
  KnowledgePointItem,
  AgentLogListRes,
  AgentStatsData,
  AgentConfigData,
  SettingsData,
  NotificationSettingItem,
  AuditLogListRes,
  AuditLogItem,
  ShareTokenData,
  ShareTokenListItem,
  HeatmapArea,
  RadarDimension,
  ResourceTrendDay,
  SystemMessage,
  DataScreenPublicData,
} from '../types'

// ============================================================
// Dashboard 统计
// ============================================================

export async function getAdminStats(): Promise<AdminStatsData> {
  return request.get('/admin/stats') as unknown as AdminStatsData
}

export async function getUsersTrend(days: number = 7): Promise<UserTrendItem[]> {
  return request.get('/admin/stats/users-trend', { params: { days } }) as unknown as UserTrendItem[]
}

export async function getResourceDistribution(): Promise<ResourceDistributionItem[]> {
  return request.get('/admin/stats/resource-distribution') as unknown as ResourceDistributionItem[]
}

export async function getAgentActivity(): Promise<AgentActivityItem[]> {
  return request.get('/admin/stats/agent-activity') as unknown as AgentActivityItem[]
}

// ============================================================
// 通知
// ============================================================

export async function getNotifications(params?: { type?: string; unread_only?: boolean; limit?: number }): Promise<AdminNotificationItem[]> {
  return request.get('/admin/notifications', { params }) as unknown as AdminNotificationItem[]
}

export async function markNotificationRead(notificationId: number): Promise<void> {
  return request.put(`/admin/notifications/${notificationId}/read`) as unknown as void
}

// ============================================================
// 用户管理
// ============================================================

export async function getUserList(params?: {
  page?: number
  page_size?: number
  keyword?: string
  role?: string
  status?: string
}): Promise<AdminUserListRes> {
  return request.get('/admin/users', { params }) as unknown as AdminUserListRes
}

export async function createUser(data: {
  username: string
  password: string
  email?: string
  role?: string
}): Promise<AdminUserDetailRes> {
  return request.post('/admin/users', data) as unknown as AdminUserDetailRes
}

export async function updateUser(userId: string, data: {
  username?: string
  email?: string
  role?: string
  password?: string
}): Promise<AdminUserDetailRes> {
  return request.put(`/admin/users/${userId}`, data) as unknown as AdminUserDetailRes
}

export async function deleteUser(userId: string): Promise<void> {
  return request.delete(`/admin/users/${userId}`) as unknown as void
}

export async function changeUserStatus(userId: string, status: string): Promise<void> {
  return request.put(`/admin/users/${userId}/status`, { status }) as unknown as void
}

export async function getUserDetail(userId: string): Promise<AdminUserDetailRes> {
  return request.get(`/admin/users/${userId}/detail`) as unknown as AdminUserDetailRes
}

export async function batchDeleteUsers(userIds: string[]): Promise<void> {
  return request.post('/admin/users/batch-delete', { user_ids: userIds }) as unknown as void
}

export async function batchChangeStatus(userIds: string[], status: string): Promise<void> {
  return request.post('/admin/users/batch-status', { user_ids: userIds, status }) as unknown as void
}

// ============================================================
// 课程管理
// ============================================================

export async function getCourseList(params?: {
  page?: number
  page_size?: number
  keyword?: string
}): Promise<CourseListRes> {
  return request.get('/admin/courses', { params }) as unknown as CourseListRes
}

export async function createCourse(data: {
  name: string
  description?: string
  chapters?: { title: string; order: number }[]
}): Promise<CourseListRes> {
  return request.post('/admin/courses', data) as unknown as CourseListRes
}

export async function updateCourse(courseId: number, data: {
  name?: string
  description?: string
  chapters?: { title: string; order: number }[]
  status?: string
}): Promise<CourseListRes> {
  return request.put(`/admin/courses/${courseId}`, data) as unknown as CourseListRes
}

export async function deleteCourse(courseId: number): Promise<void> {
  return request.delete(`/admin/courses/${courseId}`) as unknown as void
}

// ============================================================
// 资源管理
// ============================================================

export async function getResourceList(params?: {
  page?: number
  page_size?: number
  type?: string
  course_id?: number
}): Promise<ResourceListRes> {
  return request.get('/admin/resources', { params }) as unknown as ResourceListRes
}

/** Alias for ResourcesManageView */
export const getResourcesList = getResourceList

export async function createResource(data: {
  name: string
  type: string
  description?: string
  difficulty?: string
  duration?: string
  is_weak_point?: boolean
  content?: string
  course_id?: number
  knowledge_point_id?: number
  file_path?: string
  file_size?: number
}): Promise<ResourceListRes> {
  return request.post('/admin/resources', data) as unknown as ResourceListRes
}

export async function updateResource(resourceId: string, data: {
  name?: string
  type?: string
  description?: string
  difficulty?: string
  duration?: string
  is_weak_point?: boolean
  content?: string
  course_id?: number
  knowledge_point_id?: number
  status?: string
}): Promise<ResourceListRes> {
  return request.put(`/admin/resources/${resourceId}`, data) as unknown as ResourceListRes
}

export async function deleteResource(resourceId: string): Promise<void> {
  return request.delete(`/admin/resources/${resourceId}`) as unknown as void
}

// ============================================================
// 知识点管理
// ============================================================

export async function getKnowledgePoints(courseId?: number): Promise<KnowledgePointItem[]> {
  return request.get('/admin/knowledge-points', { params: { course_id: courseId } }) as unknown as KnowledgePointItem[]
}

export async function createKnowledgePoint(data: {
  course_id?: number
  name: string
  level?: number
  parent_id?: number
  description?: string
}): Promise<KnowledgePointItem> {
  return request.post('/admin/knowledge-points', data) as unknown as KnowledgePointItem
}

// ============================================================
// Agent 管理
// ============================================================

export async function getAgentList(): Promise<Record<string, unknown>[]> {
  return request.get('/admin/agents') as unknown as Record<string, unknown>[]
}

export async function getAgentLogs(agentId: string, params?: {
  page?: number
  page_size?: number
}): Promise<AgentLogListRes> {
  return request.get(`/admin/agents/${agentId}/logs`, { params }) as unknown as AgentLogListRes
}

export async function startAgent(agentId: string): Promise<void> {
  return request.post(`/admin/agents/${agentId}/start`) as unknown as void
}

export async function stopAgent(agentId: string): Promise<void> {
  return request.post(`/admin/agents/${agentId}/stop`) as unknown as void
}

export async function restartAgent(agentId: string): Promise<void> {
  return request.post(`/admin/agents/${agentId}/restart`) as unknown as void
}

export async function getAgentStats(): Promise<AgentStatsData> {
  return request.get('/admin/agents/stats') as unknown as AgentStatsData
}

// ============================================================
// Agent 配置
// ============================================================

export async function getAgentConfig(agentId: string): Promise<AgentConfigData> {
  return request.get(`/admin/agents/${agentId}/config`) as unknown as AgentConfigData
}

export async function updateAgentConfig(agentId: string, data: {
  name?: string
  description?: string
  model?: string
  temperature?: number
  max_tokens?: number
  system_prompt?: string
  enabled?: boolean
}): Promise<AgentConfigData> {
  return request.put(`/admin/agents/${agentId}/config`, data) as unknown as AgentConfigData
}

// ============================================================
// 系统设置
// ============================================================

export async function getSettings(): Promise<SettingsData> {
  return request.get('/admin/settings') as unknown as SettingsData
}

export async function updateSettings(data: {
  api_base_url?: string
  model_name?: string
  max_tokens?: number
  temperature?: number
  sse_enabled?: boolean
  auto_profile_update?: boolean
  auto_path_adjustment?: boolean
  debug_mode?: boolean
}): Promise<SettingsData> {
  return request.put('/admin/settings', data) as unknown as SettingsData
}

export async function clearCache(): Promise<void> {
  return request.post('/admin/settings/clear-cache') as unknown as void
}

export async function getNotificationSettings(): Promise<NotificationSettingItem[]> {
  return request.get('/admin/settings/notifications') as unknown as NotificationSettingItem[]
}

export async function updateNotificationSetting(type: string, data: {
  enabled: boolean
  config?: Record<string, unknown>
}): Promise<NotificationSettingItem> {
  return request.put(`/admin/settings/notifications/${type}`, data) as unknown as NotificationSettingItem
}

// ============================================================
// 审计日志
// ============================================================

export async function getAuditLogs(params?: {
  page?: number
  page_size?: number
  start_date?: string
  end_date?: string
  action_type?: string
  operator_id?: number
  keyword?: string
}): Promise<AuditLogListRes> {
  return request.get('/admin/audit-logs', { params }) as unknown as AuditLogListRes
}

export async function getAuditLogDetail(logId: number): Promise<AuditLogItem> {
  return request.get(`/admin/audit-logs/${logId}`) as unknown as AuditLogItem
}

export async function exportAuditLogs(params?: {
  start_date?: string
  end_date?: string
  action_type?: string
  operator_id?: number
  keyword?: string
}): Promise<Blob> {
  return request.get('/admin/audit-logs/export', { params, responseType: 'blob' }) as unknown as Blob
}

// ============================================================
// 数据大屏分享
// ============================================================

export async function createShareToken(expireHours: number = 24): Promise<ShareTokenData> {
  return request.post('/admin/data-screen/token', { expire_hours: expireHours }) as unknown as ShareTokenData
}

export async function getShareTokens(): Promise<ShareTokenListItem[]> {
  return request.get('/admin/data-screen/tokens') as unknown as ShareTokenListItem[]
}

export async function revokeShareToken(tokenId: number): Promise<void> {
  return request.delete(`/admin/data-screen/tokens/${tokenId}`) as unknown as void
}

// ============================================================
// 公开数据大屏
// ============================================================

export async function getDataScreenData(token: string): Promise<DataScreenPublicData> {
  return request.get('/public/data-screen', { params: { token } }) as unknown as DataScreenPublicData
}

// ============================================================
// 学习统计 & 画像统计（LearningStatsView 专用）
// ============================================================

export async function getLearningStats(params?: {
  period?: string
}): Promise<Record<string, unknown>> {
  return request.get('/admin/learning-stats', { params }) as unknown as Record<string, unknown>
}

export async function getProfileStats(): Promise<Record<string, unknown>> {
  return request.get('/admin/profile-stats') as unknown as Record<string, unknown>
}

// ============================================================
// 数据大屏扩展统计
// ============================================================

export async function getKnowledgeHeatmap(): Promise<HeatmapArea[]> {
  return request.get('/admin/stats/knowledge-heatmap') as unknown as HeatmapArea[]
}

export async function getRadarMatrix(): Promise<RadarDimension[]> {
  return request.get('/admin/stats/radar-matrix') as unknown as RadarDimension[]
}

export async function getResourceTrend(days: number = 7): Promise<ResourceTrendDay[]> {
  return request.get('/admin/stats/resource-trend', { params: { days } }) as unknown as ResourceTrendDay[]
}

export async function getSystemMessages(): Promise<SystemMessage[]> {
  return request.get('/admin/stats/system-messages') as unknown as SystemMessage[]
}
