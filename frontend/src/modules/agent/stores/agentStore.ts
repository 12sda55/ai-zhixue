import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { AgentInfo, ResourceItem } from '../../../shared/types'
import { AGENT_LIST } from '../../../shared/utils/constants'
import { chatGLM } from '../../../shared/api/glmApi'
import request from '../../../shared/utils/request'
import {
  buildDocAgentMessages, buildMindmapAgentMessages, buildQuizAgentMessages,
  buildCodeAgentMessages, buildVideoAgentMessages, buildPathAgentMessages,
  buildKnowledgeGraphAgentMessages,
} from '../prompts/agentPrompts'
import { buildReviewerMessages, parseReviewReport } from '../prompts/reviewerPrompts'
import { useProfileStore } from '../../profile/stores/profileStore'
import type { ProfileChangeInfo } from '../../profile/stores/profileStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { usePathStore } from '../../path/stores/pathStore'
import { allocate } from '../../resource/services/allocator'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'
import {
  extractCodeBlock,
  parseResourceList,
} from '../../../shared/utils/llmParsing'
import {
  parseMindmapData,
  getFallbackMindmap,
  parseKnowledgeGraph,
  getFallbackKnowledgeGraph,
  parseCodeExample,
  parseAssessQuestions,
  inferSubject,
} from '../services/agentParsing'

function createInitialAgents(): AgentInfo[] {
  return AGENT_LIST.map(a => ({
    id: a.id,
    name: a.name,
    role: a.role,
    color: a.color,
    icon: a.icon,
    status: 'idle' as const,
    progress: 0,
    log: [] as string[],
    duration: '',
  }))
}

