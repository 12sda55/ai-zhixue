/** 资源类型标签映射 */
export const RESOURCE_TYPE_MAP: Record<string, { label: string; icon: string; color: string }> = {
  document: { label: '文档', icon: '📄', color: '#00d4ff' },
  mindmap: { label: '导图', icon: '🗺️', color: '#22d3ee' },
  'knowledge-graph': { label: '知识图谱', icon: '🕸️', color: '#f59e0b' },
  exercise: { label: '习题', icon: '📝', color: '#a78bfa' },
  quiz: { label: '测验', icon: '✅', color: '#34d399' },
  code: { label: '代码', icon: '💻', color: '#6366f1' },
  video: { label: '视频', icon: '🎬', color: '#f59e0b' },
  extension: { label: '拓展', icon: '📖', color: '#34d399' },
}

/** 难度标签映射 — key 与 ResourceItem.difficulty 的值对齐 */
export const DIFFICULTY_MAP: Record<string, { label: string; color: string }> = {
  beginner: { label: '基础', color: '#34d399' },
  intermediate: { label: '中等', color: '#00d4ff' },
  advanced: { label: '进阶', color: '#a78bfa' },
  // 兼容旧数据
  basic: { label: '基础', color: '#34d399' },
  medium: { label: '中等', color: '#00d4ff' },
}

/** Agent 配置 */
export const AGENT_LIST = [
  { id: 'profile', name: '画像 Agent', role: '特征抽取 · 画像更新', icon: '👤', color: '#34d399' },
  { id: 'document', name: '文档 Agent', role: '课程讲解文档', icon: '📄', color: '#00d4ff' },
  { id: 'mindmap', name: '导图 Agent', role: '知识思维导图', icon: '🗺️', color: '#22d3ee' },
  { id: 'exercise', name: '题库 Agent', role: '分层难度习题', icon: '📝', color: '#a78bfa' },
  { id: 'code', name: '代码 Agent', role: '代码实操案例', icon: '💻', color: '#6366f1' },
  { id: 'video', name: '视频 Agent', role: '教学动画/视频', icon: '🎬', color: '#f59e0b' },
  { id: 'path', name: '路径 Agent', role: '学习路径规划', icon: '🗺️', color: '#a78bfa' },
  { id: 'knowledge-graph', name: '图谱 Agent', role: '知识关联图谱', icon: '🕸️', color: '#f59e0b' },
  { id: 'reviewer', name: '审查 Agent', role: '内容质量审查 · 问题修正', icon: '🔍', color: '#EA5455' },
]

/** 画像维度 — 雷达图 8 维 + 非雷达 3 维 */
export const PROFILE_DIMENSIONS = [
  // 雷达图维度（8维）
  { name: '基础水平', key: 'base_level', showOnRadar: true },
  { name: '薄弱知识点', key: 'weak_points', showOnRadar: true },
  { name: '学习目标', key: 'study_goal', showOnRadar: true },
  { name: '学习投入度', key: 'learning_engagement', showOnRadar: true },
  { name: '学习节奏', key: 'study_rhythm', showOnRadar: true },
  { name: '内容偏好', key: 'interest_preference', showOnRadar: true },
  { name: '知识掌握度', key: 'knowledge_mastery', showOnRadar: true },
  { name: '练习完成度', key: 'exercise_completion', showOnRadar: true },
  // 非雷达维度
  { name: '专业方向', key: 'major', showOnRadar: false },
  { name: '年级水平', key: 'grade', showOnRadar: false },
  { name: '认知风格', key: 'cognitive_style', showOnRadar: false },
]