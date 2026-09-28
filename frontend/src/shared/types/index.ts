export type AgentStatus = 'idle' | 'running' | 'completed' | 'error'

export type UserRole = 'student' | 'admin'

export interface AgentInfo {
  id: string
  name: string
  role: string
  status: AgentStatus
  progress: number
  color: string
  icon: string
  log: string[]
  duration?: string
  calls?: number
  avgTime?: string
}

/* ===== 8 维度画像枚举约束 ===== */

export type ProfileMajor = '计算机科学' | '软件工程' | '信息技术' | '电子工程' | '数学' | '其他'
export type ProfileGrade = '大一' | '大二' | '大三' | '大四' | '研究生' | '其他'
export type ProfileBaseLevel = '入门' | '基础' | '中等' | '进阶' | '精通'
export type ProfileStudyGoal = '考试通关' | '竞赛提升' | '项目实战' | '全面掌握' | '兴趣探索'
export type ProfileCognitiveStyle = '视觉型' | '听觉型' | '实践型' | '理论型' | '混合型'
export type ProfileStudyRhythm = '碎片化' | '适中节奏' | '深度沉浸' | '突击式'
export type ProfileInterestPreference = '视频教程' | '文档阅读' | '代码实操' | '思维导图' | '互动练习' | '综合型'

/* ===== 画像维度系统 ===== */

/** 雷达图上显示的维度 key（8 维，动态可变） */
export type ProfileDimensionKey = 'base_level' | 'weak_points' | 'study_goal' | 'learning_engagement' | 'study_rhythm' | 'interest_preference' | 'knowledge_mastery' | 'exercise_completion'

/** 非雷达维度 key（仅存储在已采集维度中，不显示在雷达图上） */
export type ProfileNonRadarKey = 'major' | 'grade' | 'cognitive_style'

/** 所有维度 key 的联合类型 */
export type ProfileAllDimensionKey = ProfileDimensionKey | ProfileNonRadarKey

export interface ProfileDimension {
  key: ProfileAllDimensionKey
  name: string
  value: number
  label: string
  color?: string
  enumValue?: string
  /** 是否在雷达图上显示 */
  showOnRadar?: boolean
  /** 枚举映射的基础分（由对话设定） */
  baseScore: number
  /** 行为增量（由学习行为叠加，上限为基础分的30%） */
  bonus: number
}

/** 画像更新触发源 */
export type ProfileUpdateSource = 'path_complete' | 'resource_complete' | 'assess_complete' | 'dialogue' | 'manual'

/** 画像更新记录条目 */
export interface ProfileUpdateLog {
  id: string
  timestamp: string
  source: ProfileUpdateSource
  /** 触发更新的具体描述，如 "完成了阶段：树与二叉树" */
  description: string
  /** 本次变更的维度 key → 变更前后值 */
  changes: Record<ProfileAllDimensionKey, { before: number; after: number; beforeLabel: string; afterLabel: string }>
  /** 变更的维度数量 */
  affectedCount: number
}

/** 学习事件（用于驱动画像增量更新） */
export interface LearningEvent {
  type: 'stage_complete' | 'resource_complete' | 'assess_complete'
  timestamp: string
  /** 事件来源 ID（阶段ID/资源ID/测评ID） */
  sourceId: string
  /** 事件描述 */
  description: string
  /** 关联知识点 */
  knowledgePoints: string[]
  /** 测评得分（仅 assess_complete） */
  score?: number
  /** 资源类型（仅 resource_complete） */
  resourceType?: ResourceType
}

export interface ProfileData {
  dimensions: ProfileDimension[]
  major: ProfileMajor
  grade: ProfileGrade
  base_level: ProfileBaseLevel
  weak_points: string[]
  study_goal: ProfileStudyGoal
  cognitive_style: ProfileCognitiveStyle
  study_rhythm: ProfileStudyRhythm
  interest_preference: ProfileInterestPreference
  /** 画像阶段：initial → supplement → stable */
  phase: 'initial' | 'supplement' | 'stable'
  /** 当前引导轮次 (0=未开始, 1-4=初始构建轮次) */
  dialogueRound: number
  /** 画像更新历史 */
  updateLogs: ProfileUpdateLog[]
  /** 累计学习事件 */
  learningEvents: LearningEvent[]
  /** 最后更新时间 */
  lastUpdatedAt: string
  /** 已掌握的知识点（从薄弱点中移除的） */
  masteredPoints: string[]
  /** 累计学习时长（分钟） */
  totalStudyMinutes: number
  /** 连续学习天数 */
  streakDays: number
  /** 已完成资源数 */
  completedResourceCount: number
  /** 已完成阶段数 */
  completedStageCount: number
  /** 已完成测评数 */
  completedAssessCount: number
  /** 知识掌握度 (0-100) */
  knowledge_mastery: number
  /** 练习完成度 (0-100) */
  exercise_completion: number
  /** 学习投入度 (0-100) */
  learning_engagement: number
  /** 初始画像快照（phase→stable时自动记录，作为对比基准） */
  initialSnapshot?: RadarInitialSnapshot
  /** 保存的快照列表（完美/手动保存的画像） */
  snapshots?: RadarSnapshot[]
  /** 当前活跃科目（AI推断或用户指定） */
  currentSubject?: string
  /** 科目覆盖层列表（每个科目独立的画像维度） */
  subjectOverlays?: SubjectOverlay[]
}