export const useAgentStore = defineStore('agent', () => {
  const agents = ref<AgentInfo[]>(createInitialAgents())
  const logs = ref<string[]>(['[系统] 就绪，等待任务启动'])
  const workflowStage = ref(0)
  const isRunning = ref(false)
  const errorDetails = ref<{ agentId: string; agentName: string; error: string; suggestion: string }[]>([])
  const estimatedRemainingTime = ref(0) // 预估剩余时间（秒）
  const totalEstimatedTime = ref(0) // 总预估时间（秒）
  const taskStartTime = ref(0) // 任务开始时间戳
  let abortControllers: AbortController[] = []

  // Agent 预估时间（基于历史数据，单位：秒）
  const agentEstimateTimes: Record<number, number> = {
    1: 25, // 文档 Agent
    2: 20, // 导图 Agent
    3: 30, // 题库 Agent
    4: 35, // 代码 Agent
    5: 240, // 视频 Agent（4分钟，异步不计入阻塞时间）
    6: 25, // 路径 Agent
    7: 20, // 知识图谱 Agent
    8: 15, // 审查 Agent
  }

  /* ===== 延迟恢复：刷新后如果有已保存的画像+资源，智能体自动标记就绪 ===== */
  function restoreFromSavedData() {
    try {
      const profileStore = useProfileStore()
      const resourceStore = useResourceStore()
      const hasRunBefore = profileStore.profileData.dimensions?.some(d => d.value > 0)
        && resourceStore.resources.length > 0

      if (hasRunBefore) {
        agents.value = AGENT_LIST.map(a => ({
          ...a,
          status: 'completed' as const,
          progress: 100,
          log: ['已就绪（基于已保存画像）'],
          duration: '已恢复',
        }))
        workflowStage.value = 4
        logs.value = ['[系统] 画像与资源已从本地恢复，智能体就绪']
      }
    } catch {
      // Pinia 尚未就绪，跳过
    }
  }

  // 下一个微任务中恢复（确保其他 Pinia store 已初始化）
  Promise.resolve().then(restoreFromSavedData)

  const profileReady = computed(() => {
    const profileStore = useProfileStore()
    // 画像只要有任何维度数据就视为就绪（不再要求 phase === 'stable'）
    const dims = profileStore.profileData.dimensions || []
    return dims.some(d => d.value > 0) || profileStore.profileData.phase !== 'initial'
  })

  function addLog(text: string) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    logs.value.push(`[${time}] ${text}`)
  }

  function clearLogs() {
    logs.value = ['[系统] 日志已清除']
  }

  function resetAgents() {
    agents.value = createInitialAgents()
    workflowStage.value = 0
    isRunning.value = false
    errorDetails.value = []
    estimatedRemainingTime.value = 0
    totalEstimatedTime.value = 0
    taskStartTime.value = 0
    abortControllers = []
  }

  /** 根据错误信息生成修复建议 */
  function getErrorSuggestion(errorMsg: string): string {
    if (errorMsg.includes('401') || errorMsg.includes('Unauthorized') || errorMsg.includes('Not authenticated')) {
      return '请检查 API Key 配置是否正确，或重新登录获取有效 Token'
    }
    if (errorMsg.includes('429') || errorMsg.includes('Rate limit') || errorMsg.includes('Too many requests')) {
      return 'API 请求频率过高，请稍后再试或减少并发 Agent 数量'
    }
    if (errorMsg.includes('timeout') || errorMsg.includes('Timeout') || errorMsg.includes('ETIMEDOUT')) {
      return '网络连接超时，请检查网络或使用更稳定的网络环境'
    }
    if (errorMsg.includes('500') || errorMsg.includes('Internal Server Error')) {
      return '后端服务异常，请检查服务是否正常运行'
    }
    if (errorMsg.includes('network') || errorMsg.includes('Network') || errorMsg.includes('ECONNREFUSED')) {
      return '无法连接到后端服务，请确保 Backend (8000) 和 AI Tutor (8001) 已启动'
    }
    if (errorMsg.includes('empty') || errorMsg.includes('Empty response') || errorMsg.includes('无内容')) {
      return 'LLM 返回空内容，可能是 prompt 问题或模型暂时不可用，请稍后重试'
    }
    return '请检查网络连接和 API 配置，或查看日志获取更多信息'
  }

  /** 清空错误详情 */
  function clearErrors() {
    errorDetails.value = []
  }

  /** 格式化时间（秒 → 分钟秒） */
  function formatTime(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}秒`
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${mins}分${secs}秒`
  }

  /* ===== 通用 GLM 执行函数 ===== */

  function executeAgent(
    agentIndex: number,
    messages: { role: 'system' | 'user' | 'assistant'; content: string }[],
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const agent = agents.value[agentIndex]
      agent.status = 'running'
      agent.progress = 10
      agent.log = ['正在执行...']

      let rawContent = ''
      const startTime = Date.now()
      let lastProgressUpdate = 0
      const controller = chatGLM(
        messages,
        (text: string) => {
          rawContent += text
          // 节流：最多每 200ms 更新一次 progress，避免高频 re-render 导致闪屏
          const now = Date.now()
          if (now - lastProgressUpdate >= 200) {
            lastProgressUpdate = now
            agent.progress = Math.min(90, 10 + Math.min(rawContent.length / 20, 80))
            agent.log = ['正在执行...', `已生成 ${rawContent.length} 字`]
          }
        },
        () => {
          agent.status = 'completed'
          agent.progress = 100
          const dur = ((Date.now() - startTime) / 1000).toFixed(1)
          agent.duration = `${dur}s`
          agent.log = ['正在执行...', `完成 ✓ (${rawContent.length}字)`]
          resolve(rawContent)
        },
        (error: Error) => {
          agent.status = 'error'
          agent.progress = 0
          agent.duration = '0s'
          agent.log = ['执行失败', `错误: ${error.message}`]
          // 记录错误详情
          const suggestion = getErrorSuggestion(error.message)
          errorDetails.value.push({
            agentId: agent.id,
            agentName: agent.name,
            error: error.message,
            suggestion,
          })
          // reject 而非 resolve('')，让调用方能正确处理错误
          reject(new Error(`Agent ${agent.name} 执行失败: ${error.message}`))
        },
      )
      abortControllers.push(controller)
    })
  }

  /** 视频Agent专用执行函数：创建任务后立即返回，后台轮询不阻塞其他Agent */
  function executeVideoAgent(knowledgePoint: string, subject: string): Promise<ResourceItem | null> {
    return new Promise(async (resolve) => {
      const agent = agents.value[5] // 视频Agent index=5
      agent.status = 'running'
      agent.progress = 5
      agent.log = ['正在创建视频生成任务...']

      try {
        // 1. 创建视频生成任务
        const createRes = await request<{ status: string; task_id?: string; message?: string; video_url?: string }>({
          url: '/video/generate',
          method: 'POST',
          data: { knowledge_point: knowledgePoint, style: 'rigorous' }
        })

        if (!createRes.task_id) {
          agent.status = 'error'
          agent.log = ['创建任务失败', createRes.message || '未知错误']
          errorDetails.value.push({
            agentId: agent.id,
            agentName: agent.name,
            error: createRes.message || '创建视频任务失败',
            suggestion: '请确保 AI Tutor 服务 (8001) 正常运行',
          })
          resolve(null)
          return
        }

        const taskId = createRes.task_id

        // ★ 关键修复：如果后端直接返回 completed（缓存命中），直接完成，不启动轮询
        // 避免使用旧 task_id 轮询导致 404 风暴
        if (createRes.status === 'completed' && createRes.video_url) {
          agent.status = 'completed'
          agent.progress = 100
          agent.log = ['视频生成完成（缓存命中）', createRes.video_url]
          addLog(`✅ 视频命中缓存，直接返回: ${createRes.video_url}`)

          const cachedResource: ResourceItem = {
            id: `video-${taskId}`,
            title: `${knowledgePoint} 教学视频`,
            type: 'video',
            module: knowledgePoint,
            url: createRes.video_url,
            description: 'AI生成的教学动画视频（缓存命中）',
            createdAt: new Date().toISOString(),
            aiGenerated: true,
            difficulty: 'beginner',
            videoStatus: 'done',
            video_task_id: taskId,
          }
          resolve(cachedResource)
          return
        }

        agent.progress = 15
        agent.log = ['任务已创建，后台渲染中...', `task_id: ${taskId}`]
        addLog(`视频任务已创建: ${taskId}，后台渲染中（不阻塞其他Agent）`)

        // 2. 立即返回占位资源（视频状态 pending）
        const placeholderResource: ResourceItem = {
          id: `video-${taskId}`,
          title: `${knowledgePoint} 教学视频`,
          type: 'video',
          module: knowledgePoint,
          url: '', // 暂无URL，后台轮询完成后更新
          description: '视频正在后台生成中...',
          createdAt: new Date().toISOString(),
          aiGenerated: true,
          difficulty: 'beginner',
          videoStatus: 'pending',
          video_task_id: taskId,
        }

        // 3. 启动后台轮询（不阻塞 Promise，直接 resolve）
        pollVideoTaskInBackground(taskId, knowledgePoint, agent, subject)
        resolve(placeholderResource)

      } catch (e: any) {
        agent.status = 'error'
        agent.log = ['调用视频服务失败', e?.message || '网络错误']
        errorDetails.value.push({
          agentId: agent.id,
          agentName: agent.name,
          error: e?.message || '网络错误',
          suggestion: '无法连接到视频服务，请确保 AI Tutor (8001) 已启动',
        })
        resolve(null)
      }
    })
  }

  /** 后台轮询视频任务，完成后更新资源到 resourceStore */
  function pollVideoTaskInBackground(taskId: string, knowledgePoint: string, agent: any, subject: string) {
    const resourceStore = useResourceStore()
    let lastProgress = 15
    let pollFailureCount = 0
    const MAX_POLL_FAILURES = 15  // 最大轮询失败次数（每次2秒，约30秒后放弃）

    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await request<{
          status: string
          progress?: number
          message?: string
          video_url?: string
          error?: string
        }>({
          url: `/video/task/${taskId}`,
          method: 'GET'
        })

        pollFailureCount = 0  // 成功时重置失败计数

        // 更新进度
        if (statusRes.progress && statusRes.progress > lastProgress) {
          agent.progress = Math.min(95, statusRes.progress)
          lastProgress = statusRes.progress
        }

        // 更新日志
        if (statusRes.message) {
          const stageMap: Record<string, string> = {
            '正在生成讲解脚本': '讲解脚本生成中...',
            '正在生成TTS旁白': 'TTS语音合成中...',
            '正在渲染Manim视频': 'Manim动画渲染中...',
            '正在拼接视频和音频': '视频合成中...',
          }
          agent.log = ['后台渲染中...', stageMap[statusRes.message] || statusRes.message]
        }

        // 完成
        if ((statusRes.status === 'done' || statusRes.status === 'completed') && statusRes.video_url) {
          clearInterval(pollInterval)
          agent.status = 'completed'
          agent.progress = 100
          agent.log = ['视频生成完成 ✓', statusRes.video_url]
          addLog(`✅ 视频后台渲染完成: ${statusRes.video_url}`)

          // 更新资源（替换占位资源）
          const completedResource: ResourceItem = {
            id: `video-${taskId}`,
            title: `${knowledgePoint} 教学视频`,
            type: 'video',
            module: knowledgePoint,
            url: statusRes.video_url,
            description: 'AI生成的教学动画视频',
            createdAt: new Date().toISOString(),
            aiGenerated: true,
            difficulty: 'beginner',
            videoStatus: 'done',
            video_task_id: taskId,
          }
          resourceStore.addIncrementalResources([completedResource], subject)
          addLog(`✅ 视频已自动同步到资源中心`)

          // 在 pathStore 中找到对应的 PathResource，设置 resourceRef
          try {
            const pathStore = usePathStore()
            for (const stage of pathStore.stages) {
              if (!stage.resources) continue
              for (const pr of stage.resources) {
                if (pr.type === 'video' && !pr.resourceRef) {
                  // 通过名称核心词匹配视频 PathResource
                  const kpLower = knowledgePoint.toLowerCase()
                  const prName = pr.name.toLowerCase()
                  if (prName.includes(kpLower) || kpLower.includes(prName.replace(/视频|讲解|演示|动画/g, '').trim())) {
                    pr.resourceRef = `video-${taskId}`
                    pr.status = 'active'
                    pathStore.saveStages()
                    addLog(`✅ 路径中视频资源已关联: ${pr.name} → video-${taskId}`)
                  }
                }
              }
            }
          } catch (e) {
            console.warn('[Agent] 视频资源路径关联失败', e)
          }
        }

        // 失败
        if (statusRes.status === 'failed') {
          clearInterval(pollInterval)
          agent.status = 'error'
          agent.log = ['视频生成失败', statusRes.message || statusRes.error || '未知错误']
          addLog(`❌ 视频后台渲染失败: ${statusRes.message || statusRes.error}`)
          errorDetails.value.push({
            agentId: agent.id,
            agentName: agent.name,
            error: statusRes.message || statusRes.error || '视频生成失败',
            suggestion: 'Manim 渲染出错，请检查 AI Tutor 日志或点击重新生成',
          })

          // 更新资源状态为失败（避免卡片一直显示"后台渲染中"）
          const failedResource: ResourceItem = {
            id: `video-${taskId}`,
            title: `${knowledgePoint} 教学视频`,
            type: 'video',
            module: knowledgePoint,
            url: '',
            description: statusRes.message || statusRes.error || '视频生成失败',
            createdAt: new Date().toISOString(),
            aiGenerated: true,
            difficulty: 'beginner',
            videoStatus: 'failed',
            video_task_id: taskId,
          }
          resourceStore.addIncrementalResources([failedResource], subject)
          addLog(`⚠️ 视频状态已更新为失败`)
        }
      } catch {
        // 轮询错误累计失败次数，超过上限后放弃
        pollFailureCount++
        if (pollFailureCount >= MAX_POLL_FAILURES) {
          clearInterval(pollInterval)
          agent.status = 'error'
          agent.progress = 0
          agent.log = ['视频服务连接失败', 'AI Tutor 服务可能未运行']
          addLog(`❌ 视频轮询失败（连续 ${MAX_POLL_FAILURES} 次），已停止轮询`)
          errorDetails.value.push({
            agentId: agent.id,
            agentName: agent.name,
            error: '视频服务连接失败（超时）',
            suggestion: '请确保 AI Tutor 服务 (8001) 已启动，然后重新运行视频Agent',
          })

          // 更新资源状态为失败
          const failedResource: ResourceItem = {
            id: `video-${taskId}`,
            title: `${knowledgePoint} 教学视频`,
            type: 'video',
            module: knowledgePoint,
            url: '',
            description: '视频服务连接失败，请重新生成',
            createdAt: new Date().toISOString(),
            aiGenerated: true,
            difficulty: 'beginner',
            videoStatus: 'failed',
            video_task_id: taskId,
          }
          resourceStore.addIncrementalResources([failedResource], subject)
          addLog(`⚠️ 视频状态已更新为失败（连接超时）`)
        }
      }
    }, 2000)
  }

  /* ===== 流水线执行 ===== */

  /** Agent 索引 → 产出资源类型 */
  const AGENT_RESOURCE_TYPE: Record<number, string> = {
    1: 'document', 2: 'mindmap', 3: 'exercise', 4: 'code', 5: 'video', 7: 'knowledge-graph',
  }

  /**
   * 新老用户策略：在资源池中查找可复用的同类型同科目资源
   * - 老用户（池中已有该类型资源）→ 复用，跳过 Agent 调用
   * - 新用户（池为空）→ 返回 null，走完整生成
   */
  function findReusableResource(type: string, subject: string, pool: ResourceItem[]): ResourceItem | null {
    return pool.find(r =>
      r.type === type &&
      (r.subject === subject || !r.subject) &&
      // 文本类资源需要有 content；视频类需要有 url（已渲染完成）
      (type === 'video' ? (r.url && r.videoStatus === 'done') : !!r.content)
    ) || null
  }

  async function startTask(selectedAgents: number[] = [1, 2, 3, 4, 5, 6, 7]) {
    if (isRunning.value) return

    // 检查画像是否有数据（不再要求 phase === 'stable'）
    const profileStore = useProfileStore()
    const dims = profileStore.profileData.dimensions || []
    const hasProfileData = dims.some(d => d.value > 0) || profileStore.profileData.phase !== 'initial'
    if (!hasProfileData) {
      addLog('⚠️ 画像尚未构建，请先完成画像采集')
      return
    }

    const resourceStore = useResourceStore()
    const pathStore = usePathStore()

    resetAgents()
    isRunning.value = true
    taskStartTime.value = Date.now()

    // 计算总预估时间（不包括视频 Agent，因为它是异步的）
    const blockingAgents = selectedAgents.filter(idx => idx !== 5)
    totalEstimatedTime.value = blockingAgents.reduce((sum, idx) => sum + (agentEstimateTimes[idx] || 30), 0)
    estimatedRemainingTime.value = totalEstimatedTime.value

    addLog(`任务启动 — 选中 ${selectedAgents.length} 个智能体协作，预计 ${formatTime(totalEstimatedTime.value)}`)

    // 启动定时器更新剩余时间
    const timeUpdateInterval = setInterval(() => {
      if (!isRunning.value) {
        clearInterval(timeUpdateInterval)
        return
      }
      const elapsed = (Date.now() - taskStartTime.value) / 1000
      const completedAgents = agents.value.filter(a => a.status === 'completed').length - 1 // 减去画像 Agent
      const completedTime = completedAgents * 25 // 平均每个完成的 Agent 时间
      estimatedRemainingTime.value = Math.max(0, totalEstimatedTime.value - elapsed)
    }, 1000)

    const profileData = profileStore.profileData

    // 科目推断：优先使用画像AI提取的currentSubject，仅当未设置时才用关键词映射兜底
    let subject: string
    if (profileData.currentSubject) {
      subject = profileData.currentSubject
      addLog(`科目（AI提取）：${subject}`)
    } else {
      subject = inferSubject(profileData)
      profileStore.switchSubject(subject)
      addLog(`科目（关键词推断）：${subject}`)
    }

    // 薄弱点：优先使用当前科目 overlay 的薄弱点，过滤跨科目污染内容
    const subjectOverlay = profileData.subjectOverlays?.find(o => o.subject === subject)
    const overlayWeakPoints = subjectOverlay?.weak_points || []
    const globalWeakPoints = profileData.weak_points || []
    // 合并去重，优先 overlay 的薄弱点
    const allWeakPoints = [...new Set([...overlayWeakPoints, ...globalWeakPoints])]
    // 过滤掉不属于当前科目的薄弱点（如英语科目中的"递归"等CS内容）
    const relevantWeakPoints = filterRelevantWeakPoints(allWeakPoints, subject)
    const weakPoints = relevantWeakPoints.length > 0 ? relevantWeakPoints : [`${subject}基础`]

    // 收集所有 Agent 生成的资源
    const generatedResources: ResourceItem[] = []

    // 新老用户判定：池中是否已有当前科目的资源
    const existingForSubject = resourceStore.resources.filter(r => r.subject === subject || !r.subject)
    if (existingForSubject.length > 0) {
      addLog(`📋 老用户：资源池已有 ${existingForSubject.length} 项「${subject}」资源，将优先复用、仅为缺口生成`)
    } else {
      addLog(`🆕 新用户：资源池为空，将完整生成全部资源`)
    }

    try {
      // Stage 1: 画像 Agent（已完成，标记为完成）
      agents.value[0].status = 'completed'
      agents.value[0].progress = 100
      agents.value[0].duration = '已完成'
      agents.value[0].log = ['画像数据已就绪']
      addLog('画像Agent — 数据已就绪')
      workflowStage.value = 1

      // 主题：优先使用薄弱点，无薄弱点时使用当前科目
      const topic = weakPoints[0]

      // 辅助函数：判断是否选中某个 Agent
      const isSelected = (idx: number) => selectedAgents.includes(idx)

      // Stage 2: 文档 + 导图 + 题库 + 知识图谱（选中才并行执行）
      const stage2Agents = [1, 2, 3, 7].filter(isSelected)
      if (stage2Agents.length > 0) {
        workflowStage.value = 2

        // 新老用户策略：先复用池中已有资源，只为缺口调用 Agent
        const existingPool = resourceStore.resources
        const agentsNeedingGen: number[] = []
        for (const idx of stage2Agents) {
          const type = AGENT_RESOURCE_TYPE[idx]
          const reusable = findReusableResource(type, subject, existingPool)
          if (reusable) {
            generatedResources.push(reusable)
            agents.value[idx].status = 'completed'
            agents.value[idx].progress = 100
            agents.value[idx].duration = '已复用'
            addLog(`${AGENT_LIST[idx].name} — 复用现有资源：${reusable.title}`)
          } else {
            agentsNeedingGen.push(idx)
          }
        }

        if (agentsNeedingGen.length > 0) {
          addLog(`Stage 2 生成: ${agentsNeedingGen.map(i => AGENT_LIST[i].name).join(' / ')}`)

          const stage2Promises: Promise<string | null>[] = []
          const stage2Indices: number[] = []

          if (agentsNeedingGen.includes(1)) { stage2Promises.push(executeAgent(1, buildDocAgentMessages(profileData, topic))); stage2Indices.push(1) }
          if (agentsNeedingGen.includes(2)) { stage2Promises.push(executeAgent(2, buildMindmapAgentMessages(profileData, topic))); stage2Indices.push(2) }
          if (agentsNeedingGen.includes(3)) { stage2Promises.push(executeAgent(3, buildQuizAgentMessages(profileData, topic))); stage2Indices.push(3) }
          if (agentsNeedingGen.includes(7)) { stage2Promises.push(executeAgent(7, buildKnowledgeGraphAgentMessages(profileData, topic))); stage2Indices.push(7) }

          const stage2Results = await Promise.allSettled(stage2Promises)

          // 解析结果
          stage2Indices.forEach((agentIdx, i) => {
            const result = stage2Results[i].status === 'fulfilled' ? stage2Results[i].value : null
            if (agentIdx === 1 && result) {
              generatedResources.push({ id: `agent-doc-${Date.now()}`, title: `${topic} 知识讲解`, type: 'document', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true })
              addLog('文档Agent 完成 → 知识点讲解文档')
            } else if (agentIdx === 1) { addLog('文档Agent 未生成') }

            if (agentIdx === 2 && result) {
              const mindmapItem = parseMindmapData(result)
              if (mindmapItem) { generatedResources.push(mindmapItem); addLog('导图Agent 完成 → 知识导图') }
              else { generatedResources.push({ id: `agent-mindmap-${Date.now()}`, title: `${topic} 知识导图`, type: 'mindmap', module: topic, content: getFallbackMindmap(topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }); addLog('导图Agent 完成（降级格式）') }
            } else if (agentIdx === 2) { addLog('导图Agent 未生成') }

            if (agentIdx === 3 && result) {
              const exerciseItem = parseAssessQuestions(result, topic)
              if (exerciseItem) { generatedResources.push(exerciseItem); addLog('题库Agent 完成 → 个性化题库') }
              else { generatedResources.push({ id: `agent-exercise-${Date.now()}`, title: `${topic} 练习题`, type: 'exercise', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }); addLog('题库Agent 完成（原始格式）') }
            } else if (agentIdx === 3) { addLog('题库Agent 未生成') }

            if (agentIdx === 7 && result) {
              const graphItem = parseKnowledgeGraph(result)
              if (graphItem) { generatedResources.push(graphItem); addLog('图谱Agent 完成 → 知识关联图谱') }
              else { generatedResources.push({ id: `agent-knowledge-graph-${Date.now()}`, title: '知识关联图谱', type: 'knowledge-graph', module: topic, content: getFallbackKnowledgeGraph(topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }); addLog('图谱Agent 完成（降级格式）') }
            } else if (agentIdx === 7) { addLog('图谱Agent 未生成') }
          })
        } else if (stage2Agents.every(idx => agents.value[idx].status === 'completed')) {
          addLog('Stage 2 全部复用现有资源，跳过生成')
        }
      } else {
        addLog('Stage 2 跳过（未选中任何 Agent）')
      }

      // Stage 3: 代码 + 视频（选中才并行执行）
      const stage3Agents = [4, 5].filter(isSelected)
      if (stage3Agents.length > 0) {
        workflowStage.value = 3

        // 新老用户策略：先复用池中已有资源，只为缺口调用 Agent
        const existingPool3 = resourceStore.resources
        const agentsNeedingGen3: number[] = []
        for (const idx of stage3Agents) {
          const type = AGENT_RESOURCE_TYPE[idx]
          const reusable = findReusableResource(type, subject, existingPool3)
          if (reusable) {
            generatedResources.push(reusable)
            agents.value[idx].status = 'completed'
            agents.value[idx].progress = 100
            agents.value[idx].duration = '已复用'
            addLog(`${AGENT_LIST[idx].name} — 复用现有资源：${reusable.title}`)
          } else {
            agentsNeedingGen3.push(idx)
          }
        }

        if (agentsNeedingGen3.length > 0) {
          addLog(`Stage 3 生成: ${agentsNeedingGen3.map(i => AGENT_LIST[i].name).join(' / ')}`)

          const stage3Promises: Promise<string | ResourceItem | null>[] = []
          const stage3Indices: number[] = []

          if (agentsNeedingGen3.includes(4)) { stage3Promises.push(executeAgent(4, buildCodeAgentMessages(profileData, topic))); stage3Indices.push(4) }
          if (agentsNeedingGen3.includes(5)) { stage3Promises.push(executeVideoAgent(topic, subject)); stage3Indices.push(5) }

          const stage3Results = await Promise.allSettled(stage3Promises)

          // 解析结果
          stage3Indices.forEach((agentIdx, i) => {
            const result = stage3Results[i].status === 'fulfilled' ? stage3Results[i].value : null

            if (agentIdx === 4 && result) {
              const codeItem = typeof result === 'string' ? parseCodeExample(result, topic) : null
              if (codeItem) { generatedResources.push(codeItem) }
              else if (typeof result === 'string') { generatedResources.push({ id: `agent-code-${Date.now()}`, title: `${topic} 代码示例`, type: 'code', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }) }
              addLog('代码Agent 完成 → 代码实战案例')
            } else if (agentIdx === 4) { addLog('代码Agent 未生成') }

            if (agentIdx === 5 && result && typeof result === 'object' && 'id' in result) {
              generatedResources.push(result as ResourceItem)
              addLog(`视频Agent 已创建后台渲染任务（实际渲染完成后会自动更新资源状态）`)
              try {
                const currentCount = resourceStore.resources.length
                resourceStore.addIncrementalResources([result as ResourceItem], subject)
                addLog(`✅ 视频已实时同步到资源中心 (${currentCount} → ${resourceStore.resources.length})`)
                resourceStore.saveResources()
                addLog(`✅ 已强制保存到 localStorage`)
              } catch (e: any) { addLog(`⚠️ 视频同步失败: ${e?.message || e}`) }
            } else if (agentIdx === 5) { addLog('视频Agent 未生成') }
          })
        } else if (stage3Agents.every(idx => agents.value[idx].status === 'completed')) {
          addLog('Stage 3 全部复用现有资源，跳过生成')
        }
      } else {
        addLog('Stage 3 跳过（未选中任何 Agent）')
      }

      // Stage 4: 路径 Agent（选中才执行）
      if (isSelected(6)) {
        addLog('路径Agent 启动')
        workflowStage.value = 4

        // 提取已生成资源的类型，约束路径只能包含这些类型
        const availableTypes = [...new Set(generatedResources.map(r => r.type))]
        const pathResult = await executeAgent(6, buildPathAgentMessages(profileData, weakPoints, availableTypes))

        if (pathResult) {
          addLog('路径Agent 完成 → 学习路径规划')
          // 尝试将路径结果写入 pathStore
          try {
            let pathBlock = extractCodeBlock(pathResult, 'path-plan')
            // 兜底：当 LLM 不输出 path-plan 代码块时，尝试直接解析 JSON
            if (!pathBlock) {
              const jsonMatch = pathResult.match(/\{[\s\S]*"stages"[\s\S]*\}/)
              if (jsonMatch) pathBlock = jsonMatch[0]
            }
            if (pathBlock) {
              const pathData = JSON.parse(pathBlock)
              if (pathData.stages && Array.isArray(pathData.stages)) {
                // 先将资源写入 resourceStore，确保路径关联时资源库有数据
                if (generatedResources.length > 0) {
                  resourceStore.clearAndSetResources(generatedResources, subject)
                }
                pathStore.setAgentGeneratedStages(pathData)
                addLog(`路径Agent 完成 → 生成了 ${pathData.stages.length} 个学习阶段`)
              } else {
                addLog('路径Agent JSON 缺少 stages 字段')
              }
            } else {
              addLog('路径Agent 结果中未找到 paths-plan 或 JSON')
            }
          } catch {
            addLog('路径Agent 结果解析失败，已保留原始输出')
          }
        } else {
          addLog('路径Agent 未生成')
        }
      } else {
        addLog('Stage 4 跳过（未选中路径 Agent）')
      }

      // Stage 4.5: 为路径中每个小节的缺口生成专属资源
      // 核心改进：不再只生成 1 个资源然后让所有小节复用，
      // 而是为每个小节生成它自己的资源，确保每个小节内容不同
      // ★ 先把 Stage 2-4 已生成的资源写入 store，让 allocator 能看到它们，
      // 否则 allocator 会把所有小节都当作缺口，生成重复资源
      resourceStore.clearAndSetResources(generatedResources, subject)
      pathStore.linkResourcesToGenerated()
      const allocResult = allocate(pathStore.stages, resourceStore.resources, profileData)
      if (allocResult.gaps.length > 0) {
        addLog(`检测到 ${allocResult.gaps.length} 个资源缺口，开始为每个小节生成专属资源...`)
        workflowStage.value = 4

        // ★ 关键修复：Stage 4.5 必须尊重用户勾选
        // 只为用户勾选的 Agent 类型对应的资源缺口生成新资源
        // 未勾选的类型：仅尝试复用已有资源，不调用 Agent 生成
        const userSelectedTypes = new Set<string>()
        for (const idx of selectedAgents) {
          const t = AGENT_RESOURCE_TYPE[idx]
          if (t) userSelectedTypes.add(t)
        }

        // 混合策略：最多并行生成3个视频（非阻塞后台渲染），其余视频缺口尝试复用资源池
        // 理由：executeVideoAgent 是非阻塞的，创建任务后立即返回占位资源，
        //       3个并行不会阻塞其他Agent；Manim渲染在后台进行
        const MAX_NEW_VIDEOS = 3
        const videoGaps = allocResult.gaps.filter(g => g.type === 'video')
        const nonVideoGaps = allocResult.gaps.filter(g => g.type !== 'video')

        // 过滤：未勾选类型的缺口，只走复用，不新生成
        const videoGapsAllowed = videoGaps.filter(g => userSelectedTypes.has('video'))
        const videoGapsSkipped = videoGaps.filter(g => !userSelectedTypes.has('video'))
        const nonVideoGapsAllowed = nonVideoGaps.filter(g => userSelectedTypes.has(g.type))
        const nonVideoGapsSkipped = nonVideoGaps.filter(g => !userSelectedTypes.has(g.type))

        if (videoGapsSkipped.length > 0 || nonVideoGapsSkipped.length > 0) {
          addLog(`📋 跳过未勾选类型的缺口生成：${videoGapsSkipped.length} 个视频 + ${nonVideoGapsSkipped.length} 个其他（仅尝试复用）`)
        }

        // 按小节重要性排序视频缺口：薄弱点 > 基础 > 进阶
        // ★ 使用 videoGapsAllowed（只含用户勾选视频的缺口）而非全部 videoGaps
        const videoGapsSorted = videoGapsAllowed.map(g => {
          const stage = pathStore.stages.find(s => s.id === g.stageId)
          const priority = stage?.reasonType === 'weakness' ? 0
            : stage?.reasonType === 'foundation' ? 1
            : 2
          return { ...g, _priority: priority }
        }).sort((a, b) => a._priority - b._priority)

        // 前3个生成新视频，剩余的尝试复用资源池已有视频
        const videoGapsToGen = videoGapsSorted.slice(0, MAX_NEW_VIDEOS)
        const videoGapsToReuse = videoGapsSorted.slice(MAX_NEW_VIDEOS)

        // 未勾选视频的缺口也尝试复用（不生成新的）
        const videoGapsToReuseAll = [...videoGapsToReuse, ...videoGapsSkipped]

        if (videoGapsToReuseAll.length > 0) {
          addLog(`视频策略：新生成${videoGapsToGen.length}个，尝试复用${videoGapsToReuseAll.length}个已有视频`)
          for (const gap of videoGapsToReuseAll) {
            // 优先精确匹配 topic，其次匹配同学科任意视频
            const exactMatch = resourceStore.resources.find(r =>
              r.type === 'video' && r.module === gap.topic && r.videoStatus === 'done' && r.url
            )
            const reused = exactMatch || resourceStore.resources.find(r =>
              r.type === 'video' && r.videoStatus === 'done' && r.url &&
              r.module && r.module.includes(subject)
            )
            if (reused) {
              generatedResources.push({ ...reused, id: `reuse-${Date.now()}-${gap.prId.slice(-4)}` })
              addLog(`📹 复用已有视频「${reused.title}」→ ${gap.stageTitle}`)
            } else {
              addLog(`📋 「${gap.stageTitle}」无可用视频，已跳过视频资源`)
            }
          }
        }

        // ★ 未勾选的其他类型缺口也尝试复用（不生成新的）
        for (const gap of nonVideoGapsSkipped) {
          const reused = resourceStore.resources.find(r =>
            r.type === gap.type && r.module === gap.topic
          )
          if (reused) {
            generatedResources.push({ ...reused, id: `reuse-${Date.now()}-${gap.prId.slice(-4)}` })
            addLog(`📎 复用已有「${reused.title}」→ ${gap.stageTitle}`)
          } else {
            addLog(`📋 「${gap.stageTitle}」未勾选生成此类型，已跳过`)
          }
        }

        const gapsToGen = [...videoGapsToGen, ...nonVideoGapsAllowed]

        // 并行生成所有缺口资源
        const gapPromises: Promise<ResourceItem | null>[] = gapsToGen.map(async (gap) => {
          const agentIdx = getAgentIndexByResourceType(gap.type)
          if (agentIdx < 0) return null
          try {
            let result: string | ResourceItem | null = null
            if (agentIdx === 5) {
              result = await executeVideoAgent(gap.topic, subject)
            } else {
              const msgs = agentIdx === 1 ? buildDocAgentMessages(profileData, gap.topic)
                : agentIdx === 2 ? buildMindmapAgentMessages(profileData, gap.topic)
                : agentIdx === 3 ? buildQuizAgentMessages(profileData, gap.topic)
                : agentIdx === 4 ? buildCodeAgentMessages(profileData, gap.topic)
                : agentIdx === 7 ? buildKnowledgeGraphAgentMessages(profileData, gap.topic)
                : null
              if (!msgs) return null
              result = await executeAgent(agentIdx, msgs)
            }
            if (!result) return null

            // 解析结果为 ResourceItem
            if (agentIdx === 5 && typeof result === 'object' && 'id' in result) {
              return result as ResourceItem
            }
            if (typeof result !== 'string') return null
            if (agentIdx === 1) return { id: `gap-doc-${Date.now()}-${gap.prId.slice(-4)}`, title: `${gap.topic} 知识讲解`, type: 'document', module: gap.topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            if (agentIdx === 2) return parseMindmapData(result) || { id: `gap-mindmap-${Date.now()}-${gap.prId.slice(-4)}`, title: `${gap.topic} 知识导图`, type: 'mindmap', module: gap.topic, content: getFallbackMindmap(gap.topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }
            if (agentIdx === 3) return parseAssessQuestions(result, gap.topic) || { id: `gap-quiz-${Date.now()}-${gap.prId.slice(-4)}`, title: `${gap.topic} 练习题`, type: 'exercise', module: gap.topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            if (agentIdx === 4) return parseCodeExample(result, gap.topic) || { id: `gap-code-${Date.now()}-${gap.prId.slice(-4)}`, title: `${gap.topic} 代码示例`, type: 'code', module: gap.topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            if (agentIdx === 7) return parseKnowledgeGraph(result) || { id: `gap-graph-${Date.now()}-${gap.prId.slice(-4)}`, title: '知识关联图谱', type: 'knowledge-graph', module: gap.topic, content: getFallbackKnowledgeGraph(gap.topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }
            return null
          } catch (e) {
            addLog(`⚠️ 为「${gap.stageTitle}」生成 ${gap.type} 失败`)
            return null
          }
        })

        const gapResults = await Promise.allSettled(gapPromises)
        let gapSuccessCount = 0
        for (let i = 0; i < gapResults.length; i++) {
          const r = gapResults[i]
          if (r.status === 'fulfilled' && r.value) {
            generatedResources.push(r.value)
            gapSuccessCount++
            addLog(`✅ 为「${gapsToGen[i].stageTitle}」生成 ${gapsToGen[i].type} 资源`)
          }
        }

        // 写入资源库并重新分配
        if (gapSuccessCount > 0) {
          resourceStore.clearAndSetResources(generatedResources, subject)
          pathStore.linkResourcesToGenerated()
          addLog(`缺口生成完成：${gapSuccessCount}/${gapsToGen.length} 项资源已生成并分配到各小节`)
        } else {
          addLog(`⚠️ 缺口资源全部生成失败`)
        }
      } else {
        addLog('所有小节资源已匹配，无需补充生成')
      }

      // Stage 5: 审查 Agent — 自动运行，审查所有生成内容质量
      if (generatedResources.length > 0) {
        addLog('审查Agent 启动 — 审核所有生成内容')
        workflowStage.value = 5

        // 视频资源由后台渲染，不参与内容审查（避免误判"内容尚未生成"）
        const reviewableResources = generatedResources.filter(r => r.type !== 'video')
        if (reviewableResources.length === 0) {
          addLog('审查Agent 跳过（仅视频资源，无需文本审查）')
        } else {
          const reviewResources = reviewableResources.map(r => ({
            id: r.id,
            type: r.type,
            title: r.title,
            contentPreview: r.content || r.description || '',
          }))

          const reviewResult = await executeAgent(8, buildReviewerMessages(profileData, reviewResources))

          if (reviewResult) {
            const reviewReport = parseReviewReport(reviewResult)
            if (reviewReport) {
              const reviseItems = reviewReport.items.filter((i: any) => i.status === 'revise')
              addLog(`审查完成：${reviewReport.items.length} 项审查，${reviseItems.length} 项需修订`)

              // 对需要修订的资源，触发对应 Agent 重新生成（仅一次）
              const regeneratedAgents = new Set<number>()
              for (const item of reviseItems) {
                const agentIndex = getAgentIndexByResourceType(item.type)
                if (agentIndex >= 0 && !regeneratedAgents.has(agentIndex)) {
                  regeneratedAgents.add(agentIndex)
                  addLog(`修订 ${item.type} 资源：${item.issues.join('；')}`)

                  const correctionPrompt = `\n\n【审查修正】${item.issues.join('；')}。建议：${item.suggestion}`
                  try {
                    const correctedResult = await executeAgentWithCorrection(
                      agentIndex, profileData, weakPoints[0], correctionPrompt,
                    )
                    if (correctedResult) {
                      // 替换对应资源
                      replaceResource(generatedResources, item.resourceId, correctedResult, item.type)
                      addLog(`${item.type} 资源已修正`)
                    }
                  } catch {
                    addLog(`${item.type} 资源修正失败，保留原内容`)
                  }
                }
              }
            } else {
              addLog('审查完成（报告格式解析失败）')
            }
          } else {
            addLog('审查Agent 未生成')
          }
        }
      } else {
        addLog('Stage 5 跳过（无生成资源需审查）')
      }

      // 所有 Agent 完成 → 将资源写入 resourceStore
      if (generatedResources.length > 0) {
        resourceStore.clearAndSetResources(generatedResources, subject)
        // 重新建立路径-资源关联，确保 Reviewer 修订后 resourceRef 仍指向正确资源
        pathStore.linkResourcesToGenerated()
        // ★ 强制立即保存到 localStorage，避免 watch 防抖 500ms 期间刷新丢失
        try {
          resourceStore.saveResources()
          addLog(`✅ 已强制保存 ${generatedResources.length} 项资源到本地存储`)
        } catch (e: any) {
          addLog(`⚠️ 资源保存失败: ${e?.message || e}`)
        }
        addLog(`✅ 全部Agent完成，共生成 ${generatedResources.length} 项资源已写入资源中心`)
      } else {
        addLog('✅ 全部Agent完成，但无有效资源生成')
      }

    } catch (err: any) {
      addLog(`❌ 执行出错：${err.message}`)
      // 即使出错，也将已生成的资源写入
      if (generatedResources.length > 0) {
        resourceStore.clearAndSetResources(generatedResources, subject)
      }
    } finally {
      isRunning.value = false
    }
  }

  /** 根据资源类型找到对应 Agent 索引 */
  function getAgentIndexByResourceType(type: string): number {
    const map: Record<string, number> = {
      document: 1, mindmap: 2, exercise: 3, quiz: 3,
      code: 4, video: 5, 'knowledge-graph': 7,
      extension: 1, // extension 归一化为 document，用文档 Agent 生成
    }
    return map[type] ?? -1
  }

  /** 带修正 prompt 重新执行 Agent */
  async function executeAgentWithCorrection(
    agentIndex: number,
    profileData: any,
    topic: string,
    correctionPrompt: string,
  ): Promise<string | null> {
    try {
      const messageBuilders: Record<number, () => { role: 'system' | 'user' | 'assistant'; content: string }[]> = {
        1: () => buildDocAgentMessages(profileData, topic),
        2: () => buildMindmapAgentMessages(profileData, topic),
        3: () => buildQuizAgentMessages(profileData, topic),
        4: () => buildCodeAgentMessages(profileData, topic),
        5: () => buildVideoAgentMessages(profileData, topic),
        7: () => buildKnowledgeGraphAgentMessages(profileData, topic),
      }
      const builder = messageBuilders[agentIndex]
      if (!builder) return null

      const messages = builder()
      // 在用户消息末尾附加修正要求
      const lastMsg = messages[messages.length - 1]
      if (lastMsg) lastMsg.content += correctionPrompt

      return await executeAgent(agentIndex, messages)
    } catch {
      return null
    }
  }

  /** 替换生成资源列表中指定 ID 的资源 */
  function replaceResource(resources: ResourceItem[], resourceId: string, newContent: string, type: string) {
    const idx = resources.findIndex(r => r.id === resourceId)
    if (idx < 0) return
    // 根据类型解析新内容
    if (type === 'exercise' || type === 'quiz') {
      const parsed = parseAssessQuestions(newContent, '')
      if (parsed) { resources[idx] = parsed; return }
      // 解析失败，保留原内容
      return
    }
    if (type === 'mindmap') {
      const parsed = parseMindmapData(newContent)
      if (parsed) { resources[idx] = parsed; return }
      // 解析失败，保留原内容
      return
    }
    if (type === 'knowledge-graph') {
      const parsed = parseKnowledgeGraph(newContent)
      if (parsed) { resources[idx].content = parsed.content; return }
      // 解析失败，保留原内容
      return
    }
    if (type === 'code') {
      const parsed = parseCodeExample(newContent, resources[idx].module || '')
      if (parsed) { resources[idx] = parsed; return }
      // 解析失败，保留原内容
      return
    }
    // 默认：更新 content
    resources[idx].content = newContent
  }

  function stopTask() {
    for (const ctrl of abortControllers) {
      ctrl.abort()
    }
    abortControllers = []
    isRunning.value = false
    addLog('任务已中断')
  }

  /* ===== 随学随新：画像变化后自动增量运行智能体 ===== */

  /**
   * 根据画像变化信息，自动运行必要的 Agent 生成增量资源。
   * 不清空已有资源，增量添加新资源。
   */
  async function autoRunForChange(changeInfo: ProfileChangeInfo) {
    if (isRunning.value) return

    const profileStore = useProfileStore()
    const resourceStore = useResourceStore()
    const profileData = profileStore.profileData
    const subject = profileData.currentSubject || inferSubject(profileData)

    // 确定需要运行的 Agent 和目标难度
    const { event, changeType } = changeInfo

    // 根据变化类型决定难度
    let targetDifficulty: 'beginner' | 'intermediate' | 'advanced'
    if (changeType === 'downgrade') {
      targetDifficulty = 'beginner'
    } else if (changeType === 'upgrade') {
      targetDifficulty = 'advanced'
    } else {
      targetDifficulty = 'intermediate'
    }

    // 确定需要运行的 Agent 索引（1=文档, 2=导图, 3=题库, 4=代码, 5=视频, 7=图谱）
    let agentIndices: number[] = []
    let description = ''

    if (event.type === 'assess_complete' && (event.score ?? 0) < 60) {
      // 测评低分 → 文档+导图+题库+图谱，降级难度
      agentIndices = [1, 2, 3, 7]
      description = `测评得分低(${event.score}分)，自动生成降级难度资源`
    } else if (event.type === 'assess_complete' && (event.score ?? 0) >= 80) {
      // 测评高分 → 代码+题库+图谱，进阶资源
      agentIndices = [3, 4, 7]
      description = `测评得分高(${event.score}分)，自动生成进阶资源`
    } else if (event.type === 'stage_complete') {
      // 完成阶段 → 题库+视频+图谱，新知识点资源
      agentIndices = [3, 5, 7]
      description = `完成学习阶段，自动生成新知识点资源`
    } else if (changeType === 'downgrade') {
      // 薄弱点增加 → 文档+题库+图谱
      agentIndices = [1, 3, 7]
      description = `薄弱点增加，自动生成基础巩固资源`
    } else if (changeType === 'upgrade') {
      // 画像提升 → 代码+题库
      agentIndices = [4, 3]
      description = `画像提升，自动生成进阶挑战资源`
    } else {
      // 默认：文档+题库
      agentIndices = [1, 3]
      description = `画像变化，自动生成匹配资源`
    }

    isRunning.value = true
    addLog(`🔄 随学随新：${description}`)

    // 确定主题（薄弱点或变化维度），无薄弱点时使用当前科目作为默认主题
    // ★ 过滤跨科目污染的薄弱点
    const rawWp = profileData.weak_points || []
    const relevantWp = filterRelevantWeakPoints(rawWp, subject)
    const weakPoints = relevantWp.length > 0 ? relevantWp : [`${subject}基础`]
    const topic = weakPoints[0]

    const generatedResources: ResourceItem[] = []

    try {
      // 并行运行选中的 Agent
      const promises = agentIndices.map(async (idx) => {
        const agent = agents.value[idx]
        if (!agent) return null

        let messages: { role: 'system' | 'user' | 'assistant'; content: string }[] = []
        switch (idx) {
          case 1: messages = buildDocAgentMessages(profileData, topic); break
          case 2: messages = buildMindmapAgentMessages(profileData, topic); break
          case 3: messages = buildQuizAgentMessages(profileData, topic); break
          case 4: messages = buildCodeAgentMessages(profileData, topic); break
          case 5: messages = buildVideoAgentMessages(profileData, topic); break
          case 7: messages = buildKnowledgeGraphAgentMessages(profileData, topic); break
        }

        // 在 prompt 中注入难度指示
        if (messages.length > 0 && targetDifficulty !== 'intermediate') {
          const diffHint = targetDifficulty === 'beginner'
            ? '\n\n【重要】用户当前基础薄弱，请生成简单易懂、循序渐进的内容，避免复杂概念。'
            : '\n\n【重要】用户已掌握基础，请生成有挑战性的进阶内容，包含更复杂的场景。'
          messages[0].content += diffHint
        }

        const result = await executeAgent(idx, messages)
        return { idx, result }
      })

      const results = await Promise.allSettled(promises)

      // 解析各 Agent 输出
      for (const r of results) {
        if (r.status !== 'fulfilled' || !r.value || !r.value.result) continue
        const { idx, result } = r.value

        switch (idx) {
          case 1: // 文档
            generatedResources.push({
              id: `auto-doc-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              title: `${topic} ${targetDifficulty === 'beginner' ? '基础' : '进阶'}讲解`,
              type: 'document',
              module: topic,
              content: result,
              difficulty: targetDifficulty,
              createdAt: new Date().toISOString(),
              aiGenerated: true,
              isAutoGenerated: true,
            })
            break
          case 2: // 导图
            {
              const mindmapItem = parseMindmapData(result)
              if (mindmapItem) {
                mindmapItem.difficulty = targetDifficulty
                mindmapItem.isAutoGenerated = true
                generatedResources.push(mindmapItem)
              } else {
                generatedResources.push({
                  id: `auto-mindmap-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  title: `${topic} 知识导图`,
                  type: 'mindmap',
                  module: topic,
                  content: getFallbackMindmap(topic, profileData.weak_points),
                  difficulty: targetDifficulty,
                  createdAt: new Date().toISOString(),
                  aiGenerated: true,
                  isAutoGenerated: true,
                })
              }
            }
            break
          case 3: // 题库
            {
              const exerciseItem = parseAssessQuestions(result, topic)
              if (exerciseItem) {
                exerciseItem.difficulty = targetDifficulty
                exerciseItem.isAutoGenerated = true
                generatedResources.push(exerciseItem)
              } else {
                generatedResources.push({
                  id: `auto-exercise-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  title: `${topic} ${targetDifficulty === 'beginner' ? '基础' : '进阶'}练习`,
                  type: 'exercise',
                  module: topic,
                  content: result,
                  difficulty: targetDifficulty,
                  createdAt: new Date().toISOString(),
                  aiGenerated: true,
                  isAutoGenerated: true,
                })
              }
            }
            break
          case 4: // 代码
            {
              const codeItem = parseCodeExample(result, topic)
              if (codeItem) {
                codeItem.difficulty = targetDifficulty
                codeItem.isAutoGenerated = true
                generatedResources.push(codeItem)
              } else {
                generatedResources.push({
                  id: `auto-code-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  title: `${topic} 代码示例`,
                  type: 'code',
                  module: topic,
                  content: result,
                  difficulty: targetDifficulty,
                  createdAt: new Date().toISOString(),
                  aiGenerated: true,
                  isAutoGenerated: true,
                })
              }
            }
            break
          case 5: // 视频
            {
              const videoItems = parseResourceList(result, 'video')
              for (const vi of videoItems) {
                vi.difficulty = targetDifficulty
                vi.isAutoGenerated = true
              }
              generatedResources.push(...videoItems)
            }
            break
          case 7: // 知识图谱
            {
              const graphItem = parseKnowledgeGraph(result)
              if (graphItem) {
                graphItem.difficulty = targetDifficulty
                graphItem.isAutoGenerated = true
                generatedResources.push(graphItem)
              } else {
                generatedResources.push({
                  id: `auto-graph-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  title: '知识关联图谱',
                  type: 'knowledge-graph',
                  module: topic,
                  content: getFallbackKnowledgeGraph(topic, profileData.weak_points),
                  difficulty: targetDifficulty,
                  createdAt: new Date().toISOString(),
                  aiGenerated: true,
                  isAutoGenerated: true,
                })
              }
            }
            break
        }
      }

      // 增量添加资源（不清空已有资源）
      if (generatedResources.length > 0) {
        resourceStore.addIncrementalResources(generatedResources, subject)
        addLog(`✅ 随学随新完成，增量生成 ${generatedResources.length} 项${targetDifficulty === 'beginner' ? '基础' : targetDifficulty === 'advanced' ? '进阶' : ''}资源`)
      } else {
        addLog('随学随新完成，无新资源生成')
      }

    } catch (err: any) {
      addLog(`❌ 随学随新出错：${err.message}`)
    } finally {
      isRunning.value = false
    }
  }

  /* ===== 全局画像变化监听 ===== */
  const profileStore = useProfileStore()

  watch(
    () => profileStore.profileChangeInfo,
    (changeInfo) => {
      if (!changeInfo || isRunning.value) return
      // 画像有数据才自动运行（不要求 phase === 'stable'）
      if (profileStore.profileData.dimensions?.some(d => d.value > 0)) {
        autoRunForChange(changeInfo)
      }
    },
  )

  /**
   * 重新生成单个资源
   * @param resourceType 资源类型：document, mindmap, exercise, code, video, knowledge-graph
   * @param topic 知识点主题
   * @param feedback 不满意原因（可选）。有反馈时带修正 prompt 重做，而非简单直接生成
   * @returns 生成的资源或 null
   */
  async function regenerateSingleResource(
    resourceType: string,
    topic: string,
    feedback?: { reason: string; detail?: string },
  ): Promise<ResourceItem | null> {
    const profileData = profileStore.profileData
    const resourceStore = useResourceStore()
    const subject = profileData.currentSubject || inferSubject(profileData)
    const agentIndex = getAgentIndexByResourceType(resourceType)
    if (agentIndex < 0) {
      addLog(`⚠️ 无法重新生成：未知资源类型 ${resourceType}`)
      return null
    }

    const hasFeedback = !!(feedback && feedback.reason)
    addLog(hasFeedback
      ? `退回重做 ${resourceType} 资源（原因：${feedback!.reason}）...`
      : `重新生成 ${resourceType} 资源...`)
    agents.value[agentIndex].status = 'running'
    agents.value[agentIndex].progress = 0

    // 有反馈时拼修正 prompt
    const correctionPrompt = hasFeedback
      ? `\n\n【用户反馈】不满意原因：${feedback!.reason}${feedback!.detail ? `。具体说明：${feedback!.detail}` : ''}。请根据此反馈改进内容，避免之前的问题。`
      : ''

    try {
      let result: string | ResourceItem | null = null

      // 根据类型调用对应 Agent
      // 有反馈 → executeAgentWithCorrection（带修正 prompt）
      // 无反馈 → executeAgent（普通生成）
      // 视频始终用 executeVideoAgent（重新创建渲染任务）
      switch (agentIndex) {
        case 1: result = hasFeedback
          ? await executeAgentWithCorrection(1, profileData, topic, correctionPrompt)
          : await executeAgent(1, buildDocAgentMessages(profileData, topic)); break
        case 2: result = hasFeedback
          ? await executeAgentWithCorrection(2, profileData, topic, correctionPrompt)
          : await executeAgent(2, buildMindmapAgentMessages(profileData, topic)); break
        case 3: result = hasFeedback
          ? await executeAgentWithCorrection(3, profileData, topic, correctionPrompt)
          : await executeAgent(3, buildQuizAgentMessages(profileData, topic)); break
        case 4: result = hasFeedback
          ? await executeAgentWithCorrection(4, profileData, topic, correctionPrompt)
          : await executeAgent(4, buildCodeAgentMessages(profileData, topic)); break
        case 5: result = await executeVideoAgent(topic, subject); break
        case 7: result = hasFeedback
          ? await executeAgentWithCorrection(7, profileData, topic, correctionPrompt)
          : await executeAgent(7, buildKnowledgeGraphAgentMessages(profileData, topic)); break
      }

      if (!result) {
        addLog(`${resourceType} 重新生成失败`)
        agents.value[agentIndex].status = 'error'
        return null
      }

      // 解析结果为 ResourceItem
      let newResource: ResourceItem | null = null
      if (agentIndex === 5 && typeof result === 'object' && 'id' in result) {
        newResource = result as ResourceItem
      } else if (typeof result === 'string') {
        switch (agentIndex) {
          case 1:
            newResource = { id: `regen-doc-${Date.now()}`, title: `${topic} 知识讲解`, type: 'document', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            break
          case 2:
            newResource = parseMindmapData(result) || { id: `regen-mindmap-${Date.now()}`, title: `${topic} 知识导图`, type: 'mindmap', module: topic, content: getFallbackMindmap(topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }
            break
          case 3:
            newResource = parseAssessQuestions(result, topic) || { id: `regen-exercise-${Date.now()}`, title: `${topic} 练习题`, type: 'exercise', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            break
          case 4:
            newResource = parseCodeExample(result, topic) || { id: `regen-code-${Date.now()}`, title: `${topic} 代码示例`, type: 'code', module: topic, content: result, createdAt: new Date().toISOString(), aiGenerated: true }
            break
          case 7:
            newResource = parseKnowledgeGraph(result) || { id: `regen-graph-${Date.now()}`, title: '知识关联图谱', type: 'knowledge-graph', module: topic, content: getFallbackKnowledgeGraph(topic, profileData.weak_points), createdAt: new Date().toISOString(), aiGenerated: true }
            break
        }
      }

      if (newResource) {
        // ★ 退回重做：直接替换同类型同主题旧资源的内容（保持 id 不变，避免 v-for 重新挂载导致闪屏）
        // addIncrementalResources 按 title 匹配时只更新 url/videoStatus，不更新 content，
        // 所以非视频资源退回重做后内容不会变化 —— 这里手动替换 content
        const oldIdx = resourceStore.resources.findIndex(r =>
          r.type === newResource.type && (r.module === newResource.module || r.title === newResource.title)
        )
        if (oldIdx !== -1) {
          const old = resourceStore.resources[oldIdx]
          old.content = newResource.content
          old.title = newResource.title
          old.description = newResource.description || old.description
          old.createdAt = newResource.createdAt
          old.aiGenerated = true
          // 视频资源退回重做：同步更新视频字段，重置为生成中状态
          // 否则旧资源保留旧 videoStatus='done'，后台轮询完成后 addIncrementalResources
          // 匹配不到 video_task_id，导致新视频状态无法同步
          if (newResource.type === 'video') {
            old.url = newResource.url
            old.videoStatus = newResource.videoStatus
            old.video_task_id = newResource.video_task_id
          }
          // 保留旧 id 以避免 v-for key 变化导致的卡片重新挂载
          // 保存到 localStorage
          resourceStore.saveResources()
          addLog(`✅ ${resourceType} 退回重做完成（内容已替换）`)
        } else {
          // 未找到匹配的旧资源，作为新资源添加
          resourceStore.addIncrementalResources([newResource], profileStore.profileData.currentSubject)
          addLog(`✅ ${resourceType} 重新生成完成（新增资源）`)
        }
        agents.value[agentIndex].status = 'completed'
        agents.value[agentIndex].progress = 100
        return newResource
      }

      return null
    } catch (e: any) {
      addLog(`❌ ${resourceType} 重新生成出错：${e.message}`)
      agents.value[agentIndex].status = 'error'
      return null
    }
  }

  return { agents, logs, workflowStage, isRunning, profileReady, errorDetails, estimatedRemainingTime, totalEstimatedTime, startTask, stopTask, clearLogs, clearErrors, resetAgents, autoRunForChange, regenerateSingleResource, formatTime }
})
