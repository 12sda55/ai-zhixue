/**
 * 管理端 API 响应类型定义
 * 与后端 schemas/admin_extended.py 对齐
 */

// ===== Dashboard 统计 =====

export interface AdminStatsData {
  total_users: number
  active_users: number
  total_profiles: number
  total_resources: number
  total_assessments: number
  assessment_completion_rate: number
}

export interface UserTrendItem {
  date: string
  count: number
}

export interface ResourceDistributionItem {
  type: string
  count: number
}

export interface AgentActivityItem {
  agent_id: string
  agent_name: string
  call_count: number
  success_count: number
}

// ===== 通知 =====

export interface AdminNotificationItem {
  id: number
  type: string
  title: string
  content: string | null
  target_id: number | null
  is_read: boolean
  created_at: string | null
}

// ===== 用户管理 =====

export interface AdminUserItem {
  id: string
  username: string
  email: string | null
  role: string
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface AdminUserListRes {
  items: AdminUserItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminUserDetailRes {
  user: AdminUserItem
  profile: Record<string, unknown> | null
  resources: Record<string, unknown>[]
  paths: Record<string, unknown>[]
  assessments: Record<string, unknown>[]
}

// ===== 课程管理 =====

export interface ChapterItem {
  title: string
  order: number
}

export interface CourseItem {
  id: number
  name: string
  description: string | null
  chapters: ChapterItem[] | null
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface CourseListRes {
  items: CourseItem[]
  total: number
  page: number
  page_size: number
}

// ===== 资源管理 =====

export interface AdminResourceItem {
  id: number
  name: string
  type: string
  course_id: number | null
  knowledge_point_id: number | null
  file_path: string | null
  file_size: number | null
  description: string | null
  status: string
  created_by: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ResourceListRes {
  items: AdminResourceItem[]
  total: number
  page: number
  page_size: number
}

// ===== 知识点 =====

export interface KnowledgePointItem {
  id: number
  course_id: number | null
  name: string
  level: number
  parent_id: number | null
  description: string | null
  created_at: string | null
}

// ===== Agent 管理 =====

export interface AgentLogItem {
  id: number
  agent_id: string
  agent_name: string | null
  status: string
  input_data: Record<string, unknown> | null
  output_data: Record<string, unknown> | null
  error_message: string | null
  time_used: number | null
  started_at: string | null
  completed_at: string | null
}

export interface AgentLogListRes {
  items: AgentLogItem[]
  total: number
  page: number
  page_size: number
}

export interface AgentStatsData {
  total_calls: number
  success_rate: number
  avg_time: number
  by_agent: Record<string, { calls: number; success: number }>
}

export interface AgentConfigData {
  name: string
  description: string | null
  model: string
  temperature: number
  max_tokens: number
  system_prompt: string | null
  enabled: boolean
}

// ===== 系统设置 =====

export interface SettingsData {
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  sse_enabled: boolean
  auto_profile_update: boolean
  auto_path_adjustment: boolean
  debug_mode: boolean
}

export interface NotificationSettingItem {
  id: number
  type: string
  enabled: boolean
  config: Record<string, unknown> | null
}

// ===== 审计日志 =====

export interface AuditLogItem {
  id: number
  operator_id: string
  operator_name: string | null
  action_type: string
  target_type: string | null
  target_id: number | null
  target_name: string | null
  detail: Record<string, unknown> | null
  ip_address: string | null
  created_at: string | null
}

export interface AuditLogListRes {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}

// ===== 数据大屏分享 =====

export interface ShareTokenData {
  token: string
  url: string
  expires_at: string
  created_at: string
}

export interface ShareTokenListItem {
  id: number
  token: string
  created_at: string
  expires_at: string
  is_active: boolean
}

// ===== 数据大屏扩展统计 =====

export interface HeatmapArea {
  area: string
  levels: { level: number; value: number }[]
}

export interface RadarDimension {
  name: string
  value: number
}

export interface ResourceTrendDay {
  date: string
  total: number
  by_type: Record<string, number>
}

export interface SystemMessage {
  time: string
  text: string
}

// ===== 数据大屏公开接口 =====

export interface DataScreenPublicData {
  stats: AdminStatsData
  user_trend: UserTrendItem[]
  resource_distribution: ResourceDistributionItem[]
  knowledge_heatmap: HeatmapArea[]
  agent_stats: AgentStatsData
  radar_matrix: RadarDimension[]
}