/** 科目覆盖层：每个科目独立维护的画像维度 */
export interface SubjectOverlay {
  /** 科目名称 */
  subject: string
  /** 该科目的基础水平 */
  base_level: string
  /** 该科目的薄弱知识点 */
  weak_points: string[]
  /** 该科目的学习目标 */
  study_goal: string
  /** 该科目的知识掌握度 (0-100) */
  knowledge_mastery: number
  /** 该科目的练习完成度 (0-100) */
  exercise_completion: number
  /** 该科目已完成资源数 */
  completedResourceCount: number
  /** 该科目已完成阶段数 */
  completedStageCount: number
  /** 该科目已完成测评数 */
  completedAssessCount: number
  /** 该科目已掌握的知识点 */
  masteredPoints: string[]
  /** 最后更新时间 */
  lastUpdatedAt: string
}

/** weak_points 计分规则标记 */
export const WEAK_POINTS_COUNT_RULE = 'reverse' as const

/* ===== 完美雷达图展馆 — 快照类型 ===== */

/** 初始画像快照（phase→stable时自动记录） */
export interface RadarInitialSnapshot {
  dimensions: { key: string; name: string; value: number; label: string }[]
  createdAt: string
}

/** 保存的雷达图快照 */
export interface RadarSnapshot {
  id: string
  title: string
  description?: string
  createdAt: string
  /** 快照对应的科目（多科目支持） */
  subject?: string
  dimensions: { key: string; name: string; value: number; label: string }[]
  totalScore: number
  growthFromInitial: number
  isPerfect: boolean
  summary: {
    studyMinutes: number
    completedStages: number
    completedResources: number
    completedAssess: number
    streakDays: number
  }
  profileData: ProfileData
  initialSnapshot?: RadarInitialSnapshot
}

/** 画像维度 → 分数映射表 */
export const ENUM_SCORE_MAP: Record<string, Record<string, number | typeof WEAK_POINTS_COUNT_RULE>> = {
  major: {
    '计算机科学': 90, '软件工程': 85, '信息技术': 70, '电子工程': 60, '数学': 80, '其他': 40,
  },
  grade: {
    '大一': 20, '大二': 40, '大三': 65, '大四': 85, '研究生': 95, '其他': 30,
  },
  base_level: {
    '入门': 10, '基础': 30, '中等': 55, '进阶': 75, '精通': 95,
  },
  weak_points: {
    // weak_points 使用长度反向评分：越少薄弱点分数越高
    _countRule: WEAK_POINTS_COUNT_RULE,
  },
  study_goal: {
    '考试通关': 40, '竞赛提升': 70, '项目实战': 80, '全面掌握': 95, '兴趣探索': 50,
  },
  cognitive_style: {
    '视觉型': 65, '听觉型': 60, '实践型': 80, '理论型': 70, '混合型': 85,
  },
  study_rhythm: {
    '碎片化': 30, '适中节奏': 60, '深度沉浸': 90, '突击式': 40,
  },
  interest_preference: {
    '视频教程': 60, '文档阅读': 55, '代码实操': 85, '思维导图': 70, '互动练习': 75, '综合型': 90,
  },
  // 新增动态维度（无固定枚举，由计算属性驱动）
  knowledge_mastery: {},
  exercise_completion: {},
  learning_engagement: {},
}

/** 维度元数据（名称、图标、颜色） */
export const DIMENSION_META: Record<ProfileAllDimensionKey, { name: string; icon: string; color: string; showOnRadar: boolean }> = {
  // === 雷达图维度（8 维） ===
  base_level: { name: '基础水平', icon: '💡', color: '#00d4ff', showOnRadar: true },
  weak_points: { name: '薄弱知识点', icon: '⚡', color: '#f59e0b', showOnRadar: true },
  study_goal: { name: '学习目标', icon: '🎯', color: '#34d399', showOnRadar: true },
  learning_engagement: { name: '学习投入度', icon: '🔥', color: '#f472b6', showOnRadar: true },
  study_rhythm: { name: '学习节奏', icon: '⏱️', color: '#818cf8', showOnRadar: true },
  interest_preference: { name: '内容偏好', icon: '🎨', color: '#fb923c', showOnRadar: true },
  knowledge_mastery: { name: '知识掌握度', icon: '📚', color: '#6366f1', showOnRadar: true },
  exercise_completion: { name: '练习完成度', icon: '✅', color: '#22c55e', showOnRadar: true },
  // === 非雷达维度（仅存储在已采集维度中） ===
  major: { name: '专业方向', icon: '🎓', color: '#6366f1', showOnRadar: false },
  grade: { name: '年级水平', icon: '📊', color: '#a78bfa', showOnRadar: false },
  cognitive_style: { name: '认知风格', icon: '🧠', color: '#f472b6', showOnRadar: false },
}

