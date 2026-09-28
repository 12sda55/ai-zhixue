import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage } from '../../../shared/types'
import { chatGLM } from '../../../shared/api/glmApi'
import { buildQAMessages } from '../prompts/qaPrompts'
import { useProfileStore } from '../../profile/stores/profileStore'

// 专业相关的模拟回答
const MOCK_QA_RESPONSES_BY_MAJOR: Record<string, Record<string, string>> = {
  '计算机科学': {
    '时间复杂度': `**时间复杂度**是衡量算法效率的重要指标，表示算法执行时间随输入规模增长的趋势。\n\n常见时间复杂度：O(1) 常数、O(log n) 对数、O(n) 线性、O(n log n) 线性对数、O(n²) 平方。\n\n> 计算时间复杂度时，只保留最高阶项，忽略常数系数。`,
    '链表': `**链表**是一种动态数据结构，每个节点包含数据和指向下一个节点的指针。\n\n与数组对比：链表插入删除 O(1)，访问 O(n)；数组访问 O(1)，插入删除 O(n)。`,
    '排序': `**排序算法**将数据按特定顺序排列。\n\n| 算法 | 平均 | 最坏 | 稳定 |\n|------|------|------|------|\n| 冒泡 | O(n²) | O(n²) | ✅ |\n| 快排 | O(nlogn) | O(n²) | ❌ |\n| 归并 | O(nlogn) | O(nlogn) | ✅ |`,
  },
  '物理学': {
    '牛顿定律': `**牛顿三定律**是经典力学的基础。\n\n1. **第一定律（惯性定律）**：物体在不受外力或合外力为零时，保持静止或匀速直线运动。\n\n2. **第二定律**：$F = ma$，力等于质量乘以加速度。\n\n3. **第三定律**：作用力与反作用力大小相等、方向相反、作用在不同物体上。`,
    '能量': `**能量守恒定律**：能量既不会凭空产生，也不会凭空消失，只能从一种形式转化为另一种形式。\n\n常见能量形式：动能 $E_k = \\frac{1}{2}mv^2$、势能 $E_p = mgh$、热能、电能等。`,
    '电磁': `**电磁学基础**：电荷产生电场，运动电荷产生磁场。\n\n- 库仑定律：$F = k\\frac{q_1 q_2}{r^2}$\n- 欧姆定律：$U = IR$\n- 电磁感应：变化的磁场产生电场`,
  },
  '化学': {
    '有机化学': `**有机化学**研究含碳化合物的结构、性质和反应。\n\n**官能团分类**：\n- 烷烃：C-C 单键\n- 烯烃：C=C 双键\n- 羧酸：-COOH\n- 醇：-OH\n- 醛：-CHO\n\n**反应类型**：加成反应、取代反应、消除反应、氧化还原反应。`,
    '化学键': `**化学键**是原子之间的相互作用力。\n\n- **离子键**：电子转移，如 NaCl\n- **共价键**：电子共享，如 H₂、CH₄\n- **金属键**：金属原子间的电子海模型`,
    '反应速率': `**化学反应速率**：单位时间内反应物浓度的变化。\n\n影响因素：\n- 温度（升高温度加快反应）\n- 浓度（增加浓度加快反应）\n- 催化剂（降低活化能）\n- 表面积（增大接触面积）`,
  },
  '数学与应用数学': {
    '微积分': `**微积分**是研究函数变化率（微分）和累积量（积分）的数学分支。\n\n- **导数**：$f'(x) = \\lim_{\\Delta x \\to 0} \\frac{f(x+\\Delta x) - f(x)}{\\Delta x}$\n- **积分**：$\\int f(x)dx$ 表示函数的累积\n\n基本定理：微分和积分是互逆运算。`,
    '线性代数': `**线性代数**研究向量、矩阵和线性变换。\n\n- **矩阵运算**：加法、乘法、逆矩阵\n- **向量空间**：线性无关、基、维度\n- **特征值**：$Av = \\lambda v$`,
    '概率论': `**概率论**研究随机事件的规律。\n\n- **条件概率**：$P(A|B) = \\frac{P(A\\cap B)}{P(B)}$\n- **贝叶斯公式**：$P(A|B) = \\frac{P(B|A)P(A)}{P(B)}$`,
  },
  '经济学': {
    '供给需求': `**供给与需求**是市场经济的核心机制。\n\n- **需求曲线**：价格越低，需求量越大\n- **供给曲线**：价格越高，供给量越大\n- **均衡价格**：供给曲线与需求曲线交点`,
    '边际分析': `**边际分析**：研究增加一单位投入带来的额外收益。\n\n- **边际效用**：消费增加一单位带来的满足感变化\n- **边际成本**：生产增加一单位的成本变化\n- **利润最大化**：边际收益 = 边际成本`,
    '市场结构': `**市场结构类型**：\n- 完全竞争：无数厂商，同质产品\n- 垄断竞争：多家厂商，差异化产品\n- 寡头垄断：少数厂商\n- 完全垄断：唯一厂商`,
  },
  '医学': {
    '解剖学': `**人体解剖学**研究人体结构。\n\n**主要系统**：\n- 骨骼系统：206块骨骼\n- 肌肉系统：600多块肌肉\n- 循环系统：心脏、血管\n- 神经系统：大脑、脊髓、神经`,
    '生理学': `**生理学**研究人体功能。\n\n- **血液循环**：体循环和肺循环\n- **呼吸机制**：气体交换过程\n- **神经传导**：动作电位产生与传递`,
    '病理学': `**病理学**研究疾病的发生机制。\n\n- **炎症反应**：红、肿、热、痛、功能障碍\n- **肿瘤分类**：良性肿瘤和恶性肿瘤\n- **免疫反应**：先天免疫和后天免疫`,
  },
  '历史学': {
    '朝代': `**中国古代朝代顺序**：夏→商→周→秦→汉→三国→晋→南北朝→隋→唐→宋→元→明→清。\n\n**重要事件**：\n- 秦统一六国（公元前221年）\n- 汉武帝开疆拓土\n- 唐朝盛世（贞观之治、开元盛世）`,
    '近代史': `**中国近代史**（1840-1949）重要事件：\n\n- 1840年：鸦片战争，中国开始沦为半殖民地\n- 1911年：辛亥革命，推翻清朝\n- 1919年：五四运动，新民主主义革命开端\n- 1949年：新中国成立`,
    '世界史': `**世界历史重要事件**：\n\n- 文艺复兴（14-17世纪）：人文主义兴起\n- 工业革命（18世纪）：生产力飞跃\n- 第一次世界大战（1914-1918）\n- 第二次世界大战（1939-1945）`,
  },
}

