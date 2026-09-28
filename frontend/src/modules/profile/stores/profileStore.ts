﻿﻿import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type {
  ChatMessage, ProfileData, ProfileAllDimensionKey,
  ProfileBaseLevel, ProfileStudyGoal, ProfileDimension,
  ProfileUpdateLog, LearningEvent,
  RadarSnapshot, RadarInitialSnapshot,
} from '../../../shared/types'
import { ENUM_SCORE_MAP, DIMENSION_META } from '../../../shared/types'
import { chatGLM } from '../../../shared/api/glmApi'
import { buildInitialMessages, buildSupplementMessages } from '../prompts/profilePrompts'
import { useAuthStore } from '../../auth/stores/authStore'
import { useQaStore } from '../../qa/stores/qaStore'
import { usePathStore } from '../../path/stores/pathStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { syncToServer, loadFromServer } from '../../../shared/utils/backendSync'
import {
  saveProfileHistory,
  getProfileHistoryList,
  activateProfileHistory,
  deleteProfileHistory,
  getFullProfile,
  type ProfileHistoryItem,
} from '../api/profileApi'
import {
  filterRelevantWeakPoints,
} from '../../../shared/utils/subjectFilter'
import {
  cleanContaminatedData,
  migrateDimensions,
  createEmptyProfile,
  inferSubjectForMigration,
} from '../services/profileMigration'
import {
  DIALOGUE_ROUNDS,
  extractDimension,
  extractWeakPoints,
} from '../services/dialogueExtractor'
import {
  parseProfileUpdate,
  parseProfileSummary,
} from '../services/profileParsing'

// re-export 保持现有消费者不破坏（reviewerPrompts / agentPrompts / pathStore 从此导入）
export { filterRelevantWeakPoints }

/* ===== 画像持久化 Key ===== */
const PROFILE_STORAGE_KEY = 'ai_learning_profile'
const PROFILE_DATA_VERSION = 2 // 递增此版本号可强制清除旧格式数据

/* ===== 画像变化信息类型（供 agentStore 导入使用） ===== */
export interface ProfileChangeInfo {
  event: LearningEvent
  changedDims: string[]
  changeType: 'upgrade' | 'downgrade' | 'neutral'
}

