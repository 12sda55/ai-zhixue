import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type {
  PathStage, PathStageExtended, PathResource, ResourceType,
  PathGenerationStatus, PathDiff, ProfileData, LearningEvent,
} from '../../../shared/types'
import { RESOURCE_TYPE_MAP } from '../../../shared/utils/constants'
import { chatGLM } from '../../../shared/api/glmApi'
import {
  buildPathGenerationMessages,
  buildPathRegenerationMessages,
  buildChangeDescription,
} from '../prompts/pathPrompts'
import { useProfileStore, filterRelevantWeakPoints } from '../../profile/stores/profileStore'
import { useAuthStore } from '../../auth/stores/authStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { allocate, applyAssignments } from '../../resource/services/allocator'
import request from '../../../shared/utils/request'
import { getFilteredProfile, parsePathPlan } from '../services/pathParsing'

const PATH_STORAGE_KEY = 'ai_learning_path'
const PATH_CLEARED_KEY = 'ai_learning_path_cleared'

export const usePathStore = defineStore('path', () => {
  /* ===== 按 subject 隔离的 storage key =====
   * 修复跨科目污染 bug：先生成数据结构再切英语时，pathStore.stages 残留数据结构路径，
   * 导致英语会话里显示数据结构视频。按 subject 隔离 key + switchSubject 触发 reload。
   */
  function currentSubject(): string {
    try {
      const profileStore = useProfileStore()
      return profileStore.profileData.currentSubject || profileStore.profileData.major || 'default'
    } catch { return 'default' }
  }

  function pathStorageKey(userId: string): string {
    return `${PATH_STORAGE_KEY}_${userId}_${currentSubject()}`
  }

  function pathClearedKey(userId: string): string {
    return `${PATH_CLEARED_KEY}_${userId}_${currentSubject()}`
  }

  /** 迁移旧格式存储（无 subject 后缀）到当前 subject 的 key，避免数据丢失 */
  function migrateLegacyStorage(userId: string) {
    const newKey = pathStorageKey(userId)
    if (localStorage.getItem(newKey)) return // 新 key 已有数据，不迁移

    const legacyKey = `${PATH_STORAGE_KEY}_${userId}`
    const legacy = localStorage.getItem(legacyKey)
    if (legacy) {
      try {
        const parsed = JSON.parse(legacy)
        if (Array.isArray(parsed) && parsed.length > 0) {
          localStorage.setItem(newKey, legacy)
          console.log(`[Path] 迁移旧路径数据到 subject=${currentSubject()}（${parsed.length} 个阶段）`)
        }
        localStorage.removeItem(legacyKey)
      } catch { /* ignore */ }
    }

    // 迁移 cleared 标记
    const legacyCleared = localStorage.getItem(`${PATH_CLEARED_KEY}_${userId}`)
    if (legacyCleared) {
      localStorage.setItem(pathClearedKey(userId), legacyCleared)
      localStorage.removeItem(`${PATH_CLEARED_KEY}_${userId}`)
    }
  }

  /* ===== 从 localStorage 加载路径 ===== */
  function loadStages(): PathStageExtended[] {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      migrateLegacyStorage(userId)
      const stored = localStorage.getItem(pathStorageKey(userId))
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          // 修复缓存中的"未命名资源"
          return fixUnnamedResources(parsed)
        }
      }
    } catch (e) {
      console.warn('[Path] 加载路径失败', e)
    }
    return []
  }

  /* ===== 修复缓存中的"未命名资源" ===== */
  function fixUnnamedResources(stages: PathStageExtended[]): PathStageExtended[] {
    const profileStore = useProfileStore()
    // 优先使用当前科目，其次用专业
    const subject = profileStore.profileData.currentSubject || profileStore.profileData.major || '计算机'
    const major = subject
    const weakPoints = filterRelevantWeakPoints(
      profileStore.profileData.weak_points || [],
      subject,
    )

    // 资源名称生成辅助函数
    function generateResourceName(
      stageTitle: string,
      resourceType: ResourceType,
      index: number,
      major: string,
      weakPoints: string[]
    ): string {
      const topic = stageTitle.replace(/基础|进阶|综合|专项|突破|概念|应用|实战|复习/g, '').trim() || weakPoints[0] || major
      const typeSuffixes: Record<string, string[]> = {
        'document': ['详解', '原理', '指南', '教程', '笔记'],
        'video': ['视频讲解', '动画演示', '操作演示', '案例分析', '教学视频'],
        'exercise': ['练习题', '测试题', '实战练习', '综合测试', '专项练习'],
        'code': ['代码实战', '编程练习', '代码示例', '项目实战', '代码模板'],
        'mindmap': ['思维导图', '知识图谱', '概念导图', '知识体系', '学习路线图'],
        'extension': ['拓展阅读', '参考资料', '进阶资料', '相关文献', '延伸学习'],
      }
      const suffixes = typeSuffixes[resourceType] || typeSuffixes['document']
      const suffix = suffixes[index % suffixes.length]
      return `${topic}${suffix}`
    }

    return stages.map((stage, i) => {
      const fixedResources = stage.resources.map((res, ri) => {
        // 修复 status='active' 但无 resourceRef 的脏数据（旧缓存残留）
        // 这会导致工作台显示"已生成"但实际无内容的小节
        if (res.status === 'active' && !res.resourceRef) {
          console.log(`[Path] 修复脏数据: 资源 "${res.name}" status=active 但无 resourceRef，重置为 pending`)
          res = { ...res, status: 'pending' as const }
        }
        // 检测模糊或无效的资源名称
        const vaguePatterns = ['练习题', '教程', '资料', '学习资料', '参考', '未命名', '资源', '资源名称', 'resource', 'name', 'title', '-']
        const isVague = res.name.trim() === '' ||
                        vaguePatterns.some(v => res.name.includes(v)) ||
                        res.name.length < 3

        if (isVague) {
          const newName = generateResourceName(stage.title, res.type, ri, major, weakPoints)
          console.log(`[Path] 修复缓存资源名称: "${res.name}" -> "${newName}"`)
          return { ...res, name: newName }
        }
        return res
      })
      return { ...stage, resources: fixedResources }
    })
  }

  /* ===== State ===== */

  const stages = ref<PathStageExtended[]>([])
  const generationStatus = ref<PathGenerationStatus>('idle')
  const streamingContent = ref('')
  const generationProgress = ref('')
  const generationError = ref('')
  const pathSummary = ref('')

  const isEditing = ref(false)
  const editingStageId = ref<string | null>(null)
  const editSnapshot = ref<PathStageExtended[]>([])

  const pathDiff = ref<PathDiff | null>(null)
  const previousStages = ref<PathStageExtended[]>([])

  // 多路径归档
  interface PathArchiveItem {
    id: string
    name: string
    stages: PathStageExtended[]
    profileSnapshot: any
    createdAt: string
  }
  const PATH_ARCHIVES_KEY = 'ai_learning_path_archives'
  const pathArchives = ref<PathArchiveItem[]>([])

  let abortController: AbortController | null = null
  let profileWatchStop: (() => void) | null = null
  let profileUpdateTimer: ReturnType<typeof setTimeout> | null = null
  const PROFILE_UPDATE_DELAY = 5000 // 5秒延迟，积累多次变化后统一更新

  // 初始化：加载并修复缓存数据
  const loadedStages = loadStages()
  stages.value = loadedStages
  // 如果有修复，立即保存
  if (loadedStages.length > 0) {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      localStorage.setItem(pathStorageKey(userId), JSON.stringify(loadedStages))
    } catch (e) {
      console.warn('[Path] 保存修复后的路径失败', e)
    }
    // 旧数据兼容：补分配 resourceRef（allocator 跑一次，给没 resourceRef 的 PathResource 分配）
    try {
      linkResourcesToGenerated()
    } catch (e) {
      console.warn('[Path] 初始化资源分配失败', e)
    }
  }

  /* ===== Computed ===== */

  const hasPath = computed(() => stages.value.length > 0)

  /* ===== 持久化路径到 localStorage ===== */
  function saveStages() {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      localStorage.setItem(pathStorageKey(userId), JSON.stringify(stages.value))
      // 同步到后端
      syncPathToBackend()
    } catch (e) {
      console.warn('[Path] 保存路径失败', e)
    }
  }

  let pathSyncTimer: ReturnType<typeof setTimeout> | null = null
  function syncPathToBackend() {
    const authStore = useAuthStore()
    if (!authStore.token || !authStore.user?.id) return

    if (pathSyncTimer) clearTimeout(pathSyncTimer)
    pathSyncTimer = setTimeout(async () => {
      try {
        await request.put('/data/path', {
          data: {
            stages: stages.value.map(s => ({
              id: s.id,
              title: s.title,
              status: s.status,
              suggestedDays: s.suggestedDays,
              actualDays: s.actualDays,
              progress: s.progress,
              reason: s.reason,
              reasonType: s.reasonType,
              learningTips: s.learningTips,
              resources: (s.resources || []).map(r => ({
                id: r.id,
                type: r.type,
                name: r.name,
                status: r.status,
              })),
            })),
          },
        })
        console.log('[Path] 后端同步完成')
      } catch (e) {
        console.warn('[Path] 后端同步失败', e)
      }
    }, 2000)
  }

  // 监听路径变化自动持久化（防抖 500ms）
  let pathSaveTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    () => stages.value,
    () => {
      if (pathSaveTimer) clearTimeout(pathSaveTimer)
      pathSaveTimer = setTimeout(() => saveStages(), 500)
    },
    { deep: true },
  )

  // 监听用户切换，重新加载路径
  watch(
    () => {
      try {
        const authStore = useAuthStore()
        return authStore.user?.id || 'guest'
      } catch { return 'guest' }
    },
    () => {
      stages.value = loadStages()
    },
  )

  // 监听科目切换，自动重新加载路径（架构加固：兜底机制）
  // 即使不通过 switchSubject 显式调用，任何 currentSubject 变化都能触发 reload
  watch(
    () => {
      try {
        const profileStore = useProfileStore()
        return profileStore.profileData.currentSubject || ''
      } catch { return '' }
    },
    (newSubject, oldSubject) => {
      if (newSubject && oldSubject && newSubject !== oldSubject) {
        console.log(`[Path] 检测到科目切换: ${oldSubject} → ${newSubject}, 重新加载路径`)
        reloadForCurrentSubject()
      }
    },
  )
  const totalProgress = computed(() => {
    if (!stages.value.length) return 0
    return Math.round(stages.value.reduce((sum, s) => sum + s.progress, 0) / stages.value.length)
  })
  const totalDays = computed(() => stages.value.reduce((sum, s) => sum + s.suggestedDays, 0))
  const activeStageIndex = computed(() => stages.value.findIndex(s => s.status === 'active'))

  /* ===== 路径生成 ===== */

  const GENERATION_TIMEOUT_MS = 30000  // 30秒超时，防止 API 卡住

  function generatePath() {
    // 取消上一次未完成的生成，避免竞态
    cancelGeneration()

    const profileStore = useProfileStore()
    const profileData = getFilteredProfile(profileStore.profileData)

    // 用户主动生成，清除"已清空"标记
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      localStorage.removeItem(pathClearedKey(userId))
    } catch { /* ignore */ }

    generationStatus.value = 'generating'
    streamingContent.value = ''
    generationProgress.value = '正在分析你的学习画像…'
    generationError.value = ''
    pathSummary.value = ''
    pathDiff.value = null

    // 设置超时，防止 API 卡住
    const timeoutId = setTimeout(() => {
      console.warn('[Path] API 调用超时，触发本地 fallback')
      cancelGeneration()
      generateFallbackPath(profileData)
      generationStatus.value = 'done'
      generationProgress.value = '路径生成完成！'
    }, GENERATION_TIMEOUT_MS)

    const messages = buildPathGenerationMessages(profileData)

    abortController = chatGLM(
      messages,
      // onChunk
      (text: string) => {
        streamingContent.value += text
        updateGenerationProgress(streamingContent.value)
      },
      // onDone
      () => {
        clearTimeout(timeoutId)
        const parsed = parsePathPlan(streamingContent.value)
        if (parsed) {
          applyParsedStages(parsed)
          generationProgress.value = '路径生成完成！'
        } else {
          generationProgress.value = '解析失败，使用本地生成…'
          generateFallbackPath(profileData)
        }
        generationStatus.value = 'done'
      },
      // onError
      (err: Error) => {
        clearTimeout(timeoutId)
        console.warn('[GLM 路径生成失败，降级到本地]', err.message)
        generateFallbackPath(profileData)
        generationStatus.value = 'done'
      },
    )
  }

  function regeneratePath(changeDescription?: string) {
    // 取消上一次未完成的生成，避免竞态
    cancelGeneration()

    const profileStore = useProfileStore()
    const profileData = getFilteredProfile(profileStore.profileData)

    // 保存旧路径用于 diff
    previousStages.value = JSON.parse(JSON.stringify(stages.value))

    generationStatus.value = 'generating'
    streamingContent.value = ''
    generationProgress.value = '画像已更新，正在调整路径…'
    generationError.value = ''

    // 设置超时，防止 API 卡住
    const timeoutId = setTimeout(() => {
      console.warn('[Path] API 调用超时，触发本地 fallback')
      cancelGeneration()
      generateFallbackPath(profileData)
      generationStatus.value = 'done'
      generationProgress.value = '路径已根据画像变更调整！'
    }, GENERATION_TIMEOUT_MS)

    const desc = changeDescription || '画像数据有更新'
    const messages = buildPathRegenerationMessages(
      profileData,
      previousStages.value.map(s => ({
        title: s.title,
        suggestedDays: s.suggestedDays,
        reason: s.reason,
        resources: s.resources.map(r => ({ type: r.type, name: r.name })),
      })),
      desc,
    )

    abortController = chatGLM(
      messages,
      (text: string) => {
        streamingContent.value += text
        updateGenerationProgress(streamingContent.value)
      },
      () => {
        clearTimeout(timeoutId)
        const parsed = parsePathPlan(streamingContent.value)
        if (parsed) {
          applyParsedStages(parsed)
          computePathDiff()
        } else {
          generateFallbackPath(profileData)
        }
        generationStatus.value = 'done'
        generationProgress.value = '路径已根据画像变更调整！'
      },
      (err: Error) => {
        clearTimeout(timeoutId)
        console.warn('[GLM 路径重生成失败，降级到本地]', err.message)
        generateFallbackPath(profileData)
        generationStatus.value = 'done'
      },
    )
  }

  function cancelGeneration() {
    abortController?.abort()
    abortController = null
    generationStatus.value = 'idle'
    generationProgress.value = ''
    // 同时清除画像更新定时器，防止取消后又自动触发生成
    if (profileUpdateTimer) {
      clearTimeout(profileUpdateTimer)
      profileUpdateTimer = null
    }
  }

  /* ===== 进度检测 ===== */

  function updateGenerationProgress(content: string) {
    if (content.includes('stages')) generationProgress.value = '正在规划学习阶段…'
    if (content.includes('resources')) generationProgress.value = '正在匹配学习资源…'
    if (content.includes('learningTips')) generationProgress.value = '正在生成学习建议…'
    if (content.includes('path-plan')) generationProgress.value = '正在输出路径方案…'
  }

  /* ===== 应用解析结果 ===== */

  function applyParsedStages(parsed: { summary?: string; stages: any[] }) {
    // 归档当前路径（如果有的话）
    if (stages.value.length > 0) {
      archiveCurrentPath()
    }

    pathSummary.value = parsed.summary || ''

    const validTypes = Object.keys(RESOURCE_TYPE_MAP) as ResourceType[]
    const profileStore = useProfileStore()
    // 优先使用当前科目，其次用专业
    const subject = profileStore.profileData.currentSubject || profileStore.profileData.major || '计算机'
    const major = subject
    const weakPoints = filterRelevantWeakPoints(
      profileStore.profileData.weak_points || [],
      subject,
    )

    // 资源名称生成辅助函数
    function generateResourceName(
      stageTitle: string,
      resourceType: ResourceType,
      index: number,
      major: string,
      weakPoints: string[]
    ): string {
      // 从阶段标题提取主题
      const topic = stageTitle.replace(/基础|进阶|综合|专项|突破|概念|应用|实战|复习/g, '').trim() || weakPoints[0] || major
      
      // 资源类型对应的后缀
      const typeSuffixes: Record<string, string[]> = {
        'document': ['详解', '原理', '指南', '教程', '笔记'],
        'video': ['视频讲解', '动画演示', '操作演示', '案例分析', '教学视频'],
        'exercise': ['练习题', '测试题', '实战练习', '综合测试', '专项练习'],
        'code': ['代码实战', '编程练习', '代码示例', '项目实战', '代码模板'],
        'mindmap': ['思维导图', '知识图谱', '概念导图', '知识体系', '学习路线图'],
        'extension': ['拓展阅读', '参考资料', '进阶资料', '相关文献', '延伸学习'],
      }
      
      const suffixes = typeSuffixes[resourceType] || typeSuffixes['document']
      const suffix = suffixes[index % suffixes.length]
      
      return `${topic}${suffix}`
    }

    stages.value = parsed.stages.map((s, i) => {
      const stageTitle = s.title || `阶段 ${i + 1}`
      
      const resources: PathResource[] = (s.resources || []).map((r: any, ri: number) => {
        // 'extension' 归一化为 'document'：没有 extension 类型的 Agent 生成器，
        // allocator 按类型过滤会导致 extension 小节永远匹配不到资源，文档也不会出现在工作台
        const rawType = validTypes.includes(r.type) ? r.type : 'document'
        const resourceType = rawType === 'extension' ? 'document' : rawType
        
        // AI 可能返回 name 或 title 字段，优先使用 name
        let resourceName = r.name || r.title || ''
        
        // 检测模糊或无效的资源名称
        const vaguePatterns = ['练习题', '教程', '资料', '学习资料', '参考', '未命名', '资源', '资源名称', 'resource', 'name', 'title', '-']
        const isVague = resourceName.trim() === '' || 
                        vaguePatterns.some(v => resourceName.includes(v)) ||
                        resourceName.length < 3
        
        if (isVague) {
          resourceName = generateResourceName(stageTitle, resourceType as ResourceType, ri, major, weakPoints)
          console.log(`[Path] 资源名称为空或模糊，生成新名称: "${resourceName}" (原名称: "${r.name || r.title || ''}")`)
        }
        
        return {
          id: `res-${i}-${ri}`,
          type: resourceType,
          name: resourceName,
          status: 'pending' as const,
        }
      })

      // 如果资源列表为空，根据阶段标题生成默认资源
      if (resources.length === 0) {
        const defaultTypes: ResourceType[] = ['document', 'mindmap', 'exercise']
        defaultTypes.forEach((type, ri) => {
          resources.push({
            id: `res-${i}-${ri}`,
            type,
            name: generateResourceName(stageTitle, type, ri, major, weakPoints),
            status: 'pending',
          })
        })
      }

      const validReasonTypes = ['foundation', 'weakness', 'advanced'] as const
      const reasonType = validReasonTypes.includes(s.reasonType) ? s.reasonType : 'foundation'

      return {
        id: `stage-${i + 1}`,
        title: stageTitle,
        status: (i === 0 ? 'active' : 'pending') as PathStage['status'],
        suggestedDays: Math.max(1, Math.min(30, Number(s.suggestedDays) || 7)),
        progress: i === 0 ? 5 : 0,
        reason: s.reason || '',
        reasonType,
        learningTips: s.learningTips || '',
        resources,
      }
    })
  }

  /* ===== Diff 计算 ===== */

  function computePathDiff() {
    if (!previousStages.value.length) { pathDiff.value = null; return }

    const diff: PathDiff = {
      addedStages: [], removedStages: [], modifiedStages: [],
      addedResources: [], removedResources: [],
    }

    const oldMap = new Map(previousStages.value.map(s => [s.title, s]))
    const newMap = new Map(stages.value.map(s => [s.title, s]))

    for (const [title, stage] of newMap) {
      if (!oldMap.has(title)) diff.addedStages.push(stage)
    }
    for (const [title, stage] of oldMap) {
      if (!newMap.has(title)) diff.removedStages.push(stage)
    }
    for (const [title, newStage] of newMap) {
      const oldStage = oldMap.get(title)
      if (!oldStage) continue
      if (oldStage.suggestedDays !== newStage.suggestedDays || oldStage.reason !== newStage.reason) {
        diff.modifiedStages.push({ old: oldStage, new: newStage })
      }
      // Resource diff
      const oldRes = new Map(oldStage.resources.map(r => [r.name, r]))
      const newRes = new Map(newStage.resources.map(r => [r.name, r]))
      for (const [name, res] of newRes) {
        if (!oldRes.has(name)) diff.addedResources.push({ stageId: newStage.id, resource: res })
      }
      for (const [name, res] of oldRes) {
        if (!newRes.has(name)) diff.removedResources.push({ stageId: oldStage.id, resource: res })
      }
    }

    const hasChanges = diff.addedStages.length || diff.removedStages.length ||
      diff.modifiedStages.length || diff.addedResources.length || diff.removedResources.length

    pathDiff.value = hasChanges ? diff : null
  }

  function clearDiff() {
    pathDiff.value = null
    previousStages.value = []
  }

  /* ===== 本地降级生成 ===== */

  function generateFallbackPath(profileData: ProfileData) {
    const weak = profileData.weak_points || []
    const base = profileData.base_level || '中等'
    const goal = profileData.study_goal || '全面掌握'
    const rhythm = profileData.study_rhythm || '适中节奏'
    const preference = profileData.interest_preference || '代码实操'
    const major = profileData.major || '计算机科学'
    // 优先使用当前学习科目作为主题
    const subject = profileData.currentSubject || major

    const dayMultiplier = rhythm === '碎片化' ? 0.7 : rhythm === '深度沉浸' ? 1.4 : 1
    const baseDays = base === '入门' ? 14 : base === '基础' ? 10 : base === '进阶' ? 5 : base === '精通' ? 3 : 7

    // 根据薄弱点确定学习主题，但确保与当前科目相关
    // 如果薄弱点与当前科目不匹配，使用当前科目作为主题
    const mainTopic = weak.length > 0 ? weak[0] : `${subject}核心知识`
    const fallbackStages: PathStageExtended[] = []

    // 第一阶段：基础概念（与当前科目相关）
    fallbackStages.push({
      id: 'stage-1',
      title: `${mainTopic}基础概念`,
      status: 'active',
      suggestedDays: Math.round(baseDays * dayMultiplier),
      progress: 5,
      reason: `基础水平为${base}，需要${base === '入门' || base === '基础' ? '重点夯实' : '快速回顾'}${mainTopic}基础知识`,
      reasonType: 'foundation',
      learningTips: base === '入门' ? '从基础概念开始，配合示例理解核心原理' : '快速过一遍基础，把时间留给薄弱点',
      resources: buildFallbackResources(mainTopic, preference, 0, subject),
    })

    // 第二阶段：薄弱点突破（如果有薄弱点）
    if (weak.length > 0) {
      const weakTopics = weak.slice(0, 3).join('、')
      fallbackStages.push({
        id: 'stage-2',
        title: `${weakTopics}专项突破`,
        status: 'pending',
        suggestedDays: Math.round((goal === '考试通关' ? 7 : 10) * dayMultiplier),
        progress: 0,
        reason: `薄弱知识点：${weak.join('、')}，需要专项突破`,
        reasonType: 'weakness',
        learningTips: '针对薄弱点多做练习，遇到不理解的概念及时回顾基础',
        resources: buildFallbackResources(weak[0], preference, 1, subject),
      })
    }

    // 第三阶段：进阶应用（根据学习目标）
    const hasAdvanced = goal === '全面掌握' || goal === '竞赛提升' || goal === '项目实战'
    if (hasAdvanced) {
      fallbackStages.push({
        id: `stage-${fallbackStages.length + 1}`,
        title: goal === '竞赛提升' ? `${mainTopic}竞赛进阶` : `${mainTopic}高级应用`,
        status: 'pending',
        suggestedDays: Math.round(12 * dayMultiplier),
        progress: 0,
        reason: `学习目标为${goal}，需要进阶提升`,
        reasonType: 'advanced',
        learningTips: goal === '竞赛提升' ? '多刷题，掌握常见解题技巧' : '结合项目实战，在应用中巩固知识',
        resources: buildFallbackResources(`${mainTopic}进阶`, preference, 2, subject),
      })
    }

    // 第四阶段：综合复习
    fallbackStages.push({
      id: `stage-${fallbackStages.length + 1}`,
      title: `${mainTopic}综合复习与实战`,
      status: 'pending',
      suggestedDays: Math.round(5 * dayMultiplier),
      progress: 0,
      reason: '最后阶段进行综合复习，查漏补缺',
      reasonType: 'foundation',
      learningTips: '回顾所有知识点，做综合练习题检验掌握程度',
      resources: buildFallbackResources(`${mainTopic}综合`, preference, 3, subject),
    })

    stages.value = fallbackStages
    pathSummary.value = `基于${base}基础的${subject}学习路径${weak.length ? '，重点突破' + weak.join('、') : ''}（${goal === '考试通关' ? '应试' : '全面'}路线）`
  }

  function buildFallbackResources(topic: string, preference: string, stageIndex: number, major: string): PathResource[] {
    // 根据专业和主题生成相关资源名称
    // 专业相关的资源模板
    const majorTemplates: Record<string, Record<string, string[]>> = {
      '英语': {
        'document': ['英语语法详解', '核心词汇手册', '阅读理解技巧', '写作范文精选', '翻译技巧指南'],
        'video': ['语法讲解视频', '听力训练材料', '口语示范视频', '阅读解析视频', '写作指导视频'],
        'exercise': ['语法练习题', '词汇测试题', '阅读理解练习', '翻译实战练习', '写作模拟题'],
        'code': ['词汇记忆工具', '语法练习程序', '阅读速度训练', '听力练习工具', '写作批改工具'],
        'mindmap': ['语法体系导图', '词汇分类导图', '时态关系导图', '句型结构导图', '写作框架导图'],
        'extension': ['英文名著阅读', 'BBC学习资料', 'TED演讲素材', '英文新闻阅读', '拓展学习材料'],
      },
      '化学': {
        'document': ['化学原理详解', '化学反应机制', '化学键理论', '分子结构分析', '化学实验指南'],
        'video': ['化学反应动画', '实验操作演示', '分子结构视频', '化学原理讲解', '实验安全教程'],
        'exercise': ['化学计算练习', '反应方程练习', '结构分析练习', '实验设计练习', '化学综合测试'],
        'code': ['化学模拟代码', '分子建模代码', '数据处理代码', '实验分析代码', '化学计算工具'],
        'mindmap': ['化学知识体系', '元素周期脑图', '反应类型导图', '有机化学导图', '无机化学导图'],
        'extension': ['化学文献阅读', '前沿研究资料', '化学史资料', '应用案例集', '拓展学习材料'],
      },
      '有机化学': {
        'document': ['有机化学基础', '官能团性质', '有机反应机理', '有机合成方法', '有机物命名规则'],
        'video': ['有机反应动画', '合成路线演示', '官能团视频', '有机实验操作', '有机结构讲解'],
        'exercise': ['有机命名练习', '反应预测练习', '合成设计练习', '结构推断练习', '有机综合测试'],
        'code': ['有机分子建模', '反应模拟代码', '结构分析工具', '合成路线规划', '有机数据处理'],
        'mindmap': ['有机化学体系', '官能团导图', '反应类型导图', '合成路线导图', '有机物分类导图'],
        'extension': ['有机前沿研究', '有机合成文献', '药物化学资料', '材料化学案例', '有机拓展学习'],
      },
      '计算机': {
        'document': ['编程基础详解', '算法原理深入', '数据结构指南', '核心知识点', '学习笔记'],
        'video': ['算法动画演示', '编程实战视频', '数据结构讲解', '案例解析', '教学视频'],
        'exercise': ['编程基础练习', '算法进阶练习', '数据结构实战', '模拟测试', '综合练习'],
        'code': ['代码实战', '编程练习', '代码示例', '项目实战', '代码模板'],
        'mindmap': ['知识体系脑图', '算法思维导图', '数据结构图谱', '概念关系图', '学习路线图'],
        'extension': ['拓展阅读', '技术博客', '进阶资料', '开源项目', '延伸学习'],
      },
      '数学': {
        'document': ['数学原理详解', '定理证明分析', '公式推导指南', '数学思想方法', '解题技巧'],
        'video': ['数学动画演示', '定理证明视频', '解题思路讲解', '数学应用案例', '教学视频'],
        'exercise': ['基础计算练习', '证明题练习', '应用题练习', '综合测试', '竞赛题目'],
        'code': ['数学计算代码', '数值模拟代码', '绘图代码', '数据分析代码', '数学工具'],
        'mindmap': ['数学知识体系', '定理关系导图', '公式推导导图', '数学思想导图', '解题方法导图'],
        'extension': ['数学史资料', '前沿研究', '数学应用案例', '竞赛资料', '拓展学习'],
      },
      '物理': {
        'document': ['物理原理详解', '定律推导分析', '物理模型指南', '实验原理', '物理思想'],
        'video': ['物理现象动画', '实验演示视频', '定律讲解视频', '物理应用案例', '教学视频'],
        'exercise': ['物理计算练习', '定律应用练习', '实验设计练习', '综合测试', '物理竞赛题'],
        'code': ['物理模拟代码', '数值计算代码', '实验分析代码', '物理建模代码', '物理工具'],
        'mindmap': ['物理知识体系', '定律关系导图', '物理模型导图', '实验方法导图', '物理思想导图'],
        'extension': ['物理史资料', '前沿研究', '物理应用案例', '科技发展', '拓展学习'],
      },
      '生物': {
        'document': ['生物学原理', '细胞结构详解', '遗传机制分析', '生态学指南', '分子生物学'],
        'video': ['生物过程动画', '实验操作视频', '结构讲解视频', '生物应用案例', '教学视频'],
        'exercise': ['生物概念练习', '遗传计算练习', '实验分析练习', '综合测试', '生物竞赛题'],
        'code': ['生物模拟代码', '序列分析代码', '实验数据处理', '生物建模代码', '生物工具'],
        'mindmap': ['生物知识体系', '细胞结构导图', '遗传机制导图', '生态系统导图', '分子生物导图'],
        'extension': ['生物前沿研究', '生物技术应用', '医学资料', '生态保护案例', '拓展学习'],
      },
      '历史': {
        'document': ['历史事件详解', '时代背景分析', '历史人物传记', '历史文献解读', '史学理论'],
        'video': ['历史纪录片', '事件动画演示', '人物讲解视频', '历史地图讲解', '教学视频'],
        'exercise': ['历史事件排序', '人物匹配练习', '年代计算练习', '综合测试', '历史分析题'],
        'code': ['历史数据分析', '时间线代码', '历史地图工具', '文献检索工具', '历史可视化'],
        'mindmap': ['历史知识体系', '朝代更迭导图', '事件关系导图', '人物关系导图', '历史脉络导图'],
        'extension': ['历史文献集', '考古发现', '历史研究前沿', '历史应用案例', '拓展学习'],
      },
      '经济': {
        'document': ['经济学原理', '市场分析指南', '经济政策解读', '财务管理', '投资理论'],
        'video': ['经济现象动画', '市场分析视频', '政策讲解视频', '案例分析', '教学视频'],
        'exercise': ['经济计算练习', '案例分析练习', '政策分析练习', '综合测试', '经济应用题'],
        'code': ['经济数据分析', '市场预测代码', '财务计算代码', '投资分析工具', '经济可视化'],
        'mindmap': ['经济学体系导图', '市场机制导图', '政策影响导图', '财务知识导图', '投资理论导图'],
        'extension': ['经济前沿研究', '市场报告', '政策文件', '经济案例集', '拓展学习'],
      },
    }

    // 根据偏好确定主要资源类型
    const preferredTypes: Record<string, string[]> = {
      '代码实操': ['code', 'exercise', 'document'],
      '视频教程': ['video', 'document', 'exercise'],
      '思维导图': ['mindmap', 'document', 'extension'],
      '理论阅读': ['document', 'extension', 'mindmap'],
    }

    const types = preferredTypes[preference] || ['document', 'video', 'exercise']
    const resources: PathResource[] = []

    // 查找匹配的专业模板
    let matchedTemplates: Record<string, string[]> | undefined = undefined
    for (const [key, templates] of Object.entries(majorTemplates)) {
      if (major.includes(key) || topic.includes(key)) {
        matchedTemplates = templates
        break
      }
    }

    // 如果没有匹配的专业模板，使用通用模板
    const defaultTemplates: Record<string, string[]> = {
      'document': ['概念详解', '原理深入', '入门指南', '核心知识点', '学习笔记'],
      'video': ['动画演示', '视频讲解', '实战演示', '案例解析', '教学视频'],
      'exercise': ['基础练习', '进阶练习', '实战练习', '模拟测试', '综合练习'],
      'code': ['实战代码', '编程练习', '代码示例', '项目实战', '代码模板'],
      'mindmap': ['知识体系脑图', '思维导图', '知识图谱', '概念关系图', '学习路线图'],
      'extension': ['拓展阅读', '参考资料', '进阶资料', '相关文献', '延伸学习'],
    }

    const templatesToUse = matchedTemplates || defaultTemplates

    // 为每个类型生成 1-2 个资源（与主题相关）
    types.forEach((type, typeIndex) => {
      const typeTemplates = templatesToUse[type] || defaultTemplates[type]
      const nameIndex = (stageIndex + typeIndex) % typeTemplates.length
      resources.push({
        id: `res-${stageIndex}-${typeIndex}`,
        type: type as any,
        name: `${topic}${typeTemplates[nameIndex]}`,
        status: 'pending'
      })
    })

    // 添加一个额外资源（与主题相关）
    const extraTypes = ['mindmap', 'extension', 'code']
    const extraType = extraTypes[Math.floor(Math.random() * extraTypes.length)]
    const extraTemplates = templatesToUse[extraType] || defaultTemplates[extraType]
    const extraName = extraTemplates[Math.floor(Math.random() * extraTemplates.length)]
    resources.push({
      id: `res-${stageIndex}-${types.length}`,
      type: extraType as any,
      name: `${topic}${extraName}`,
      status: 'pending'
    })

    return resources
  }

  /* ===== 编辑操作 ===== */

  function startEditing() {
    isEditing.value = true
    editSnapshot.value = JSON.parse(JSON.stringify(stages.value))
  }

  function cancelEditing() {
    isEditing.value = false
    stages.value = editSnapshot.value
    editSnapshot.value = []
  }

  function saveEditing() {
    isEditing.value = false
    editSnapshot.value = []
  }

  function reorderStages(fromIndex: number, toIndex: number) {
    const [moved] = stages.value.splice(fromIndex, 1)
    stages.value.splice(toIndex, 0, moved)
  }

  function addStage(title: string, suggestedDays: number) {
    const id = `stage-${Date.now()}`
    stages.value.push({
      id,
      title,
      status: 'pending',
      suggestedDays,
      progress: 0,
      reason: '用户手动添加',
      reasonType: 'foundation',
      learningTips: '',
      resources: [],
    })
  }

  function removeStage(stageId: string) {
    const idx = stages.value.findIndex(s => s.id === stageId)
    if (idx !== -1) stages.value.splice(idx, 1)
  }

  function updateSuggestedDays(stageId: string, days: number) {
    const stage = stages.value.find(s => s.id === stageId)
    if (stage) stage.suggestedDays = Math.max(1, Math.min(30, days))
  }

  function addResource(stageId: string, type: ResourceType, name: string) {
    const stage = stages.value.find(s => s.id === stageId)
    if (!stage) return
    stage.resources.push({
      id: `res-${Date.now()}`,
      type,
      name,
      status: 'pending',
    })
  }

  function removeResource(stageId: string, resourceId: string) {
    const stage = stages.value.find(s => s.id === stageId)
    if (!stage) return
    const idx = stage.resources.findIndex(r => r.id === resourceId)
    if (idx !== -1) stage.resources.splice(idx, 1)
  }

  function toggleResource(stageId: string, resourceId: string) {
    const stage = stages.value.find(s => s.id === stageId)
    if (!stage) return
    const res = stage.resources.find(r => r.id === resourceId)
    if (!res) return
    const order: PathResource['status'][] = ['pending', 'active', 'completed']
    const next = order[(order.indexOf(res.status) + 1) % order.length]

    // 记录资源完成前的状态
    const wasResourceCompleted = res.status === 'completed'
    res.status = next

    // 更新阶段进度
    if (stage.resources.length) {
      const completed = stage.resources.filter(r => r.status === 'completed').length
      stage.progress = Math.round((completed / stage.resources.length) * 100)
    }

    // ===== 画像增量更新：资源完成时触发 =====
    if (next === 'completed' && !wasResourceCompleted) {
      const profileStore = useProfileStore()
      const event: LearningEvent = {
        type: 'resource_complete',
        timestamp: new Date().toISOString(),
        sourceId: resourceId,
        description: `完成学习资源：${res.name}`,
        knowledgePoints: extractKnowledgePoints(stage.title),
        resourceType: res.type,
      }
      profileStore.applyLearningEvent(event)
    }

    // ===== 画像增量更新：阶段完成时触发 =====
    if (stage.progress === 100 && stage.status !== 'completed') {
      stage.status = 'completed'
      // 激活下一个阶段
      const stageIdx = stages.value.findIndex(s => s.id === stageId)
      const nextStage = stages.value[stageIdx + 1]
      if (nextStage && nextStage.status === 'pending') {
        nextStage.status = 'active'
      }

      const profileStore = useProfileStore()
      const event: LearningEvent = {
        type: 'stage_complete',
        timestamp: new Date().toISOString(),
        sourceId: stageId,
        description: `完成学习阶段：${stage.title}`,
        knowledgePoints: extractKnowledgePoints(stage.title),
      }
      profileStore.applyLearningEvent(event)
    }
  }

  /** 完成资源学习（通过学习弹窗确认后调用） */
  function completeResource(stageId: string, resourceId: string) {
    const stage = stages.value.find(s => s.id === stageId)
    if (!stage) return
    const res = stage.resources.find(r => r.id === resourceId)
    if (!res) return

    // 如果已经是完成状态，不做处理
    if (res.status === 'completed') return

    // 记录资源完成前的状态
    const wasResourceCompleted = res.status === 'completed'
    res.status = 'completed'

    // 更新阶段进度
    if (stage.resources.length) {
      const completed = stage.resources.filter(r => r.status === 'completed').length
      stage.progress = Math.round((completed / stage.resources.length) * 100)
    }

    // ===== 画像增量更新：资源完成时触发 =====
    if (!wasResourceCompleted) {
      const profileStore = useProfileStore()
      const event: LearningEvent = {
        type: 'resource_complete',
        timestamp: new Date().toISOString(),
        sourceId: resourceId,
        description: `完成学习资源：${res.name}`,
        knowledgePoints: extractKnowledgePoints(stage.title),
        resourceType: res.type,
      }
      profileStore.applyLearningEvent(event)
    }

    // ===== 画像增量更新：阶段完成时触发 =====
    if (stage.progress === 100 && stage.status !== 'completed') {
      stage.status = 'completed'
      // 激活下一个阶段
      const stageIdx = stages.value.findIndex(s => s.id === stageId)
      const nextStage = stages.value[stageIdx + 1]
      if (nextStage && nextStage.status === 'pending') {
        nextStage.status = 'active'
      }

      const profileStore = useProfileStore()
      const event: LearningEvent = {
        type: 'stage_complete',
        timestamp: new Date().toISOString(),
        sourceId: stageId,
        description: `完成学习阶段：${stage.title}`,
        knowledgePoints: extractKnowledgePoints(stage.title),
      }
      profileStore.applyLearningEvent(event)
    }
  }

  /** 从阶段标题提取知识点关键词 */
  function extractKnowledgePoints(title: string): string[] {
    const keywords = ['数组', '链表', '栈', '队列', '树', '二叉树', '图', '哈希', '排序',
      '查找', '递归', '动态规划', '贪心', '回溯', '分治', '堆', '字符串', '基础', '进阶', '综合']
    return keywords.filter(kw => title.includes(kw))
  }

  /* ===== 画像联动（自动更新路径） ===== */

  function startProfileWatch() {
    if (profileWatchStop) return

    const profileStore = useProfileStore()
    let oldProfileJson = JSON.stringify(profileStore.profileData)

    profileWatchStop = watch(
      () => profileStore.profileData,
      () => {
        // 清除之前的定时器（防抖）
        if (profileUpdateTimer) {
          clearTimeout(profileUpdateTimer)
          profileUpdateTimer = null
        }

        // 设置新的定时器，延迟更新
        if (hasPath.value) {
          profileUpdateTimer = setTimeout(() => {
            // 延迟到此处才做昂贵对比，避免主线程阻塞
            const currentJson = JSON.stringify(profileStore.profileData)
            if (currentJson === oldProfileJson) {
              profileUpdateTimer = null
              return
            }
            oldProfileJson = currentJson
            try {
              const desc = buildChangeDescription(
                getFilteredProfile(JSON.parse(currentJson) as ProfileData),
                getFilteredProfile(profileStore.profileData),
              )
              regeneratePath(desc)
            } catch (e) {
              console.warn('[Path] profileWatch 回调异常', e)
            }
            profileUpdateTimer = null
          }, PROFILE_UPDATE_DELAY)
        }
      },
      { deep: true },
    )
  }

  function stopProfileWatch() {
    if (profileWatchStop) {
      profileWatchStop()
      profileWatchStop = null
    }
    if (profileUpdateTimer) {
      clearTimeout(profileUpdateTimer)
      profileUpdateTimer = null
    }
  }

  /* ===== 智能体写入路径 ===== */

  function setAgentGeneratedStages(data: { summary?: string; stages: any[] }) {
    applyParsedStages(data)
    // 将 PathResource ID 与资源库中已生成的资源建立关联
    linkResourcesToGenerated()
    generationStatus.value = 'done'
    generationProgress.value = '路径由智能体生成完成'
  }

  /** 将路径中的 PathResource 与资源库中已生成的 ResourceItem 建立关联 */
  function linkResourcesToGenerated() {
    const resourceStore = useResourceStore()
    const profileStore = useProfileStore()
    // 调 allocator 深模块：一次性分配，跨小节 exclude 累积，避免重复
    const { assignments, gaps } = allocate(stages.value, resourceStore.resources, profileStore.profileData)
    const changed = applyAssignments(stages.value, assignments)
    if (changed) saveStages()
    if (gaps.length > 0) {
      console.log(`[Path] 资源分配缺口：${gaps.length} 项需生成`, gaps)
    }
  }

  /* ===== 多路径归档 ===== */

  function loadArchives() {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      const stored = localStorage.getItem(`${PATH_ARCHIVES_KEY}_${userId}`)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) pathArchives.value = parsed
      }
    } catch (e) {
      console.warn('[Path] 加载归档失败', e)
    }
  }

  let saveArchivesTimer: ReturnType<typeof setTimeout> | null = null
  function saveArchives() {
    // 异步执行 localStorage 写入，避免阻塞主线程（Trae WebView 性能敏感）
    if (saveArchivesTimer) clearTimeout(saveArchivesTimer)
    saveArchivesTimer = setTimeout(() => {
      saveArchivesTimer = null
      try {
        const authStore = useAuthStore()
        const userId = authStore.user?.id || 'guest'
        localStorage.setItem(`${PATH_ARCHIVES_KEY}_${userId}`, JSON.stringify(pathArchives.value))
      } catch (e) {
        console.warn('[Path] 保存归档失败', e)
      }
    }, 0)
  }

  function archiveCurrentPath() {
    if (stages.value.length === 0) return

    const profileStore = useProfileStore()
    const archiveSubject = profileStore.profileData.currentSubject || profileStore.profileData.major || ''
    const archiveWeakPoints = filterRelevantWeakPoints(
      profileStore.profileData.weak_points || [],
      archiveSubject,
    )
    const topic = archiveSubject
      || archiveWeakPoints[0]
      || ''
    const stageCount = stages.value.length
    const baseName = pathSummary.value || stages.value[0]?.title || '学习路径'
    const name = topic ? `${topic} - ${baseName} (${stageCount}阶段)` : `${baseName} (${stageCount}阶段)`
    // 轻量快照：只保留画像关键字段，避免深拷贝整个 profileData 导致卡死
    const lightProfileSnapshot = {
      major: profileStore.profileData.major,
      grade: profileStore.profileData.grade,
      currentSubject: profileStore.profileData.currentSubject,
      base_level: profileStore.profileData.base_level,
      weak_points: archiveWeakPoints,
      study_goal: profileStore.profileData.study_goal,
      cognitive_style: profileStore.profileData.cognitive_style,
      study_rhythm: profileStore.profileData.study_rhythm,
      interest_preference: profileStore.profileData.interest_preference,
      knowledge_mastery: profileStore.profileData.knowledge_mastery,
      exercise_completion: profileStore.profileData.exercise_completion,
      learning_engagement: profileStore.profileData.learning_engagement,
    }

    const archive: PathArchiveItem = {
      id: `archive-${Date.now()}`,
      name,
      // 浅拷贝：复制 stage 和 resource 对象，避免 JSON.parse(JSON.stringify) 深拷贝阻塞主线程
      // 安全性：resetPath 用 stages.value = [] 替换数组（不 mutate 旧对象），所以归档引用不会被修改
      stages: stages.value.map(s => ({
        ...s,
        resources: (s.resources || []).map(r => ({ ...r })),
      })),
      profileSnapshot: lightProfileSnapshot as any,
      createdAt: new Date().toISOString(),
    }

    pathArchives.value.unshift(archive)
    if (pathArchives.value.length > 20) {
      pathArchives.value = pathArchives.value.slice(0, 20)
    }
    saveArchives()
  }

  function switchToPath(archiveId: string) {
    const archive = pathArchives.value.find(a => a.id === archiveId)
    if (!archive) return
    // 恢复归档路径（不自动归档当前路径，避免反复归档产生重复）
    stages.value = JSON.parse(JSON.stringify(archive.stages))
    pathSummary.value = archive.name
    // 从归档列表中移除（已激活）
    pathArchives.value = pathArchives.value.filter(a => a.id !== archiveId)
    saveArchives()
    saveStages()
  }

  function deleteArchive(archiveId: string) {
    pathArchives.value = pathArchives.value.filter(a => a.id !== archiveId)
    saveArchives()
  }

  // 初始化时加载归档
  loadArchives()

  /* ===== 重置 ===== */

  function resetPath() {
    cancelGeneration()
    stages.value = []
    generationStatus.value = 'idle'
    streamingContent.value = ''
    generationProgress.value = ''
    generationError.value = ''
    pathSummary.value = ''
    pathDiff.value = null
    previousStages.value = []
    isEditing.value = false
    editSnapshot.value = []
    // 标记为"用户已清空"，阻止 App.vue 的自动生成逻辑
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      localStorage.setItem(pathClearedKey(userId), '1')
    } catch { /* ignore */ }
  }

  function isPathCleared(): boolean {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      return localStorage.getItem(pathClearedKey(userId)) === '1'
    } catch { return false }
  }

  /** 切换科目时调用：按当前 subject 重新加载路径
   *  修复跨科目污染：不清空会导致英语会话显示数据结构路径
   */
  function reloadForCurrentSubject() {
    const loaded = loadStages()
    stages.value = loaded
    if (loaded.length > 0) {
      // 旧数据兼容：补分配 resourceRef
      try { linkResourcesToGenerated() } catch (e) {
        console.warn('[Path] reload 后资源分配失败', e)
      }
    }
    // 重置生成状态
    generationStatus.value = loaded.length > 0 ? 'done' : 'idle'
    generationProgress.value = loaded.length > 0 ? '路径已加载' : ''
    pathSummary.value = ''
    pathDiff.value = null
  }

  return {
    stages,
    generationStatus,
    streamingContent,
    generationProgress,
    generationError,
    pathSummary,
    isEditing,
    editingStageId,
    pathDiff,
    hasPath,
    totalProgress,
    totalDays,
    activeStageIndex,
    generatePath,
    regeneratePath,
    cancelGeneration,
    clearDiff,
    startEditing,
    cancelEditing,
    saveEditing,
    reorderStages,
    addStage,
    removeStage,
    updateSuggestedDays,
    addResource,
    removeResource,
    toggleResource,
    completeResource,
    saveStages,
    startProfileWatch,
    stopProfileWatch,
    setAgentGeneratedStages,
    linkResourcesToGenerated,
    resetPath,
    reloadForCurrentSubject,
    isPathCleared,
    pathArchives,
    archiveCurrentPath,
    switchToPath,
    deleteArchive,
  }
})