function findMockResponse(question: string, major: string): string {
  // 先查找专业相关的回答
  const majorResponses = MOCK_QA_RESPONSES_BY_MAJOR[major] || {}
  for (const [key, value] of Object.entries(majorResponses)) {
    if (question.includes(key)) return value
  }
  
  // 再查找通用回答（计算机科学）
  const genericResponses = MOCK_QA_RESPONSES_BY_MAJOR['计算机科学'] || {}
  for (const [key, value] of Object.entries(genericResponses)) {
    if (question.includes(key)) return value
  }
  
  // 默认回答
  return `关于"${question}"：这是${major || '该学科'}中的重要知识点。建议从基本概念入手，结合教材和练习题来巩固理解。如有具体问题可以继续提问！`
}

export const useQaStore = defineStore('qa', () => {
  const messages = ref<ChatMessage[]>([])
  const history = ref<{ question: string; time: string; type: string }[]>([])
  const isGenerating = ref(false)
  let abortController: AbortController | null = null

  function sendMessage(content: string) {
    if (!content?.trim() || isGenerating.value) return

    // 用户消息
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    }
    messages.value.push(userMsg)

    // 记录历史
    history.value.unshift({
      question: content.length > 15 ? content.slice(0, 15) + '...' : content,
      time: '刚刚',
      type: '文字',
    })

    // AI 消息占位
    const aiMsgId = `a-${Date.now()}`
    messages.value.push({
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true,
    })

    // 开始 GLM 请求
    askGLM(content, aiMsgId)
  }

  function askGLM(question: string, aiMsgId: string) {
    isGenerating.value = true

    const profileStore = useProfileStore()
    const major = profileStore.profileData.major || '通用学科'
    const chatHistory = messages.value
      .filter(m => m.id !== aiMsgId && m.role !== 'system' as string)
      .slice(-20)
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }))

    let glmMessages: { role: 'system' | 'user' | 'assistant'; content: string }[]

    try {
      glmMessages = buildQAMessages(question, profileStore.profileData, chatHistory)
    } catch (err: any) {
      console.error('[QA] 构建 prompt 失败，降级:', err.message)
      applyFallback(aiMsgId, question, major)
      return
    }

    console.log('[QA] 发送 GLM 请求, messages:', glmMessages.length)

    let hasContent = false
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null

    // 10秒超时降级：如果 API 无响应则自动降级
    fallbackTimer = setTimeout(() => {
      if (!hasContent && isGenerating.value) {
        console.warn('[QA] GLM 超时(10s)，降级')
        abortController?.abort()
        abortController = null
        applyFallback(aiMsgId, question, major)
      }
    }, 10000)

    abortController = chatGLM(
      glmMessages,
      // onChunk
      (text: string) => {
        hasContent = true
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.content = (aiMsg.content || '') + text
        }
      },
      // onDone
      () => {
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        console.log('[QA] GLM 完成, hasContent:', hasContent)
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.isStreaming = false
          if (!aiMsg.content?.trim()) {
            aiMsg.content = findMockResponse(question, major)
            aiMsg.source = '知识库匹配'
          } else {
            aiMsg.source = 'AI 生成'
          }
        }
        isGenerating.value = false
      },
      // onError
      (err: Error) => {
        if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
        console.warn('[QA] GLM 失败，降级:', err.message)
        applyFallback(aiMsgId, question, major)
      },
    )
  }

  function applyFallback(aiMsgId: string, question: string, major: string) {
    const aiMsg = messages.value.find(m => m.id === aiMsgId)
    if (aiMsg) {
      aiMsg.content = findMockResponse(question, major)
      aiMsg.isStreaming = false
      aiMsg.source = '知识库匹配'
    }
    isGenerating.value = false
  }

  function stopGenerating() {
    abortController?.abort()
    abortController = null
    isGenerating.value = false
    const lastAi = [...messages.value].reverse().find(m => m.role === 'assistant' && m.isStreaming)
    if (lastAi) lastAi.isStreaming = false
  }

  function clearChat() {
    messages.value = []
  }

  /** 清空所有历史记录和当前对话（切换画像时调用） */
  function clearAll() {
    messages.value = []
    history.value = []
    saveHistory()
  }

  return { messages, history, isGenerating, sendMessage, stopGenerating, clearChat, clearAll }
})