export const useProfileStore = defineStore('profile', () => {
  /* ===== 从 localStorage 加载画像 ===== */
  function loadProfile(): ProfileData {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      const storageKey = `${PROFILE_STORAGE_KEY}_${userId}`

      // 检查数据版本，旧版本直接清除
      const versionKey = `${storageKey}_version`
      const savedVersion = localStorage.getItem(versionKey)
      if (savedVersion && Number(savedVersion) < PROFILE_DATA_VERSION) {
        localStorage.removeItem(storageKey)
        localStorage.removeItem(versionKey)
      }

      const stored = localStorage.getItem(storageKey)
      if (stored) {
        const parsed = JSON.parse(stored) as ProfileData
        // 兼容旧数据：确保所有字段存在
        if (!parsed.dimensions || !Array.isArray(parsed.dimensions)) {
          return createEmptyProfile()
        }
        if (!parsed.updateLogs) parsed.updateLogs = []
        if (!parsed.learningEvents) parsed.learningEvents = []
        if (!parsed.masteredPoints) parsed.masteredPoints = []
        if (parsed.totalStudyMinutes === undefined || parsed.totalStudyMinutes === null) parsed.totalStudyMinutes = 0
        if (parsed.streakDays === undefined || parsed.streakDays === null) parsed.streakDays = 0
        if (parsed.completedResourceCount === undefined || parsed.completedResourceCount === null) parsed.completedResourceCount = 0
        if (parsed.completedStageCount === undefined || parsed.completedStageCount === null) parsed.completedStageCount = 0
        if (parsed.completedAssessCount === undefined || parsed.completedAssessCount === null) parsed.completedAssessCount = 0
        if (!parsed.lastUpdatedAt) parsed.lastUpdatedAt = new Date().toISOString()
        if (!parsed.weak_points) parsed.weak_points = []
        // 兼容旧数据：添加新维度字段
        if (parsed.exercise_completion === undefined || parsed.exercise_completion === null) parsed.exercise_completion = 0
        if (parsed.learning_engagement === undefined || parsed.learning_engagement === null) parsed.learning_engagement = 0
        // 兼容旧维度结构
        migrateDimensions(parsed)
        // 多科目迁移：旧数据推断科目并创建第一个覆盖层
        if (!parsed.subjectOverlays || parsed.subjectOverlays.length === 0) {
          const subject = inferSubjectForMigration(parsed)
          if (subject) {
            parsed.currentSubject = subject
            parsed.subjectOverlays = [{
              subject,
              base_level: parsed.base_level || '',
              weak_points: [...(parsed.weak_points || [])],
              study_goal: parsed.study_goal || '',
              knowledge_mastery: parsed.knowledge_mastery || 0,
              exercise_completion: parsed.exercise_completion || 0,
              completedResourceCount: parsed.completedResourceCount || 0,
              completedStageCount: parsed.completedStageCount || 0,
              completedAssessCount: parsed.completedAssessCount || 0,
              masteredPoints: [...(parsed.masteredPoints || [])],
              lastUpdatedAt: parsed.lastUpdatedAt || new Date().toISOString(),
            }]
          }
        }
        // 保存版本号
        localStorage.setItem(versionKey, String(PROFILE_DATA_VERSION))
        return parsed
      }
    } catch (e) {
      console.warn('[Profile] 加载画像失败，使用空画像', e)
    }
    return createEmptyProfile()
  }

  const chatMessages = ref<ChatMessage[]>([])
  // 初始为空画像，由 reloadProfileForUser() 在 watch 中异步从后端加载正确数据
  // 避免 store 初始化时从 localStorage 加载到错误用户的旧数据
  const profileData = ref<ProfileData>(createEmptyProfile())
  const streamingContent = ref('')
  const isStreaming = ref(false)

  // 标记画像是否正在从后端加载，防止 initDialogue 在加载完成前误触发
  const isLoadingProfile = ref(true)

  // 画像历史列表
  const profileHistories = ref<ProfileHistoryItem[]>([])
  const isLoadingHistories = ref(false)
  const showHistorySelector = ref(false)

  // 追踪 simulateStreaming 的 interval，避免内存泄漏
  let streamingTimer: ReturnType<typeof setInterval> | null = null
  // 追踪 chatGLM 的 AbortController，允许取消进行中的请求
  let chatAbortController: AbortController | null = null

  /* ===== 画像历史相关方法 ===== */

  /** 加载画像历史列表 */
  async function loadProfileHistories() {
    isLoadingHistories.value = true
    try {
      const res = await getProfileHistoryList()
      if (res.success) {
        profileHistories.value = res.histories
      }
    } catch (e) {
      console.warn('[Profile] 加载画像历史失败', e)
    }
    isLoadingHistories.value = false
  }

  /** 切换到某个历史画像（保留学习进度，清空答疑历史） */
  async function switchToHistory(historyId: string) {
    try {
      const res = await activateProfileHistory(historyId)
      if (res.success) {
        // 清空答疑历史和当前对话
        const qaStore = useQaStore()
        qaStore.clearAll()
        
        // 保存当前的学习进度数据（不随画像切换而丢失）
        const currentProgress = {
          completedResourceCount: profileData.value.completedResourceCount || 0,
          completedStageCount: profileData.value.completedStageCount || 0,
          completedAssessCount: profileData.value.completedAssessCount || 0,
          masteredPoints: profileData.value.masteredPoints || [],
          totalStudyMinutes: profileData.value.totalStudyMinutes || 0,
          streakDays: profileData.value.streakDays || 0,
          learningEvents: profileData.value.learningEvents || [],
          updateLogs: profileData.value.updateLogs || [],
        }
        
        // 直接从后端获取完整的画像数据（确保数据是最新的）
        const fullProfileRes = await getFullProfile() as any
        const profileDataRaw = fullProfileRes.data
        if (profileDataRaw && typeof profileDataRaw === 'object') {
          const newProfileData = profileDataRaw as ProfileData
          // 兼容性填充
          if (!newProfileData.updateLogs) newProfileData.updateLogs = []
          if (!newProfileData.learningEvents) newProfileData.learningEvents = []
          if (!newProfileData.masteredPoints) newProfileData.masteredPoints = []
          if (!newProfileData.weak_points || !Array.isArray(newProfileData.weak_points)) newProfileData.weak_points = []
          if (!newProfileData.totalStudyMinutes) newProfileData.totalStudyMinutes = 0
          if (!newProfileData.streakDays) newProfileData.streakDays = 0
          if (!newProfileData.completedResourceCount) newProfileData.completedResourceCount = 0
          if (!newProfileData.completedStageCount) newProfileData.completedStageCount = 0
          if (!newProfileData.completedAssessCount) newProfileData.completedAssessCount = 0
          if (!newProfileData.subjectOverlays || !Array.isArray(newProfileData.subjectOverlays)) newProfileData.subjectOverlays = []
          if (!newProfileData.snapshots || !Array.isArray(newProfileData.snapshots)) newProfileData.snapshots = []
          if (newProfileData.exercise_completion === undefined) newProfileData.exercise_completion = 0
          if (newProfileData.learning_engagement === undefined) newProfileData.learning_engagement = 0
          if (newProfileData.knowledge_mastery === undefined) newProfileData.knowledge_mastery = 0
          // 兼容旧维度结构
          migrateDimensions(newProfileData)
          // 清理跨科目污染数据
          cleanContaminatedData(newProfileData)
          profileData.value = newProfileData
          // 加载当前科目的 overlay 维度
          const hSubject = newProfileData.currentSubject || ''
          if (hSubject) loadOverlay(hSubject)
        } else {
          // 如果获取失败，使用 reloadProfileForUser
          await reloadProfileForUser()
        }
        
        // 恢复学习进度数据（取历史数据和当前数据的最大值，确保进度不丢失）
        profileData.value.completedResourceCount = Math.max(
          profileData.value.completedResourceCount || 0,
          currentProgress.completedResourceCount
        )
        profileData.value.completedStageCount = Math.max(
          profileData.value.completedStageCount || 0,
          currentProgress.completedStageCount
        )
        profileData.value.completedAssessCount = Math.max(
          profileData.value.completedAssessCount || 0,
          currentProgress.completedAssessCount
        )
        // masteredPoints 合并去重
        const mergedMastered = new Set([
          ...profileData.value.masteredPoints || [],
          ...currentProgress.masteredPoints
        ])
        profileData.value.masteredPoints = Array.from(mergedMastered)
        profileData.value.totalStudyMinutes = Math.max(
          profileData.value.totalStudyMinutes || 0,
          currentProgress.totalStudyMinutes
        )
        profileData.value.streakDays = Math.max(
          profileData.value.streakDays || 0,
          currentProgress.streakDays
        )
        // 合并学习事件（保留最近的）
        const mergedEvents = [...currentProgress.learningEvents, ...profileData.value.learningEvents || []]
        // 按时间戳去重（保留最新的）
        const uniqueEvents = mergedEvents.filter((e, i, arr) => 
          arr.findIndex(x => x.timestamp === e.timestamp && x.type === e.type) === i
        )
        profileData.value.learningEvents = uniqueEvents.slice(-100)
        
        showHistorySelector.value = false
        // 刷新历史列表
        await loadProfileHistories()
        
        // 保存更新后的画像（确保学习进度被持久化）
        saveProfile()
        
        console.log('[Profile] 画像切换成功，专业:', profileData.value.major)
      }
    } catch (e) {
      console.warn('[Profile] 切换画像失败', e)
    }
  }

  /** 删除某个历史画像 */
  async function deleteHistory(historyId: string) {
    try {
      const res = await deleteProfileHistory(historyId)
      if (res.success) {
        await loadProfileHistories()
      }
    } catch (e) {
      console.warn('[Profile] 删除画像失败', e)
    }
  }

  /** 保存当前画像到历史记录 */
  async function saveCurrentToHistory(name?: string) {
    try {
      const res = await saveProfileHistory({
        name,
        profile_data: profileData.value,
      })
      if (res.success) {
        await loadProfileHistories()
      }
    } catch (e) {
      console.warn('[Profile] 保存画像历史失败', e)
    }
  }

  /* ===== 画像更新信号：学习事件触发画像变化时置 true，3秒后自动复位 ===== */
  const profileJustUpdated = ref(false)
  let updateSignalTimer: ReturnType<typeof setTimeout> | null = null
  function signalProfileUpdate() {
    profileJustUpdated.value = true
    if (updateSignalTimer) clearTimeout(updateSignalTimer)
    updateSignalTimer = setTimeout(() => { profileJustUpdated.value = false }, 3000)
  }

  /* ===== 画像变化信息：用于通知智能体等 store 做联动 ===== */
  const profileChangeInfo = ref<ProfileChangeInfo | null>(null)

  function determineChangeType(changes: Record<string, any>): 'upgrade' | 'downgrade' | 'neutral' {
    // 如果薄弱点增加 → downgrade
    if (changes['weak_points']) {
      const weakChange = changes['weak_points']
      if (weakChange.after < weakChange.before) return 'downgrade'
      if (weakChange.after > weakChange.before) return 'upgrade'
    }
    // 如果基础水平降低 → downgrade
    if (changes['base_level'] && changes['base_level'].after < changes['base_level'].before) return 'downgrade'
    // 其他变化视为 upgrade（分数提升）
    if (Object.keys(changes).length > 0) return 'upgrade'
    return 'neutral'
  }

  /* ===== 持久化：自动保存画像到 localStorage + 后端 ===== */
  function saveProfile() {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      const storageKey = `${PROFILE_STORAGE_KEY}_${userId}`
      profileData.value.lastUpdatedAt = new Date().toISOString()
      localStorage.setItem(storageKey, JSON.stringify(profileData.value))
      localStorage.setItem(`${storageKey}_version`, String(PROFILE_DATA_VERSION))
      // 同步到后端（防抖 1s）
      syncToServer('profile', profileData.value)
    } catch (e) {
      console.warn('[Profile] 保存画像失败', e)
    }
  }

  // 监听画像变化自动持久化（防抖 500ms）
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    () => profileData.value,
    () => {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => saveProfile(), 500)
    },
    { deep: true },
  )

  /* ===== 登录状态变更时自动加载对应用户的画像 ===== */
  async function reloadProfileForUser() {
    const authStore = useAuthStore()
    const userId = authStore.user?.id || 'guest'
    const storageKey = `${PROFILE_STORAGE_KEY}_${userId}`

    isLoadingProfile.value = true

    // 优先从后端加载
    const serverData = await loadFromServer('profile')
    if (serverData && typeof serverData === 'object') {
      const parsed = serverData as ProfileData
      // 兼容性填充
      if (!parsed.updateLogs) parsed.updateLogs = []
      if (!parsed.learningEvents) parsed.learningEvents = []
      if (!parsed.masteredPoints) parsed.masteredPoints = []
      if (!parsed.weak_points || !Array.isArray(parsed.weak_points)) parsed.weak_points = []
      if (!parsed.totalStudyMinutes) parsed.totalStudyMinutes = 0
      if (!parsed.streakDays) parsed.streakDays = 0
      if (!parsed.completedResourceCount) parsed.completedResourceCount = 0
      if (!parsed.completedStageCount) parsed.completedStageCount = 0
      if (!parsed.completedAssessCount) parsed.completedAssessCount = 0
      if (!parsed.subjectOverlays || !Array.isArray(parsed.subjectOverlays)) parsed.subjectOverlays = []
      if (!parsed.snapshots || !Array.isArray(parsed.snapshots)) parsed.snapshots = []
      if (parsed.exercise_completion === undefined) parsed.exercise_completion = 0
      if (parsed.learning_engagement === undefined) parsed.learning_engagement = 0
      if (parsed.knowledge_mastery === undefined) parsed.knowledge_mastery = 0
      // 兼容旧维度结构
      migrateDimensions(parsed)
      // 清理跨科目污染数据（如英语overlay中的"递归"等CS内容）
      cleanContaminatedData(parsed)
      profileData.value = parsed
      // 加载当前科目的 overlay 维度（base_level, study_goal 等）
      const cs = parsed.currentSubject || ''
      if (cs) loadOverlay(cs)
    } else {
      // 检查 localStorage 中是否有当前用户的数据
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as ProfileData
          if (parsed.dimensions && Array.isArray(parsed.dimensions)) {
            // 兼容性填充
            if (!parsed.updateLogs) parsed.updateLogs = []
            if (!parsed.learningEvents) parsed.learningEvents = []
            if (!parsed.masteredPoints) parsed.masteredPoints = []
            if (!parsed.weak_points || !Array.isArray(parsed.weak_points)) parsed.weak_points = []
            if (!parsed.totalStudyMinutes) parsed.totalStudyMinutes = 0
            if (!parsed.streakDays) parsed.streakDays = 0
            if (!parsed.completedResourceCount) parsed.completedResourceCount = 0
            if (!parsed.completedStageCount) parsed.completedStageCount = 0
            if (!parsed.completedAssessCount) parsed.completedAssessCount = 0
            if (!parsed.subjectOverlays || !Array.isArray(parsed.subjectOverlays)) parsed.subjectOverlays = []
            if (!parsed.snapshots || !Array.isArray(parsed.snapshots)) parsed.snapshots = []
            if (parsed.exercise_completion === undefined) parsed.exercise_completion = 0
            if (parsed.learning_engagement === undefined) parsed.learning_engagement = 0
            if (parsed.knowledge_mastery === undefined) parsed.knowledge_mastery = 0
            // 兼容旧维度结构
            migrateDimensions(parsed)
            // 清理跨科目污染数据
            cleanContaminatedData(parsed)
            profileData.value = parsed
            const cs2 = parsed.currentSubject || ''
            if (cs2) loadOverlay(cs2)
          } else {
            // 数据格式错误，创建空画像
            profileData.value = createEmptyProfile()
          }
        } catch {
          // 解析失败，创建空画像
          profileData.value = createEmptyProfile()
        }
      } else {
        // localStorage 中没有当前用户的数据，创建空画像
        profileData.value = createEmptyProfile()
      }
    }
    chatMessages.value = []
    streamingContent.value = ''
    isStreaming.value = false
    isLoadingProfile.value = false
  }

  // 监听 authStore 的用户变化，自动切换画像
  let lastUserId: string | null = null
  watch(
    () => {
      try {
        const authStore = useAuthStore()
        return authStore.user?.id || 'guest'
      } catch {
        return 'guest'
      }
    },
    (newUserId) => {
      if (newUserId !== lastUserId) {
        lastUserId = newUserId
        reloadProfileForUser()
      }
    },
    { immediate: true },
  )

  /* ===== 计算属性 ===== */

  /** 可通过对话采集的维度（排除自动计算的动态维度） */
  const collectibleDimensions = computed(() =>
    (profileData.value.dimensions || []).filter(d =>
      d.key !== 'knowledge_mastery' && d.key !== 'exercise_completion' && d.key !== 'learning_engagement'
    )
  )

  const currentOverlay = computed(() => {
    const subject = profileData.value.currentSubject
    if (!subject || !profileData.value.subjectOverlays?.length) return null
    return profileData.value.subjectOverlays.find(o => o.subject === subject) || null
  })

  const effectiveProfile = computed(() => {
    const base = profileData.value
    const overlay = currentOverlay.value
    if (!overlay) return base

    // 创建合并后的 dimensions 数组
    const mergedDimensions = (base.dimensions || []).map(dim => {
      const key = dim.key
      let newValue = dim.value
      let newLabel = dim.label

      // 根据覆盖层字段更新对应维度
      if (key === 'base_level' && overlay.base_level) {
        const score = computeScore('base_level', overlay.base_level)
        newValue = score
        newLabel = overlay.base_level
      } else if (key === 'weak_points' && overlay.weak_points?.length > 0) {
        const score = computeScore('weak_points', '', overlay.weak_points.length)
        newValue = score
        newLabel = `${overlay.weak_points.length}项薄弱`
      } else if (key === 'study_goal' && overlay.study_goal) {
        const score = computeScore('study_goal', overlay.study_goal)
        newValue = score
        newLabel = overlay.study_goal
      } else if (key === 'knowledge_mastery' && overlay.knowledge_mastery > 0) {
        newValue = overlay.knowledge_mastery
        newLabel = overlay.knowledge_mastery >= 80 ? '良好' : overlay.knowledge_mastery >= 60 ? '一般' : '待提升'
      } else if (key === 'exercise_completion' && overlay.exercise_completion > 0) {
        newValue = overlay.exercise_completion
        newLabel = overlay.exercise_completion >= 80 ? '良好' : overlay.exercise_completion >= 60 ? '一般' : '待练习'
      }

      return { ...dim, value: newValue, label: newLabel }
    })

    // 返回合并后的画像对象
    return {
      ...base,
      dimensions: mergedDimensions,
      base_level: overlay.base_level || base.base_level,
      weak_points: overlay.weak_points?.length > 0 ? overlay.weak_points : base.weak_points,
      study_goal: overlay.study_goal || base.study_goal,
      knowledge_mastery: overlay.knowledge_mastery ?? base.knowledge_mastery,
      exercise_completion: overlay.exercise_completion ?? base.exercise_completion,
      completedResourceCount: overlay.completedResourceCount ?? base.completedResourceCount,
      completedStageCount: overlay.completedStageCount ?? base.completedStageCount,
      completedAssessCount: overlay.completedAssessCount ?? base.completedAssessCount,
      masteredPoints: overlay.masteredPoints?.length > 0 ? overlay.masteredPoints : base.masteredPoints,
    } as ProfileData
  })

  /** 画像完成度：只看可对话采集的维度 */
  const completionRate = computed(() => {
    const dims = collectibleDimensions.value
    if (!dims.length) return 0
    const filled = dims.filter(d => d.value > 0)
    return Math.round((filled.length / dims.length) * 100)
  })

  const completedDims = computed(() =>
    collectibleDimensions.value.filter(d => d.value > 0).length
  )

  const totalDims = computed(() => collectibleDimensions.value.length)

  /** 知识掌握度计算：放宽系数 + 里程碑加分 */
  const knowledgeMastery = computed(() => {
    const data = profileData.value
    const resourceScore = Math.min((data.completedResourceCount || 0) * 8, 40)
    const stageScore = Math.min((data.completedStageCount || 0) * 12, 45)
    const assessScore = Math.min((data.completedAssessCount || 0) * 10, 25)
    const masteredScore = Math.min((data.masteredPoints || []).length * 6, 15)
    // 阶段里程碑加分：每完成3个阶段+15
    const milestoneBonus = Math.floor((data.completedStageCount || 0) / 3) * 15

    return Math.min(resourceScore + stageScore + assessScore + masteredScore + milestoneBonus, 100)
  })

  /** 练习完成度计算：放宽系数 + 测评满分加分 */
  const exerciseCompletion = computed(() => {
    const data = profileData.value
    const assessCount = data.completedAssessCount || 0
    const assessScore = Math.min(assessCount * 10, 50)
    const masteredScore = Math.min((data.masteredPoints || []).length * 6, 30)
    const practiceEvents = (data.learningEvents || []).filter(e =>
      e.type === 'resource_complete' && (e.resourceType === 'exercise' || e.resourceType === 'quiz')
    ).length
    const practiceScore = Math.min(practiceEvents * 5, 20)
    // 测评满分加分：从学习事件中统计满分测评
    const perfectAssess = (data.learningEvents || []).filter(e =>
      e.type === 'assess_complete' && e.score === 100
    ).length
    const perfectBonus = Math.min(perfectAssess * 10, 20)

    return Math.min(assessScore + masteredScore + practiceScore + perfectBonus, 100)
  })

  /** 学习投入度计算：放宽系数 + 连续学习加分 */
  const learningEngagement = computed(() => {
    const data = profileData.value
    // 学习时长：每20分钟贡献2分，上限40（原30分钟）
    const timeScore = Math.min(Math.floor((data.totalStudyMinutes || 0) / 20) * 2, 40)
    // 连续天数：每天贡献6分，上限30（原×5/25）
    const streakScore = Math.min((data.streakDays || 0) * 6, 30)
    // 学习事件：每个贡献1.5分，上限25（原×1/20）
    const eventScore = Math.min(Math.floor((data.learningEvents || []).length * 1.5), 25)
    // 认知风格加分
    const styleBonus = data.cognitive_style === '实践型' ? 10
      : data.cognitive_style === '混合型' ? 8
      : data.cognitive_style === '理论型' ? 5
      : data.cognitive_style === '视觉型' ? 4
      : data.cognitive_style === '听觉型' ? 3
      : 0
    // 连续学习加分
    const streakBonus = (data.streakDays || 0) >= 30 ? 20
      : (data.streakDays || 0) >= 7 ? 10
      : 0

    return Math.min(timeScore + streakScore + eventScore + styleBonus + streakBonus, 100)
  })

  const weakDimensions = computed(() =>
    profileData.value.dimensions.filter(d =>
      d.key === 'weak_points' && d.value >= 60
    )
  )

  /** 同步动态维度分数到 dimensions 数组（知识掌握度、练习完成度、学习投入度） */
  function syncDynamicDimensions() {
    const data = profileData.value
    if (!data.dimensions) return

    // 知识掌握度
    const kmValue = knowledgeMastery.value
    data.knowledge_mastery = kmValue
    const kmDim = data.dimensions.find(d => d.key === 'knowledge_mastery')
    if (kmDim) {
      kmDim.value = kmValue
      kmDim.label = kmValue >= 80 ? '掌握良好' : kmValue >= 50 ? '逐步掌握' : kmValue > 0 ? '初步掌握' : '待学习'
    }

    // 练习完成度
    const ecValue = exerciseCompletion.value
    data.exercise_completion = ecValue
    const ecDim = data.dimensions.find(d => d.key === 'exercise_completion')
    if (ecDim) {
      ecDim.value = ecValue
      ecDim.label = ecValue >= 80 ? '完成度高' : ecValue >= 50 ? '稳步推进' : ecValue > 0 ? '初步练习' : '待练习'
    }

    // 学习投入度
    const leValue = learningEngagement.value
    data.learning_engagement = leValue
    const leDim = data.dimensions.find(d => d.key === 'learning_engagement')
    if (leDim) {
      leDim.value = leValue
      leDim.label = leValue >= 80 ? '高度投入' : leValue >= 50 ? '积极学习' : leValue > 0 ? '初步投入' : '待评估'
    }
  }

  /** 当前引导轮次的配置 */
  const currentRoundConfig = computed(() => {
    if (profileData.value.phase !== 'initial') return null
    const round = profileData.value.dialogueRound
    if (round < 1 || round > 4) return null
    return DIALOGUE_ROUNDS[round - 1]
  })

  /** 当前阶段的快捷回复 */
  const quickReplies = computed(() => {
    if (profileData.value.phase === 'initial') {
      const config = currentRoundConfig.value
      return config ? config.quickReplies : []
    }
    // supplement 阶段
    return ['修改学习目标', '补充薄弱知识点', '调整认知风格', '确认无误']
  })

  /** 画像是否需要确认（第4轮完成后） */
  const needsConfirmation = computed(() =>
    profileData.value.dialogueRound >= 4 && profileData.value.phase === 'initial'
  )

  /* ===== 维度分数计算 ===== */

  function computeScore(key: ProfileAllDimensionKey, enumValue: string, weakPointsCount?: number): number {
    if (key === 'weak_points') {
      // 薄弱点越少分数越高：0个=95, 1个=80, 2个=65, 3个=50, 4个=35, 5+个=20
      const count = weakPointsCount ?? profileData.value.weak_points.length
      const scores = [95, 80, 65, 50, 35, 20]
      return scores[Math.min(count, scores.length - 1)]
    }
    const map = ENUM_SCORE_MAP[key]
    const val = map?.[enumValue]
    // 跳过非数字值（如 _countRule）
    return typeof val === 'number' ? val : 40
  }

  /** 枚举值自动升级：当 baseScore + bonus 超过下一级枚举的基础分时，升级枚举值并重置 bonus */
  function tryUpgradeEnum(dim: ProfileDimension): void {
    // 动态维度和薄弱点不适用枚举升级
    if (dim.key === 'weak_points' || dim.key === 'knowledge_mastery' ||
        dim.key === 'exercise_completion' || dim.key === 'learning_engagement') return

    const map = ENUM_SCORE_MAP[dim.key]
    if (!map) return

    const totalScore = dim.baseScore + dim.bonus
    // 找到比当前 baseScore 更高且 totalScore 已达到的最近枚举值
    let bestEnum = dim.enumValue || ''
    let bestBase = dim.baseScore
    for (const [enumVal, score] of Object.entries(map)) {
      if (typeof score !== 'number') continue
      if (score > dim.baseScore && totalScore >= score && score > bestBase) {
        bestEnum = enumVal
        bestBase = score
      }
    }
    if (bestBase > dim.baseScore) {
      dim.enumValue = bestEnum
      dim.baseScore = bestBase
      dim.bonus = 0
      dim.value = bestBase
      dim.label = bestEnum
      // 同步 flat field
      const data = profileData.value as any
      data[dim.key] = bestEnum
    }
  }

  /** 给枚举维度增加行为增量 */
  function addBonus(dimKey: ProfileAllDimensionKey, increment: number): void {
    const dim = profileData.value.dimensions.find(d => d.key === dimKey)
    if (!dim) return
    // 动态维度不用 bonus 机制
    if (dimKey === 'knowledge_mastery' || dimKey === 'exercise_completion' || dimKey === 'learning_engagement') return

    const maxBonus = Math.floor(dim.baseScore * 0.3) || 15 // 至少允许15分增量
    dim.bonus = Math.min(dim.bonus + increment, maxBonus)
    // 低分不减少到基础分以下
    if (dim.bonus < 0) dim.bonus = 0
    dim.value = dim.baseScore + dim.bonus
    // 尝试枚举自动升级
    tryUpgradeEnum(dim)
  }

  /* ===== 更新画像维度 ===== */

  function updateDimension(key: ProfileAllDimensionKey, enumValue: string, weakPoints?: string[]) {
    const dim = profileData.value.dimensions.find(d => d.key === key)
    if (!dim) return

    if (key === 'weak_points' && weakPoints) {
      profileData.value.weak_points = weakPoints
      const score = computeScore(key, '', weakPoints.length)
      dim.value = score
      dim.baseScore = score
      dim.bonus = 0
      dim.label = weakPoints.length > 0 ? `${weakPoints.length}项薄弱` : '无明显薄弱'
      dim.enumValue = dim.label
    } else {
      const score = computeScore(key, enumValue)
      dim.value = score
      dim.baseScore = score
      dim.bonus = 0
      dim.label = enumValue
      dim.enumValue = enumValue

      // 同步更新 flat field
      const data = profileData.value as any
      data[key] = enumValue
    }
  }

  /** 从解析结果更新画像 */
  function applyParsedUpdate(parsed: Record<string, string>) {
    for (const [key, val] of Object.entries(parsed)) {
      if (key === 'weak_points') {
        const points = val.split(',').map(p => p.trim()).filter(Boolean)
        updateDimension('weak_points', '', points)
      } else if (key === 'currentSubject') {
        const newSubject = val.trim()
        if (newSubject && newSubject !== profileData.value.currentSubject) {
          switchSubject(newSubject)
        }
      } else if (key in DIMENSION_META) {
        updateDimension(key as ProfileAllDimensionKey, val)
      }
    }
    // 同步动态维度
    syncDynamicDimensions()
    // 同步科目独立维度到覆盖层
    if (profileData.value.currentSubject) {
      saveCurrentOverlay()
    }
  }

  /* ===== 多科目：覆盖层管理 ===== */

  function ensureOverlay(subject: string) {
    if (!profileData.value.subjectOverlays) {
      profileData.value.subjectOverlays = []
    }
    const existing = profileData.value.subjectOverlays.find(o => o.subject === subject)
    if (!existing) {
      profileData.value.subjectOverlays.push({
        subject,
        base_level: '',
        weak_points: [],
        study_goal: '',
        knowledge_mastery: 0,
        exercise_completion: 0,
        completedResourceCount: 0,
        completedStageCount: 0,
        completedAssessCount: 0,
        masteredPoints: [],
        lastUpdatedAt: new Date().toISOString(),
      })
    }
  }

  function saveCurrentOverlay() {
    const subject = profileData.value.currentSubject
    if (!subject) return

    ensureOverlay(subject)
    const overlay = profileData.value.subjectOverlays!.find(o => o.subject === subject)
    if (!overlay) return

    overlay.base_level = profileData.value.base_level
    // ★ 保存前过滤跨科目污染的薄弱点，防止CS内容混入非CS科目
    overlay.weak_points = filterRelevantWeakPoints([...profileData.value.weak_points], subject)
    overlay.study_goal = profileData.value.study_goal
    overlay.knowledge_mastery = profileData.value.knowledge_mastery
    overlay.exercise_completion = profileData.value.exercise_completion
    overlay.completedResourceCount = profileData.value.completedResourceCount
    overlay.completedStageCount = profileData.value.completedStageCount
    overlay.completedAssessCount = profileData.value.completedAssessCount
    overlay.masteredPoints = [...profileData.value.masteredPoints]
    overlay.lastUpdatedAt = new Date().toISOString()
  }

  function loadOverlay(subject: string) {
    const overlay = profileData.value.subjectOverlays?.find(o => o.subject === subject)
    if (!overlay) return

    // 判断是否为新科目的空 overlay（没有科目相关数据）
    const isNewOverlay = !overlay.base_level &&
      (!overlay.weak_points || overlay.weak_points.length === 0) &&
      !overlay.study_goal

    if (isNewOverlay) {
      // 新科目：重置科目相关维度为默认值，让雷达图显示空白状态
      profileData.value.base_level = '' as ProfileBaseLevel
      profileData.value.weak_points = []
      profileData.value.study_goal = '' as ProfileStudyGoal
      profileData.value.knowledge_mastery = 0
      profileData.value.exercise_completion = 0
      profileData.value.completedResourceCount = 0
      profileData.value.completedStageCount = 0
      profileData.value.completedAssessCount = 0
      profileData.value.masteredPoints = []

      // 重置 dimensions 数组中科目相关维度的分数
      const subjectDims = ['base_level', 'weak_points', 'study_goal', 'knowledge_mastery', 'exercise_completion']
      for (const key of subjectDims) {
        const dim = profileData.value.dimensions.find(d => d.key === key)
        if (dim) {
          dim.value = 0
          dim.baseScore = 0
          dim.bonus = 0
          dim.label = key === 'knowledge_mastery' ? '待学习'
            : key === 'exercise_completion' ? '待练习'
            : key === 'weak_points' ? '待收集'
            : '待确定'
          dim.enumValue = ''
        }
      }
      // learning_engagement 是跨科目维度，保持不变
      syncDynamicDimensions()
      return
    }

    // 已有 overlay：加载科目数据
    if (overlay.base_level) profileData.value.base_level = overlay.base_level as ProfileBaseLevel
    else profileData.value.base_level = '' as ProfileBaseLevel
    // ★ 过滤跨科目污染的薄弱点（如英语科目中残留的"递归"等CS内容）
    const filteredWeakPoints = filterRelevantWeakPoints(overlay.weak_points || [], subject)
    if (filteredWeakPoints.length > 0) {
      profileData.value.weak_points = filteredWeakPoints
      // 同步清理 overlay 中的脏数据
      if (overlay.weak_points && overlay.weak_points.length !== filteredWeakPoints.length) {
        overlay.weak_points = filteredWeakPoints
      }
    } else {
      profileData.value.weak_points = []
      overlay.weak_points = []
    }
    if (overlay.study_goal) profileData.value.study_goal = overlay.study_goal as ProfileStudyGoal
    else profileData.value.study_goal = '' as ProfileStudyGoal
    profileData.value.knowledge_mastery = overlay.knowledge_mastery || 0
    profileData.value.exercise_completion = overlay.exercise_completion || 0
    profileData.value.completedResourceCount = overlay.completedResourceCount || 0
    profileData.value.completedStageCount = overlay.completedStageCount || 0
    profileData.value.completedAssessCount = overlay.completedAssessCount || 0
    if (overlay.masteredPoints && overlay.masteredPoints.length > 0) profileData.value.masteredPoints = [...overlay.masteredPoints]
    else profileData.value.masteredPoints = []

    syncDynamicDimensions()

    // 同步 dimensions 数组中的分数
    const baseDim = profileData.value.dimensions.find(d => d.key === 'base_level')
    if (baseDim) {
      if (overlay.base_level) {
        const score = computeScore('base_level', overlay.base_level)
        baseDim.value = score
        baseDim.baseScore = score
        baseDim.label = overlay.base_level
        baseDim.enumValue = overlay.base_level
      } else {
        baseDim.value = 0
        baseDim.baseScore = 0
        baseDim.bonus = 0
        baseDim.label = '待确定'
        baseDim.enumValue = ''
      }
    }

    const weakDim = profileData.value.dimensions.find(d => d.key === 'weak_points')
    if (weakDim) {
      // 使用过滤后的薄弱点（已清理跨科目污染）
      const currentWp = profileData.value.weak_points
      if (currentWp && currentWp.length > 0) {
        const score = computeScore('weak_points', '', currentWp.length)
        weakDim.value = score
        weakDim.baseScore = score
        weakDim.label = `${currentWp.length}项薄弱`
        weakDim.enumValue = weakDim.label
      } else {
        weakDim.value = 0
        weakDim.baseScore = 0
        weakDim.bonus = 0
        weakDim.label = '待收集'
        weakDim.enumValue = ''
      }
    }

    const goalDim = profileData.value.dimensions.find(d => d.key === 'study_goal')
    if (goalDim) {
      if (overlay.study_goal) {
        const score = computeScore('study_goal', overlay.study_goal)
        goalDim.value = score
        goalDim.baseScore = score
        goalDim.label = overlay.study_goal
        goalDim.enumValue = overlay.study_goal
      } else {
        goalDim.value = 0
        goalDim.baseScore = 0
        goalDim.bonus = 0
        goalDim.label = '待确定'
        goalDim.enumValue = ''
      }
    }
  }

  function switchSubject(subject: string) {
    if (!subject) return
    if (profileData.value.currentSubject === subject) return

    saveCurrentOverlay()

    profileData.value.currentSubject = subject

    ensureOverlay(subject)
    loadOverlay(subject)

    saveProfile()

    // 切换科目时按 subject 重新加载 path 和 resources
    // 修复跨科目污染：不清空会导致英语会话显示数据结构路径/视频
    try {
      const pathStore = usePathStore()
      const resourceStore = useResourceStore()
      pathStore.reloadForCurrentSubject()
      resourceStore.reloadForCurrentSubject()
    } catch (e) {
      console.warn('[Profile] 切换科目后 reload path/resource 失败', e)
    }
  }

  /* ===== 发送消息 ===== */

  async function sendMessage(content: string) {
    // 取消上一次未完成的流式请求，避免竞态
    if (chatAbortController) {
      chatAbortController.abort()
      chatAbortController = null
    }
    if (streamingTimer) {
      clearInterval(streamingTimer)
      streamingTimer = null
    }

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      isStreaming: false,
    }
    chatMessages.value.push(userMsg)

    const aiMsgId = `msg-${Date.now()}-ai`
    const aiMsg: ChatMessage = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    chatMessages.value.push(aiMsg)

    isStreaming.value = true
    streamingContent.value = ''

    // 检测确认操作
    if (needsConfirmation.value) {
      if (content.includes('确认') || content.includes('无误') || content.includes('没问题')) {
        profileData.value.phase = 'stable'
        simulateStreaming(aiMsgId, '画像已确认生效！✅\n\n所有 7 个智能体将基于你的画像生成个性化内容，包括学习路径、推荐资源、练习题目等。\n\n后续如有变动，随时可以告诉我修改画像。', false)
        return
      }
    }

    // 构建 GLM API 请求消息
    let glmMessages: { role: 'system' | 'user' | 'assistant'; content: string }[]
    if (profileData.value.phase === 'stable' || profileData.value.phase === 'supplement') {
      glmMessages = buildSupplementMessages(content, profileData.value)
    } else {
      const round = profileData.value.dialogueRound
      glmMessages = buildInitialMessages(round, content, profileData.value)
    }

    // 调用 GLM API 流式输出
    chatAbortController = chatGLM(
      glmMessages,
      // onChunk: 流式文本片段
      (text: string) => {
        streamingContent.value += text
        const msg = chatMessages.value.find(m => m.id === aiMsgId)
        if (msg) msg.content = streamingContent.value

        // 实时解析画像更新
        const parsed = parseProfileUpdate(streamingContent.value)
        if (parsed) applyParsedUpdate(parsed)
        const summary = parseProfileSummary(streamingContent.value)
        if (summary) applyParsedUpdate(summary)
      },
      // onDone: 流式结束
      () => {
        chatAbortController = null
        isStreaming.value = false
        const msg = chatMessages.value.find(m => m.id === aiMsgId)
        if (msg) msg.isStreaming = false

        // 初次构建阶段推进轮次
        if (profileData.value.phase === 'initial') {
          advanceDialogueRound()
        }
      },
      // onError: API 出错，提示用户
      (_error: Error) => {
        chatAbortController = null
        isStreaming.value = false
        console.error('[DeepSeek API 请求失败]', _error.message)
        
        // 给用户明确的错误提示
        const errorMsg = _error.message.includes('余额不足') 
          ? 'API 余额不足，请检查账户余额'
          : _error.message.includes('API Key')
          ? 'API Key 无效，请检查配置'
          : _error.message.includes('网络') || _error.message.includes('fetch')
          ? '网络连接失败，请检查网络后重试'
          : 'AI 服务暂时不可用，请稍后重试'
        
        import('ant-design-vue').then(({ message }) => message.error(errorMsg, 5)).catch(() => {})
        
        // 重置消息状态
        streamingContent.value = ''
        const msg = chatMessages.value.find(m => m.id === aiMsgId)
        if (msg) {
          msg.content = `抱歉，AI 服务暂时不可用 😔\n\n**错误原因**: ${errorMsg}\n\n请稍后重试，或者刷新页面重新开始对话。`
          msg.isStreaming = false
        }
      },
    )
  }

  /** 根据用户消息提取画像维度并生成动态回复 */
  function handleMockReply(aiMsgId: string) {
    const userMsg = chatMessages.value
      .filter(m => m.role === 'user')
      .pop()?.content || ''

    // 检测用户是否在提问
    const isQuestion = /[?？怎么什么为什么如何哪里多少哪些谁何时]/u.test(userMsg)

    const updatedPairs: string[] = []
    const dimLabels: string[] = []

    // 尝试从用户消息中提取所有维度的信息（不再限制于当前轮次）
    const allDimKeys: ProfileAllDimensionKey[] = [
      'major', 'grade', 'base_level', 'weak_points',
      'study_goal', 'cognitive_style', 'study_rhythm', 'interest_preference',
    ]

    for (const dimKey of allDimKeys) {
      if (dimKey === 'weak_points') {
        const points = extractWeakPoints(userMsg)
        if (points.length > 0) {
          updateDimension('weak_points', '', points)
          updatedPairs.push(`weak_points:${points.join(',')}`)
          dimLabels.push(`⚡ **薄弱知识点**：${points.join('、')}`)
        }
      } else {
        const extracted = extractDimension(userMsg, dimKey)
        if (extracted) {
          updateDimension(dimKey, extracted)
          updatedPairs.push(`${dimKey}:${extracted}`)
          const meta = DIMENSION_META[dimKey]
          dimLabels.push(`${meta.icon} **${meta.name}**：${extracted}`)
        }
      }
    }

    // 检查所有可采集维度是否已收集完成（排除自动计算的动态维度）
    const collectibleDims = profileData.value.dimensions.filter(d =>
      d.key !== 'knowledge_mastery' && d.key !== 'exercise_completion' && d.key !== 'learning_engagement'
    )
    const filledCount = collectibleDims.filter(d => d.value > 0).length
    const totalCount = collectibleDims.length
    const allFilled = filledCount >= totalCount

    if (updatedPairs.length > 0) {
      const updateBlock = updatedPairs.join('|')

      if (allFilled) {
        // 所有维度已收集完成，输出总结
        const allLabels = profileData.value.dimensions
          .filter(d => d.value > 0 && d.key !== 'weak_points')
          .map(d => `- ${DIMENSION_META[d.key].icon} **${DIMENSION_META[d.key].name}**：${d.label}`)
          .join('\n')
        const weakLabel = profileData.value.weak_points.length > 0
          ? `\n- ⚡ **薄弱知识点**：${profileData.value.weak_points.join('、')}`
          : ''
        const summaryBlock = profileData.value.dimensions
          .filter(d => d.value > 0)
          .map(d => `${d.key}:${d.label}`)
          .join('|')

        const reply = `所有维度已收集完毕！🎉\n\n\`\`\`profile-update\n${updateBlock}\n\`\`\`\n\n---\n\n**📋 画像总结确认**\n\n你的 8 维度学习画像如下：\n${allLabels}${weakLabel}\n\n\`\`\`profile-summary\n${summaryBlock}\n\`\`\`\n\n如以上信息有误请告诉我修改。确认无误后画像将生效！`
        simulateStreaming(aiMsgId, reply, false)
      } else {
        // 还有维度未收集，友好询问
        const missing: string[] = []
        const dimNames: Record<ProfileAllDimensionKey, string> = {
          major: '专业方向',
          grade: '年级水平',
          base_level: '基础水平',
          weak_points: '薄弱知识点',
          study_goal: '学习目标',
          cognitive_style: '认知风格',
          study_rhythm: '学习节奏',
          interest_preference: '内容偏好',
          learning_engagement: '学习投入度',
          knowledge_mastery: '知识掌握度',
          exercise_completion: '练习完成度',
        }
        for (const dim of profileData.value.dimensions) {
          if (dim.value === 0) {
            missing.push(dimNames[dim.key as ProfileAllDimensionKey] || dim.name)
          }
        }

        const reply = `已提取以下信息：\n\n${dimLabels.join('\n')}\n\n\`\`\`profile-update\n${updateBlock}\n\`\`\`\n\n还有 ${missing.length} 个维度未收集：${missing.join('、')}。你可以继续告诉我这些信息，或者按你的方式自由表达！`
        simulateStreaming(aiMsgId, reply, true)
      }
    } else {
      // 没有提取到任何维度信息
      if (isQuestion) {
        // 用户在提问，友好回应并引导
        const missing: string[] = []
        const dimNames: Record<ProfileAllDimensionKey, string> = {
          major: '专业方向',
          grade: '年级水平',
          base_level: '基础水平',
          weak_points: '薄弱知识点',
          study_goal: '学习目标',
          cognitive_style: '认知风格',
          study_rhythm: '学习节奏',
          interest_preference: '内容偏好',
          learning_engagement: '学习投入度',
          knowledge_mastery: '知识掌握度',
          exercise_completion: '练习完成度',
        }
        for (const dim of profileData.value.dimensions) {
          if (dim.value === 0) {
            missing.push(dimNames[dim.key as ProfileAllDimensionKey] || dim.name)
          }
        }
        const reply = `我理解你的问题！不过为了更好地帮助你，请先告诉我一些基本信息：${missing.join('、')}。你可以按自己的方式自由表达，不一定要按提示词回答。`
        simulateStreaming(aiMsgId, reply, false)
      } else {
        // 无法理解用户输入
        simulateStreaming(aiMsgId, `没能从你的回答中提取到有效信息 😅\n\n请告诉我你的专业、年级、基础水平、学习目标、薄弱知识点等，你可以按自己的方式自由表达！`, false)
      }
    }
  }

  function handleSupplementMessage(content: string, aiMsgId: string) {
    const dimKeywords: Record<ProfileAllDimensionKey, string[]> = {
      major: ['专业', '方向'],
      grade: ['年级'],
      base_level: ['基础', '水平'],
      weak_points: ['薄弱', '知识点', '难点', '困难'],
      study_goal: ['目标', '学习目标'],
      cognitive_style: ['风格', '认知', '学习方式'],
      study_rhythm: ['节奏', '时间', '习惯'],
      interest_preference: ['偏好', '内容', '喜欢'],
      learning_engagement: ['投入', '积极性', '参与'],
      knowledge_mastery: ['掌握', '知识掌握'],
      exercise_completion: ['练习', '做题', '完成度'],
    }

    const updatedPairs: string[] = []
    const dimLabels: string[] = []

    for (const [key, keywords] of Object.entries(dimKeywords)) {
      if (!keywords.some(kw => content.includes(kw))) continue

      if (key === 'weak_points') {
        const points = extractWeakPoints(content)
        if (points.length > 0) {
          updateDimension('weak_points', '', points)
          updatedPairs.push(`weak_points:${points.join(',')}`)
          dimLabels.push(`⚡ **薄弱知识点**：${points.join('、')}`)
        }
      } else {
        const extracted = extractDimension(content, key as ProfileAllDimensionKey)
        if (extracted) {
          updateDimension(key as ProfileAllDimensionKey, extracted)
          updatedPairs.push(`${key}:${extracted}`)
          const meta = DIMENSION_META[key as ProfileAllDimensionKey]
          dimLabels.push(`${meta.icon} **${meta.name}**：${extracted}`)
        }
      }
    }

    if (updatedPairs.length > 0) {
      const reply = `画像已更新！\n\n${dimLabels.join('\n')}\n\n\`\`\`profile-update\n${updatedPairs.join('|')}\n\`\`\`\n\n✓ 已修改的维度已同步更新，相关 Agent 将基于最新画像重新生成推荐内容。`
      simulateStreaming(aiMsgId, reply, false)
    } else {
      simulateStreaming(aiMsgId, '请告诉我你想修改哪个维度？比如"修改学习目标"或"补充薄弱知识点树和图"。', false)
    }
  }

  /** 通用模拟流式输出 */
  function simulateStreaming(aiMsgId: string, fullText: string, advanceRound = true) {
    // 清除之前的 interval，避免重叠
    if (streamingTimer) {
      clearInterval(streamingTimer)
      streamingTimer = null
    }

    let index = 0
    isStreaming.value = true

    streamingTimer = setInterval(() => {
      if (index < fullText.length) {
        const chunkSize = Math.min(2, fullText.length - index)
        streamingContent.value += fullText.slice(index, index + chunkSize)
        index += chunkSize

        const msg = chatMessages.value.find(m => m.id === aiMsgId)
        if (msg) msg.content = streamingContent.value

        // 实时解析画像更新
        const parsed = parseProfileUpdate(streamingContent.value)
        if (parsed) applyParsedUpdate(parsed)
        const summary = parseProfileSummary(streamingContent.value)
        if (summary) applyParsedUpdate(summary)
      } else {
        clearInterval(streamingTimer!)
        streamingTimer = null
        isStreaming.value = false
        const msg = chatMessages.value.find(m => m.id === aiMsgId)
        if (msg) msg.isStreaming = false
        // 仅在初始构建阶段推进轮次
        if (advanceRound) advanceDialogueRound()
      }
    }, 30)
  }

  /* ===== 对话轮次推进 ===== */

  function advanceDialogueRound() {
    if (profileData.value.phase !== 'initial') return

    // 只检查可对话采集的维度（排除自动计算的动态维度）
    const collectibleDims = profileData.value.dimensions.filter(d =>
      d.key !== 'knowledge_mastery' && d.key !== 'exercise_completion' && d.key !== 'learning_engagement'
    )
    const filledCount = collectibleDims.filter(d => d.value > 0).length
    const totalCount = collectibleDims.length

    // 如果所有可采集维度都收集完成，进入确认阶段
    if (filledCount >= totalCount) {
      // 不自动推进到 stable，等待用户确认
      return
    }

    // 根据当前轮次关注的维度是否已收集来决定是否推进
    const currentRound = profileData.value.dialogueRound
    if (currentRound >= 4) return

    const currentConfig = DIALOGUE_ROUNDS[currentRound - 1]
    if (!currentConfig) return

    // 检查当前轮次关注的维度是否都已收集
    const focusDimsFilled = currentConfig.focusDimensions.every(dimKey => {
      const dim = profileData.value.dimensions.find(d => d.key === dimKey)
      return dim && dim.value > 0
    })

    // 如果当前轮次关注的维度都已收集，推进到下一轮
    if (focusDimsFilled) {
      profileData.value.dialogueRound = currentRound + 1

      // 发送下一轮引导消息
      const nextConfig = DIALOGUE_ROUNDS[currentRound]
      if (nextConfig) {
        setTimeout(() => {
          const guideMsg: ChatMessage = {
            id: `msg-guide-${Date.now()}`,
            role: 'assistant',
            content: nextConfig.prompt,
            timestamp: new Date().toISOString(),
            isStreaming: false,
          }
          chatMessages.value.push(guideMsg)
        }, 500)
      }
    }
  }

  /* ===== 初始化对话 ===== */

  function initDialogue() {
    if (chatMessages.value.length > 0) return

    // 已确认的画像不再重置为 initial，进入 supplement 模式
    if (profileData.value.phase === 'stable') {
      profileData.value.phase = 'supplement'
      // 发送补充模式欢迎消息
      const supplementMsg: ChatMessage = {
        id: 'msg-supplement-welcome',
        role: 'assistant',
        content: `欢迎回来！🎉\n\n你当前的画像已确认生效。如果需要修改或补充任何维度（如学习目标、薄弱知识点、当前学习科目等），直接告诉我即可。\n\n例如：\n- "我想学英语动词时态" → 自动切换科目\n- "我的基础水平是进阶" → 更新基础水平\n- "我想改为项目实战目标" → 修改学习目标`,
        timestamp: new Date().toISOString(),
        isStreaming: false,
      }
      chatMessages.value.push(supplementMsg)
    } else {
      profileData.value.dialogueRound = 1
      profileData.value.phase = 'initial'

      // 发送第1轮引导
      const firstRound = DIALOGUE_ROUNDS[0]
      const guideMsg: ChatMessage = {
        id: 'msg-guide-1',
        role: 'assistant',
        content: firstRound.prompt,
        timestamp: new Date().toISOString(),
        isStreaming: false,
      }
      chatMessages.value.push(guideMsg)
    }
  }

  /** 确认画像生效 */
  function confirmProfile() {
    profileData.value.phase = 'stable'

    // 记录初始画像快照（作为对比基准）
    recordInitialSnapshot()

    // 保存画像到历史记录
    const historyName = `${profileData.value.major || '画像'} - ${new Date().toLocaleDateString('zh-CN')}`
    saveCurrentToHistory(historyName)
    
    const aiMsgId = `msg-${Date.now()}-ai`
    const aiMsg: ChatMessage = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    chatMessages.value.push(aiMsg)
    simulateStreaming(aiMsgId, '画像已确认生效！✅\n\n画像已保存到历史记录，下次登录可以选择使用。\n\n所有 7 个智能体将基于你的画像生成个性化内容，包括学习路径、推荐资源、练习题目等。\n\n后续如有变动，随时可以告诉我修改画像。', false)
  }

  /** 重置画像，重新开始对话 */
  function resetProfile() {
    profileData.value = createEmptyProfile()
    chatMessages.value = []
    streamingContent.value = ''
    isStreaming.value = false
    saveProfile()
    initDialogue()
  }

  /* ===== 完美雷达图展馆 — 快照逻辑 ===== */

  /** 检测是否达成完美雷达图（8维全部≥90） */
  const isPerfectRadar = computed(() => {
    const radarDims = (profileData.value.dimensions || []).filter(d => d.showOnRadar !== false)
    return radarDims.length > 0 && radarDims.every(d => d.value >= 90)
  })

  /** 计算相比初始画像的总提升分 */
  const growthFromInitial = computed(() => {
    const initial = profileData.value.initialSnapshot
    if (!initial) return 0
    const currentDims = (profileData.value.dimensions || []).filter(d => d.showOnRadar !== false)
    let totalGrowth = 0
    for (const dim of currentDims) {
      const initDim = initial.dimensions.find(id => id.key === dim.key)
      const initVal = initDim?.value || 0
      totalGrowth += Math.max(0, dim.value - initVal)
    }
    return totalGrowth
  })

  /** 生成当前画像快照 */
  function createSnapshot(title: string, description?: string): RadarSnapshot {
    const radarDims = (profileData.value.dimensions || []).filter(d => d.showOnRadar !== false)
    // 总分 = 所有雷达维度值之和（与 growthFromInitial 对齐）
    const totalScore = radarDims.reduce((sum, d) => sum + d.value, 0)

    return {
      id: `snapshot-${Date.now()}`,
      title,
      description,
      createdAt: new Date().toISOString(),
      subject: profileData.value.currentSubject || undefined,
      dimensions: radarDims.map(d => ({
        key: d.key,
        name: d.name,
        value: d.value,
        label: d.label,
      })),
      totalScore,
      growthFromInitial: growthFromInitial.value,
      isPerfect: isPerfectRadar.value,
      summary: {
        studyMinutes: profileData.value.totalStudyMinutes || 0,
        completedStages: profileData.value.completedStageCount || 0,
        completedResources: profileData.value.completedResourceCount || 0,
        completedAssess: profileData.value.completedAssessCount || 0,
        streakDays: profileData.value.streakDays || 0,
      },
      profileData: JSON.parse(JSON.stringify(profileData.value)),
      initialSnapshot: profileData.value.initialSnapshot
        ? { ...profileData.value.initialSnapshot }
        : undefined,
    }
  }

  /** 保存快照（自动/手动） */
  function saveSnapshot(title: string, description?: string): RadarSnapshot {
    const snapshot = createSnapshot(title, description)
    if (!profileData.value.snapshots) profileData.value.snapshots = []
    profileData.value.snapshots.unshift(snapshot)
    // 保留最近 50 个快照
    if (profileData.value.snapshots.length > 50) {
      profileData.value.snapshots = profileData.value.snapshots.slice(0, 50)
    }
    saveProfile()
    return snapshot
  }

  /** 删除快照 */
  function deleteSnapshot(snapshotId: string): void {
    if (!profileData.value.snapshots) return
    profileData.value.snapshots = profileData.value.snapshots.filter(s => s.id !== snapshotId)
    saveProfile()
  }

  /** 记录初始画像快照（phase→stable时调用） */
  function recordInitialSnapshot(): void {
    if (profileData.value.initialSnapshot) return // 已记录过
    // 只记录雷达图维度（与 createSnapshot 的 totalScore 计算方式对齐）
    const radarDims = profileData.value.dimensions.filter(d => d.showOnRadar !== false)
    profileData.value.initialSnapshot = {
      dimensions: radarDims.map(d => ({
        key: d.key,
        name: d.name,
        value: d.value,
        label: d.label,
      })),
      createdAt: new Date().toISOString(),
    }
  }

  /** 完美达成弹窗控制 */
  const showPerfectToast = ref(false)
  const perfectAlreadySaved = ref(false) // 防止重复弹窗

  /* ===== 画像增量更新引擎 ===== */

  /**
   * 核心方法：根据学习事件增量更新画像
   * - 完成学习阶段 → 提升基础水平、移除薄弱点
   * - 完成学习资源 → 提升对应维度分数
   * - 完成测评 → 根据得分调整薄弱点
   *
   * 画像在任何阶段（initial/supplement/stable）均可被学习事件更新，
   * 确保"随学随新"——用户学习后立即看到画像和雷达图变化。
   */
  function applyLearningEvent(event: LearningEvent) {
    // 确保数组字段存在（兼容旧数据）
    if (!profileData.value.learningEvents) profileData.value.learningEvents = []
    if (!profileData.value.updateLogs) profileData.value.updateLogs = []
    if (!profileData.value.masteredPoints) profileData.value.masteredPoints = []
    if (!profileData.value.dimensions) {
      // 极端情况：dimensions 丢失，重建空画像
      profileData.value = createEmptyProfile()
      return
    }

    console.log('[Profile] 记录学习事件:', event.type, event.sourceId, event.timestamp)

    // 记录学习事件
    profileData.value.learningEvents.push(event)

    // 保留最近 100 条事件
    if (profileData.value.learningEvents.length > 100) {
      profileData.value.learningEvents = profileData.value.learningEvents.slice(-100)
    }

    console.log('[Profile] 当前学习事件数量:', profileData.value.learningEvents.length)

    const changes: ProfileUpdateLog['changes'] = {} as any
    let affectedCount = 0

    switch (event.type) {
      case 'stage_complete':
        affectedCount += handleStageComplete(event, changes)
        break
      case 'resource_complete':
        affectedCount += handleResourceComplete(event, changes)
        break
      case 'assess_complete':
        affectedCount += handleAssessComplete(event, changes)
        break
    }

    // 更新连续学习天数
    updateStreakDays()

    // 记录更新日志
    if (affectedCount > 0) {
      const log: ProfileUpdateLog = {
        id: `log-${Date.now()}`,
        timestamp: new Date().toISOString(),
        source: event.type === 'stage_complete' ? 'path_complete'
          : event.type === 'resource_complete' ? 'resource_complete'
          : 'assess_complete',
        description: event.description,
        changes,
        affectedCount,
      }
      profileData.value.updateLogs.push(log)
      // 保留最近 50 条日志
      if (profileData.value.updateLogs.length > 50) {
        profileData.value.updateLogs = profileData.value.updateLogs.slice(-50)
      }
    }

    // 通知前端画像已更新（用于雷达图闪烁提示等）
    signalProfileUpdate()

    // 同步动态维度（知识掌握度、练习完成度、学习投入度）
    syncDynamicDimensions()

    // 设置画像变化信息，用于智能体联动
    if (affectedCount > 0) {
      profileChangeInfo.value = {
        event,
        changedDims: Object.keys(changes),
        changeType: determineChangeType(changes),
      }
    }

    // 完美雷达图检测
    if (affectedCount > 0 && isPerfectRadar.value && !perfectAlreadySaved.value) {
      perfectAlreadySaved.value = true
      showPerfectToast.value = true
      // 3秒后自动关闭提示
      setTimeout(() => { showPerfectToast.value = false }, 5000)
    }

    // 同步科目独立维度到覆盖层
    if (profileData.value.currentSubject && affectedCount > 0) {
      saveCurrentOverlay()
    }

    // 立即持久化
    saveProfile()
  }

  /** 处理完成学习阶段 */
  function handleStageComplete(event: LearningEvent, changes: ProfileUpdateLog['changes']): number {
    let affected = 0

    // 1. 提升基础水平（使用 bonus 增量机制）
    const baseDim = profileData.value.dimensions.find(d => d.key === 'base_level')
    if (baseDim) {
      const before = baseDim.value
      const beforeLabel = baseDim.label
      // 里程碑爆发：每完成一个阶段 +5 bonus
      addBonus('base_level', Math.min(10, Math.max(5, 100 - baseDim.value)))
      // 更新 label
      baseDim.label = scoreToBaseLevel(baseDim.value)
      baseDim.enumValue = baseDim.label
      profileData.value.base_level = baseDim.label as ProfileBaseLevel
      if (baseDim.value !== before) {
        changes['base_level'] = { before, after: baseDim.value, beforeLabel, afterLabel: baseDim.label }
        affected++
      }
    }

    // 2. 移除已掌握的薄弱点（含爆发奖励）
    const mastered = event.knowledgePoints.filter(kp =>
      profileData.value.weak_points.some(wp => wp.toLowerCase().includes(kp.toLowerCase()) || kp.toLowerCase().includes(wp.toLowerCase()))
    )
    if (mastered.length > 0) {
      const weakDim = profileData.value.dimensions.find(d => d.key === 'weak_points')
      if (weakDim) {
        const before = weakDim.value
        const beforeLabel = weakDim.label
        profileData.value.weak_points = profileData.value.weak_points.filter(
          wp => !mastered.some(m => wp.toLowerCase().includes(m.toLowerCase()) || m.toLowerCase().includes(wp.toLowerCase()))
        )
        profileData.value.masteredPoints = [...new Set([...profileData.value.masteredPoints, ...mastered])]
        // 重新计算薄弱点分数
        const newScore = computeScore('weak_points', '', profileData.value.weak_points.length)
        // 爆发奖励：每移除一个薄弱点额外+10，全部清零额外+15
        let burstBonus = mastered.length * 10
        if (profileData.value.weak_points.length === 0) burstBonus += 15
        weakDim.value = Math.min(95, newScore + burstBonus)
        weakDim.baseScore = newScore
        weakDim.bonus = Math.min(burstBonus, Math.floor(newScore * 0.3) || 15)
        weakDim.label = profileData.value.weak_points.length > 0 ? `${profileData.value.weak_points.length}项薄弱` : '无明显薄弱'
        weakDim.enumValue = weakDim.label
        if (weakDim.value !== before) {
          changes['weak_points'] = { before, after: weakDim.value, beforeLabel, afterLabel: weakDim.label }
          affected++
        }
      }
    }

    // 3. 累计学习时长
    profileData.value.totalStudyMinutes += 45
    profileData.value.completedStageCount++

    return affected
  }

  /** 处理完成学习资源（使用 addBonus 增量机制） */
  function handleResourceComplete(event: LearningEvent, changes: ProfileUpdateLog['changes']): number {
    let affected = 0

    // 根据资源类型提升对应维度（使用 addBonus）
    const resType = event.resourceType
    if (resType === 'code') {
      addBonus('cognitive_style', 3)
      addBonus('interest_preference', 3)
      affected += recordChange('cognitive_style', changes)
      affected += recordChange('interest_preference', changes)
    } else if (resType === 'video') {
      addBonus('cognitive_style', 2)
      addBonus('interest_preference', 2)
      affected += recordChange('cognitive_style', changes)
      affected += recordChange('interest_preference', changes)
    } else if (resType === 'document') {
      addBonus('cognitive_style', 2)
      addBonus('interest_preference', 2)
      affected += recordChange('cognitive_style', changes)
      affected += recordChange('interest_preference', changes)
    } else if (resType === 'mindmap') {
      addBonus('interest_preference', 3)
      affected += recordChange('interest_preference', changes)
    } else if (resType === 'exercise') {
      addBonus('interest_preference', 3)
      addBonus('base_level', 2)
      affected += recordChange('interest_preference', changes)
      affected += recordChange('base_level', changes)
    } else if (resType === 'knowledge-graph') {
      addBonus('interest_preference', 3)
      addBonus('cognitive_style', 2)
      affected += recordChange('interest_preference', changes)
      affected += recordChange('cognitive_style', changes)
    } else if (resType === 'quiz') {
      addBonus('interest_preference', 3)
      addBonus('base_level', 3)
      affected += recordChange('interest_preference', changes)
      affected += recordChange('base_level', changes)
    }

    // 累计学习时长
    profileData.value.totalStudyMinutes += 20
    profileData.value.completedResourceCount++

    return affected
  }

  /** 处理完成测评（使用 addBonus 增量机制） */
  function handleAssessComplete(event: LearningEvent, changes: ProfileUpdateLog['changes']): number {
    let affected = 0
    const score = event.score ?? 0

    // 1. 根据得分调整基础水平
    if (score >= 80) {
      // 高分 → 基础水平 bonus 提升
      addBonus('base_level', 5)
      affected += recordChange('base_level', changes)
      // 高分知识点从薄弱点移除（含爆发奖励）
      const mastered = event.knowledgePoints.filter(kp =>
        profileData.value.weak_points.some(wp => wp.toLowerCase().includes(kp.toLowerCase()) || kp.toLowerCase().includes(wp.toLowerCase()))
      )
      if (mastered.length > 0) {
        const weakDim = profileData.value.dimensions.find(d => d.key === 'weak_points')
        if (weakDim) {
          const before = weakDim.value
          const beforeLabel = weakDim.label
          profileData.value.weak_points = profileData.value.weak_points.filter(
            wp => !mastered.some(m => wp.toLowerCase().includes(m.toLowerCase()) || m.toLowerCase().includes(wp.toLowerCase()))
          )
          profileData.value.masteredPoints = [...new Set([...profileData.value.masteredPoints, ...mastered])]
          const newScore = computeScore('weak_points', '', profileData.value.weak_points.length)
          let burstBonus = mastered.length * 10
          if (profileData.value.weak_points.length === 0) burstBonus += 15
          weakDim.value = Math.min(95, newScore + burstBonus)
          weakDim.baseScore = newScore
          weakDim.bonus = Math.min(burstBonus, Math.floor(newScore * 0.3) || 15)
          weakDim.label = profileData.value.weak_points.length > 0 ? `${profileData.value.weak_points.length}项薄弱` : '无明显薄弱'
          weakDim.enumValue = weakDim.label
          if (weakDim.value !== before) {
            changes['weak_points'] = { before, after: weakDim.value, beforeLabel, afterLabel: weakDim.label }
            affected++
          }
        }
      }
    } else if (score < 60) {
      // 低分 → 新增薄弱点
      const newWeak = event.knowledgePoints.filter(kp =>
        !profileData.value.weak_points.some(wp => wp.toLowerCase().includes(kp.toLowerCase()) || kp.toLowerCase().includes(wp.toLowerCase()))
      )
      if (newWeak.length > 0) {
        const weakDim = profileData.value.dimensions.find(d => d.key === 'weak_points')
        if (weakDim) {
          const before = weakDim.value
          const beforeLabel = weakDim.label
          profileData.value.weak_points = [...profileData.value.weak_points, ...newWeak]
          weakDim.value = computeScore('weak_points', '', profileData.value.weak_points.length)
          weakDim.baseScore = weakDim.value
          weakDim.bonus = 0
          weakDim.label = `${profileData.value.weak_points.length}项薄弱`
          weakDim.enumValue = weakDim.label
          if (weakDim.value !== before) {
            changes['weak_points'] = { before, after: weakDim.value, beforeLabel, afterLabel: weakDim.label }
            affected++
          }
        }
      }
    }

    profileData.value.completedAssessCount++
    profileData.value.totalStudyMinutes += 15

    return affected
  }

  /** 记录维度变化到 changes 对象（配合 addBonus 使用） */
  function recordChange(dimKey: ProfileAllDimensionKey, changes: ProfileUpdateLog['changes']): number {
    const dim = profileData.value.dimensions.find(d => d.key === dimKey)
    if (!dim) return 0
    // 更新 label（如果分数变化足够大，可能升级枚举值）
    if (dimKey === 'base_level') {
      dim.label = scoreToBaseLevel(dim.value)
      dim.enumValue = dim.label
      profileData.value.base_level = dim.label as ProfileBaseLevel
    }
    // 只有 value 确实变化了才记录
    if (changes[dimKey]) return 0 // 已记录过
    return 1
  }

  /** 微调维度分数（增量更新辅助方法，保留兼容） */
  function bumpDimension(
    dimKey: ProfileAllDimensionKey,
    _targetEnum: string,
    increment: number,
    changes: ProfileUpdateLog['changes'],
  ): number {
    const dim = profileData.value.dimensions.find(d => d.key === dimKey)
    if (!dim) return 0

    const before = dim.value
    const beforeLabel = dim.label
    // 使用 addBonus 代替直接修改 value
    addBonus(dimKey, increment)

    if (dim.value !== before) {
      if (dimKey === 'base_level') {
        dim.label = scoreToBaseLevel(dim.value)
        dim.enumValue = dim.label
        profileData.value.base_level = dim.label as ProfileBaseLevel
      }
      changes[dimKey] = { before, after: dim.value, beforeLabel, afterLabel: dim.label }
      return 1
    }
    return 0
  }

  /** 分数 → 基础水平枚举 */
  function scoreToBaseLevel(score: number): string {
    if (score >= 90) return '精通'
    if (score >= 70) return '进阶'
    if (score >= 50) return '中等'
    if (score >= 25) return '基础'
    return '入门'
  }

  /** 更新连续学习天数 */
  function updateStreakDays() {
    const events = profileData.value.learningEvents || []
    if (!events.length) { profileData.value.streakDays = 0; return }

    // 按日期去重
    const dates = [...new Set(events.map(e => e.timestamp.slice(0, 10)))].sort().reverse()
    const today = new Date().toISOString().slice(0, 10)

    let streak = 0
    let checkDate = new Date(today)

    for (let i = 0; i < 365; i++) {
      const dateStr = checkDate.toISOString().slice(0, 10)
      if (dates.includes(dateStr)) {
        streak++
        checkDate.setDate(checkDate.getDate() - 1)
      } else if (i === 0) {
        // 今天还没学习，从昨天开始算
        checkDate.setDate(checkDate.getDate() - 1)
        continue
      } else {
        break
      }
    }

    profileData.value.streakDays = streak
  }

  /** 获取最近 N 条更新日志 */
  function getRecentLogs(count = 10): ProfileUpdateLog[] {
    return (profileData.value.updateLogs || []).slice(-count).reverse()
  }

  /** 获取最近 N 条学习事件 */
  function getRecentEvents(count = 20): LearningEvent[] {
    return (profileData.value.learningEvents || []).slice(-count).reverse()
  }

  /** 画像是否已有数据（非空画像） */
  const hasProfile = computed(() =>
    profileData.value.phase !== 'initial' || (Array.isArray(profileData.value.dimensions) && profileData.value.dimensions.some(d => d.value > 0))
  )

  /** 加载雷达图数据（启用后端时） */
  // async function loadRadarData() {
  //   try {
  //     const data = await getRadarData()
  //     if (data) profileData.value = data
  //   } catch {}
  // }

  return {
    chatMessages,
    profileData,
    streamingContent,
    isStreaming,
    isLoadingProfile,
    profileJustUpdated,
    profileChangeInfo,
    completionRate,
    completedDims,
    totalDims,
    knowledgeMastery,
    exerciseCompletion,
    learningEngagement,
    syncDynamicDimensions,
    weakDimensions,
    currentRoundConfig,
    quickReplies,
    needsConfirmation,
    hasProfile,
    sendMessage,
    initDialogue,
    confirmProfile,
    resetProfile,
    parseProfileUpdate,
    // 增量更新引擎
    applyLearningEvent,
    getRecentLogs,
    getRecentEvents,
    saveProfile,
    reloadProfileForUser,
    // 新增：评分增量机制
    addBonus,
    tryUpgradeEnum,
    // 新增：完美雷达图展馆
    isPerfectRadar,
    growthFromInitial,
    saveSnapshot,
    deleteSnapshot,
    recordInitialSnapshot,
    createSnapshot,
    showPerfectToast,
    perfectAlreadySaved,
    // 画像历史相关
    profileHistories,
    isLoadingHistories,
    showHistorySelector,
    loadProfileHistories,
    switchToHistory,
    deleteHistory,
    saveCurrentToHistory,
    // 多科目支持
    effectiveProfile,
    currentOverlay,
    switchSubject,
  }
})