/** 各维度枚举可选值列表 */
export const DIMENSION_ENUMS: Record<ProfileAllDimensionKey, string[]> = {
  // 雷达图维度
  base_level: ['入门', '基础', '中等', '进阶', '精通'],
  weak_points: [], // 动态生成，不固定枚举
  study_goal: ['考试通关', '竞赛提升', '项目实战', '全面掌握', '兴趣探索'],
  learning_engagement: [], // 动态计算，无固定枚举
  study_rhythm: ['碎片化', '适中节奏', '深度沉浸', '突击式'],
  interest_preference: ['视频教程', '文档阅读', '代码实操', '思维导图', '互动练习', '综合型'],
  knowledge_mastery: [], // 动态计算，无固定枚举
  exercise_completion: [], // 动态计算，无固定枚举
  // 非雷达维度
  major: ['计算机科学', '软件工程', '信息技术', '电子工程', '数学', '其他'],
  grade: ['大一', '大二', '大三', '大四', '研究生', '其他'],
  cognitive_style: ['视觉型', '听觉型', '实践型', '理论型', '混合型'],
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  isStreaming?: boolean
  source?: string
}

export type ResourceType = 'document' | 'mindmap' | 'quiz' | 'exercise' | 'code' | 'video' | 'extension' | 'knowledge-graph'

export interface ResourceItem {
  id: string
  title: string
  type: ResourceType
  module: string
  createdAt: string
  aiGenerated?: boolean
  content?: string
  url?: string
  /** 所属科目（如"数据结构"，多科目逗号分隔如"数据结构,算法"） */
  subject?: string
  /** 视频生成任务ID（ai_tutor异步生成视频） */
  video_task_id?: string
  /** 资源难度等级 */
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  /** 智能体随学随新自动生成的标记（不触发画像更新，防循环） */
  isAutoGenerated?: boolean
  /** 资源描述 */
  description?: string
  /** 标签 */
  tags?: string[]
  /** 完成状态 */
  status?: 'pending' | 'active' | 'completed'
  /** 视频生成状态（异步生成时使用） */
  videoStatus?: 'pending' | 'running' | 'done' | 'failed'
  /** @deprecated 使用 video_task_id 替代。保留用于兼容旧数据读取 */
  taskId?: string
  /** 完成时间 */
  completedAt?: string
  /** 是否为薄弱点资源（画像匹配用） */
  isWeakPoint?: boolean
  /** 画像匹配度分数（0-100） */
  match_score?: number
  /** 用户评分（1-5，0/未设置表示未评分） */
  rating?: number
  /** 是否收藏 */
  favorited?: boolean
  /** 是否已掌握 */
  mastered?: boolean
}

export type PathStageStatus = 'completed' | 'active' | 'pending'

export interface PathStage {
  id: string
  title: string
  status: PathStageStatus
  suggestedDays: number
  actualDays?: number
  progress: number
  resources: PathResource[]
  reason: string
  reasonType: 'weakness' | 'foundation' | 'advanced'
}

export interface PathResource {
  id: string
  type: ResourceType
  name: string
  status: 'completed' | 'active' | 'pending'
  /** 引用的 ResourceItem ID（显式关联，不再依赖 ID 替换） */
  resourceRef?: string | null
}

export type PathGenerationStatus = 'idle' | 'generating' | 'done' | 'error'

export interface PathDiff {
  addedStages: PathStage[]
  removedStages: PathStage[]
  modifiedStages: { old: PathStage; new: PathStage }[]
  addedResources: { stageId: string; resource: PathResource }[]
  removedResources: { stageId: string; resource: PathResource }[]
}

export interface PathStageExtended extends PathStage {
  learningTips?: string
}

export interface AssessReport {
  score: number
  studyHours: number
  accuracy: number
  completionRate: number
  streakDays: number
  modules: AssessModule[]
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
}

export interface AssessModule {
  name: string
  score: number
  color: string
}

export interface UserInfo {
  id: string
  username: string
  role: UserRole
  email?: string
  createdAt?: string
  status?: 'active' | 'disabled'
}

export interface LoginResponse {
  token: string
  user: UserInfo
}

/* ===== 测评相关类型 ===== */

export type QuestionType = 'choice' | 'fill'
export type QuestionDifficulty = 'beginner' | 'intermediate' | 'advanced'

export interface AssessQuestion {
  id: string
  type: QuestionType
  question: string
  options?: string[]       // 选择题必填
  answer: string           // 选择题: "A"/"B"/"C"/"D"，填空题: 标准答案
  explanation: string
  difficulty: QuestionDifficulty
  knowledgePoints: string[]
}

export type AssessMode = 'practice' | 'instant-feedback'

export interface AssessAnswer {
  questionId: string
  userAnswer: string       // 选择题: "A"/"B"/"C"/"D"，填空题: 用户输入
  isCorrect: boolean
  timeSpent: number        // 秒
}