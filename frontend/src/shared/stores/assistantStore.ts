import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useProfileStore } from '../../modules/profile/stores/profileStore'
import { useResourceStore } from '../../modules/resource/stores/resourceStore'
import { usePathStore } from '../../modules/path/stores/pathStore'
import { useAssessStore } from '../../modules/assess/stores/assessStore'
import { useWorkspaceStore } from '../../modules/workspace/stores/workspaceStore'
import { chatGLM } from '../api/glmApi'
import { buildQAMessages } from '../../modules/qa/prompts/qaPrompts'

export interface AssistantMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
}

export const useAssistantStore = defineStore('assistant', () => {
  const isOpen = ref(false)
  const messages = ref<AssistantMessage[]>([])
  const isStreaming = ref(false)
  const contextTopic = ref('')
  let abortController: AbortController | null = null

  /**
   * 根据当前路由推算对话上下文
   * 由 FloatingAssistant 组件调用（传入 route.path），不在 store 内 useRoute
   */
  function deriveContext(currentPath: string): string {
    try {
      const profileStore = useProfileStore()
      const major = profileStore.profileData?.major || ''
      const weakPoints = profileStore.profileData?.weak_points?.join('、') || ''
      const baseInfo = `用户专业：${major}${weakPoints ? `，薄弱点：${weakPoints}` : ''}。`

      // ===== 答题页面：注入当前题目 =====
      if (currentPath.includes('/assess')) {
        try {
          const assessStore = useAssessStore()
          const q = assessStore.currentQuestion
          if (q) {
            contextTopic.value = q.question.slice(0, 20) + '...'
            const qType = q.type === 'choice' ? '选择题' : q.type === 'fill' ? '填空题' : '题目'
            let qDesc = `用户正在做${qType}："${q.question}"`
            if (q.options?.length) {
              qDesc += `\n选项：${q.options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`).join('；')}`
            }
            if (q.knowledgePoints?.length) {
              qDesc += `\n涉及知识点：${q.knowledgePoints.join('、')}`
            }
            qDesc += `\n${baseInfo}请围绕此题提供解题思路和知识点讲解，但不要直接给出正确答案（可以给提示和引导）。`
            return qDesc
          }
        } catch { /* assessStore 可能未初始化 */ }
        contextTopic.value = '练习评估'
        return `用户正在做练习题评估。${baseInfo}请围绕考题知识点提供解释和帮助，给解题思路但不要直接给答案。`
      }

      // ===== 工作台页面：注入当前阶段+选中资源 =====
      if (currentPath.includes('/workspace')) {
        try {
          const wsStore = useWorkspaceStore()
          const sel = wsStore.selectedResource
          if (sel) {
            contextTopic.value = sel.title
            return `用户正在工作台阅读资源"${sel.title}"（类型：${sel.type}，模块：${sel.module || ''}）。${baseInfo}请围绕此知识点提供精准帮助。`
          }
          const stages = wsStore.stages
          const active = stages.find(s => s.status === 'active')
          if (active) {
            contextTopic.value = active.title
            return `用户当前学习阶段："${active.title}"。${baseInfo}请围绕此阶段内容提供帮助。`
          }
        } catch { /* wsStore 可能未初始化 */ }
        contextTopic.value = '学习工作台'
        return `用户正在学习工作台。${baseInfo}请提供学习帮助。`
      }

      // ===== 资源页面 =====
      if (currentPath.includes('/resource')) {
        try {
          const resourceStore = useResourceStore()
          const sel = resourceStore.selectedResource
          if (sel) {
            contextTopic.value = sel.title
            return `用户正在阅读资源"${sel.title}"（类型：${sel.type}）。${baseInfo}请围绕此知识点提供精准帮助。`
          }
        } catch { /* */ }
        contextTopic.value = '资源中心'
        return `用户正在浏览学习资源。${baseInfo}请准备回答相关学习问题。`
      }

      // ===== 路径页面 =====
      if (currentPath.includes('/path')) {
        try {
          const pathStore = usePathStore()
          const stages = pathStore.stages || []
          const activeStage = stages.find(s => s.status === 'active')
          if (activeStage) {
            contextTopic.value = activeStage.title
            return `用户当前学习阶段："${activeStage.title}"。${baseInfo}请围绕此阶段内容提供帮助。`
          }
        } catch { /* */ }
        contextTopic.value = '学习路径'
        return `用户正在规划学习路径。${baseInfo}`
      }

      // ===== 画像页面 =====
      if (currentPath.includes('/profile')) {
        contextTopic.value = '学习画像'
        return `用户正在查看/编辑学习画像。${baseInfo}请帮助用户理解画像各项指标的含义，以及如何改善薄弱点。`
      }

      // ===== 答疑页面 =====
      if (currentPath.includes('/qa')) {
        contextTopic.value = '答疑'
        return `用户正在答疑页面。${baseInfo}已在正常对话中。`
      }

      // ===== 默认 =====
      contextTopic.value = ''
      return `${baseInfo}请提供学习帮助。`
    } catch {
      return ''
    }
  }

  /** 生成3个快捷提问建议 */
  function getQuickQuestions(context: string): string[] {
    if (context.includes('做选择题') || context.includes('做填空题') || context.includes('做题目')) {
      return [
        '这道题的解题思路是什么？',
        '相关的知识点能帮我梳理一下吗？',
        '给点提示，别直接告诉我答案',
      ]
    }
    if (context.includes('练习题评估')) {
      return [
        '提示我一下，不要直接给答案',
        '这个知识点我不太懂，能讲讲吗？',
        '换一道类似的题再练练',
      ]
    }
    if (context.includes('阅读资源')) {
      return [
        '这段内容不太懂，能再解释一遍吗？',
        '能举个具体的例子吗？',
        '这个知识点在实际中怎么应用？',
      ]
    }
    if (context.includes('学习阶段') || context.includes('工作台')) {
      return [
        '这个阶段的学习重点是什么？',
        '推荐一些额外的学习资料',
        '学完这个阶段后该学什么？',
      ]
    }
    if (context.includes('画像')) {
      return [
        '我的画像各项指标是什么意思？',
        '怎么改善我的薄弱点？',
        '如何提升学习效率？',
      ]
    }
    return [
      '我想复习一下最近学的内容',
      '帮我梳理一下知识框架',
      '推荐一些练习题',
    ]
  }

  const quickQuestions = computed(() => getQuickQuestions(contextTopic.value))

  function toggle() {
    isOpen.value = !isOpen.value
    if (isOpen.value && messages.value.length === 0) {
      messages.value.push({
        id: 'welcome',
        role: 'assistant',
        content: '你好！我是你的AI学习助手。做题不会可以问我思路，看资源有疑问也可以随时提问。',
        timestamp: Date.now(),
      })
    }
  }

  function open() {
    if (!isOpen.value) toggle()
  }

  function close() {
    isOpen.value = false
  }

  function addMessage(msg: AssistantMessage) {
    messages.value.push(msg)
  }

  function clearMessages() {
    messages.value = []
  }

  /** 发送消息并调用 chatGLM 流式回复 */
  function sendMessage(text: string, currentPath: string) {
    if (!text.trim() || isStreaming.value) return

    // 切换页面时清空旧消息
    const userMsg: AssistantMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    const aiMsgId = `a_${Date.now()}`
    messages.value.push({
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    })

    isStreaming.value = true

    const context = deriveContext(currentPath)

    const profileStore = useProfileStore()
    const chatHistory = messages.value
      .filter(m => m.id !== aiMsgId && m.role !== 'system')
      .slice(-20)
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    let glmMessages: { role: 'system' | 'user' | 'assistant'; content: string }[]
    try {
      glmMessages = buildQAMessages(text, profileStore.profileData, chatHistory)
      // 将上下文注入到 system message 中
      if (glmMessages.length > 0 && glmMessages[0].role === 'system' && context) {
        glmMessages[0].content = `${glmMessages[0].content}\n\n当前场景：${context}`
      }
    } catch (err: any) {
      glmMessages = [
        { role: 'system', content: `你是一个学习助手。${context}` },
        { role: 'user', content: text },
      ]
    }

    let hasContent = false
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null

    fallbackTimer = setTimeout(() => {
      if (!hasContent && isStreaming.value) {
        console.warn('[Assistant] GLM 超时(15s)，降级')
        abortController?.abort()
        abortController = null
        applyFallback(aiMsgId, text)
      }
    }, 15000)

    abortController = chatGLM(
      glmMessages,
      (chunkText: string) => {
        hasContent = true
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.content = (aiMsg.content || '') + chunkText
        }
      },
      () => {
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.isStreaming = false
          if (!aiMsg.content?.trim()) {
            aiMsg.content = `关于"${text}"，建议你从基础概念入手，结合练习题加深理解。如果有具体困惑，请继续提问！`
          }
        }
        isStreaming.value = false
        abortController = null
      },
      (_err: Error) => {
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        console.warn('[Assistant] GLM 失败，降级:', _err.message)
        applyFallback(aiMsgId, text)
        abortController = null
      },
    )
  }

  function applyFallback(aiMsgId: string, question: string) {
    const aiMsg = messages.value.find(m => m.id === aiMsgId)
    if (aiMsg) {
      aiMsg.content = aiMsg.content?.trim()
        ? aiMsg.content
        : `关于"${question}"，建议你从基础概念入手，结合教材和练习题来巩固理解。如有具体问题可以继续提问！`
      aiMsg.isStreaming = false
    }
    isStreaming.value = false
  }

  function stopGenerating() {
    abortController?.abort()
    abortController = null
    isStreaming.value = false
    const lastAi = [...messages.value].reverse().find(m => m.role === 'assistant' && m.isStreaming)
    if (lastAi) lastAi.isStreaming = false
  }

  return {
    isOpen, messages, isStreaming, contextTopic,
    quickQuestions,
    deriveContext, toggle, open, close,
    addMessage, clearMessages, sendMessage, stopGenerating,
  }
})
