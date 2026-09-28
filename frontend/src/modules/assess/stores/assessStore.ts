import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AssessQuestion, AssessMode, AssessAnswer, AssessModule, LearningEvent } from '../../../shared/types'
import { chatGLM } from '../../../shared/api/glmApi'
import { buildAssessMessages } from '../prompts/assessPrompts'
import { useProfileStore } from '../../profile/stores/profileStore'
import { evaluateAdaptiveRules, type QuestionDifficulty } from '../utils/adaptiveRules'
import { buildFollowUpMessages } from '../prompts/followUpPrompts'
import { message } from 'ant-design-vue'

/* ===== 降级题库（按专业分类） ===== */

// 化学专业降级题库
const CHEMISTRY_FALLBACK: AssessQuestion[] = [
  { id: 'ch1', type: 'choice', question: '下列哪个是有机化合物的特征？', options: ['含有碳元素', '只含有碳和氢', '必须含有氧元素', '不含金属元素'], answer: 'A', explanation: '有机化合物是指含碳化合物（除CO、CO2、碳酸盐等少数简单含碳化合物外）。', difficulty: 'beginner', knowledgePoints: ['有机化学', '有机物特征'] },
  { id: 'ch2', type: 'choice', question: '乙醇的官能团是？', options: ['羧基', '羟基', '醛基', '酮基'], answer: 'B', explanation: '乙醇（C2H5OH）含有羟基（-OH）官能团，属于醇类。', difficulty: 'beginner', knowledgePoints: ['有机化学', '官能团', '醇'] },
  { id: 'ch3', type: 'fill', question: '有机化学中，-OH称为___基', answer: '羟基', explanation: '羟基（-OH）是醇类化合物的特征官能团。', difficulty: 'beginner', knowledgePoints: ['有机化学', '官能团'] },
  { id: 'ch4', type: 'choice', question: '下列反应属于取代反应的是？', options: ['乙醇燃烧', '乙醇与乙酸反应', '乙醇脱水', '乙醇氧化'], answer: 'B', explanation: '乙醇与乙酸反应生成乙酸乙酯，属于取代反应（酯化反应）。', difficulty: 'intermediate', knowledgePoints: ['有机化学', '化学反应', '取代反应'] },
  { id: 'ch5', type: 'fill', question: '有机物系统命名法中，主链碳数用___表示', answer: '天干', explanation: '主链碳数1-10用天干（甲乙丙丁戊己庚辛壬癸）表示。', difficulty: 'beginner', knowledgePoints: ['有机化学', '命名规则'] },
  { id: 'ch6', type: 'choice', question: '苯环的结构特点是？', options: ['六个碳原子形成正六边形', '碳碳键完全相同', '具有芳香性', '以上都是'], answer: 'D', explanation: '苯环是正六边形结构，碳碳键完全相同（介于单键和双键之间），具有芳香性。', difficulty: 'intermediate', knowledgePoints: ['有机化学', '苯', '芳香性'] },
  { id: 'ch7', type: 'choice', question: '酯化反应的产物是？', options: ['醇和水', '酸和水', '酯和水', '醛和水'], answer: 'C', explanation: '酯化反应：酸 + 醇 → 酯 + 水。', difficulty: 'beginner', knowledgePoints: ['有机化学', '酯化反应'] },
  { id: 'ch8', type: 'fill', question: '羧酸的官能团是___', answer: '羧基', explanation: '羧基（-COOH）是羧酸的特征官能团。', difficulty: 'beginner', knowledgePoints: ['有机化学', '官能团', '羧酸'] },
  { id: 'ch9', type: 'choice', question: '下列哪个是有机合成中常用的还原剂？', options: ['氢气/催化剂', '氧气', '氯气', '氮气'], answer: 'A', explanation: '氢气在催化剂（如Ni、Pt）作用下可还原多种有机物。', difficulty: 'intermediate', knowledgePoints: ['有机化学', '有机合成', '还原反应'] },
  { id: 'ch10', type: 'choice', question: '烷烃的通式是？', options: ['CnH2n', 'CnH2n+2', 'CnH2n-2', 'CnHn'], answer: 'B', explanation: '烷烃通式为CnH2n+2，是饱和烃。', difficulty: 'beginner', knowledgePoints: ['有机化学', '烷烃', '通式'] },
]

// 计算机专业降级题库
const CS_FALLBACK: AssessQuestion[] = [
  { id: 'cs1', type: 'choice', question: '数组随机访问的时间复杂度是？', options: ['O(1)', 'O(n)', 'O(log n)', 'O(n²)'], answer: 'A', explanation: '数组在内存中连续存储，可以通过下标直接计算地址，实现 O(1) 随机访问。', difficulty: 'beginner', knowledgePoints: ['数组', '时间复杂度'] },
  { id: 'cs2', type: 'choice', question: '链表插入操作的时间复杂度是？', options: ['O(1)', 'O(n)', 'O(log n)', 'O(n²)'], answer: 'A', explanation: '链表插入只需修改指针，不需要移动元素。', difficulty: 'beginner', knowledgePoints: ['链表', '时间复杂度'] },
  { id: 'cs3', type: 'choice', question: '栈的特点是？', options: ['先进先出', '后进先出', '随机访问', '优先级队列'], answer: 'B', explanation: '栈是后进先出 LIFO 结构。', difficulty: 'beginner', knowledgePoints: ['栈'] },
  { id: 'cs4', type: 'choice', question: '二叉搜索树的查找时间复杂度（平均）是？', options: ['O(1)', 'O(n)', 'O(log n)', 'O(n log n)'], answer: 'C', explanation: 'BST 平均查找复杂度为 O(log n)。', difficulty: 'intermediate', knowledgePoints: ['二叉搜索树', '时间复杂度'] },
  { id: 'cs5', type: 'fill', question: '二叉树的前序遍历顺序是：___、左子树、右子树', answer: '根节点', explanation: '前序遍历：根 → 左 → 右', difficulty: 'beginner', knowledgePoints: ['二叉树', '遍历'] },
  { id: 'cs6', type: 'fill', question: '队列的特点是___先进先出', answer: 'FIFO', explanation: 'FIFO = First In First Out', difficulty: 'beginner', knowledgePoints: ['队列'] },
]

// 数学专业降级题库
const MATH_FALLBACK: AssessQuestion[] = [
  { id: 'm1', type: 'choice', question: '极限 lim(x→0) sin(x)/x 的值是？', options: ['0', '1', '不存在', '∞'], answer: 'B', explanation: '这是一个重要极限，lim(x→0) sin(x)/x = 1。', difficulty: 'beginner', knowledgePoints: ['极限', '重要极限'] },
  { id: 'm2', type: 'choice', question: '导数的几何意义是？', options: ['函数值', '切线斜率', '面积', '弧长'], answer: 'B', explanation: '导数表示函数在某点的切线斜率。', difficulty: 'beginner', knowledgePoints: ['导数', '几何意义'] },
  { id: 'm3', type: 'fill', question: '∫(1/x)dx = ___ + C', answer: 'ln|x|', explanation: '1/x 的不定积分是 ln|x| + C。', difficulty: 'beginner', knowledgePoints: ['积分', '不定积分'] },
  { id: 'm4', type: 'choice', question: '矩阵乘法满足什么性质？', options: ['交换律', '结合律', '都有', '都不满足'], answer: 'B', explanation: '矩阵乘法满足结合律，但不满足交换律。', difficulty: 'intermediate', knowledgePoints: ['线性代数', '矩阵'] },
]

// 物理专业降级题库
const PHYSICS_FALLBACK: AssessQuestion[] = [
  { id: 'p1', type: 'choice', question: '牛顿第一定律又称？', options: ['加速度定律', '惯性定律', '作用反作用定律', '万有引力定律'], answer: 'B', explanation: '牛顿第一定律又称惯性定律，物体在没有外力作用下保持静止或匀速直线运动。', difficulty: 'beginner', knowledgePoints: ['力学', '牛顿定律'] },
  { id: 'p2', type: 'fill', question: '动能公式是 E_k = ___', answer: 'mv²/2', explanation: '动能 E_k = mv²/2，其中m是质量，v是速度。', difficulty: 'beginner', knowledgePoints: ['力学', '动能'] },
  { id: 'p3', type: 'choice', question: '光的折射遵循什么定律？', options: ['反射定律', '斯涅尔定律', '衍射定律', '干涉定律'], answer: 'B', explanation: '光的折射遵循斯涅尔定律：n1sinθ1 = n2sinθ2。', difficulty: 'intermediate', knowledgePoints: ['光学', '折射'] },
]

// 历史专业降级题库
const HISTORY_FALLBACK: AssessQuestion[] = [
  { id: 'h1', type: 'choice', question: '中国历史上第一个统一的封建王朝是？', options: ['夏朝', '商朝', '周朝', '秦朝'], answer: 'D', explanation: '秦朝（公元前221年）是中国历史上第一个统一的封建王朝。', difficulty: 'beginner', knowledgePoints: ['中国古代史', '秦朝'] },
  { id: 'h2', type: 'fill', question: '唐朝的建立者是___', answer: '李渊', explanation: '李渊于618年建立唐朝，定都长安。', difficulty: 'beginner', knowledgePoints: ['中国古代史', '唐朝'] },
  { id: 'h3', type: 'choice', question: '鸦片战争发生在哪一年？', options: ['1840年', '1856年', '1894年', '1900年'], answer: 'A', explanation: '1840年第一次鸦片战争爆发，标志着中国近代史的开始。', difficulty: 'beginner', knowledgePoints: ['中国近代史', '鸦片战争'] },
]

// 经济专业降级题库
const ECONOMICS_FALLBACK: AssessQuestion[] = [
  { id: 'e1', type: 'choice', question: '供给曲线向右移动表示？', options: ['供给增加', '供给减少', '需求增加', '需求减少'], answer: 'A', explanation: '供给曲线向右移动表示在相同价格下供给量增加。', difficulty: 'beginner', knowledgePoints: ['经济学', '供给'] },
  { id: 'e2', type: 'fill', question: 'GDP的全称是___', answer: '国内生产总值', explanation: 'GDP = Gross Domestic Product，国内生产总值。', difficulty: 'beginner', knowledgePoints: ['经济学', 'GDP'] },
  { id: 'e3', type: 'choice', question: '通货膨胀会导致？', options: ['货币升值', '物价上涨', '失业增加', '经济增长'], answer: 'B', explanation: '通货膨胀表现为物价普遍持续上涨。', difficulty: 'beginner', knowledgePoints: ['经济学', '通货膨胀'] },
]

// 通用降级题库（当专业不匹配时使用）
const GENERAL_FALLBACK: AssessQuestion[] = [
  { id: 'g1', type: 'choice', question: '科学方法的基本步骤包括？', options: ['观察、假设、实验、结论', '阅读、记忆、考试', '猜测、验证', '以上都不是'], answer: 'A', explanation: '科学方法：观察现象 → 提出假设 → 设计实验 → 得出结论。', difficulty: 'beginner', knowledgePoints: ['科学方法'] },
  { id: 'g2', type: 'choice', question: '逻辑推理中，演绎推理的特点是？', options: ['从特殊到一般', '从一般到特殊', '类比推理', '归纳推理'], answer: 'B', explanation: '演绎推理是从一般原理推出特殊结论的推理方法。', difficulty: 'beginner', knowledgePoints: ['逻辑推理'] },
]

// 根据专业获取对应的降级题库
function getFallbackByMajor(major: string): AssessQuestion[] {
  const majorLower = major.toLowerCase()
  
  if (majorLower.includes('化学') || majorLower.includes('材料化学')) {
    return CHEMISTRY_FALLBACK
  }
  if (majorLower.includes('有机')) {
    return CHEMISTRY_FALLBACK
  }
  if (majorLower.includes('计算机') || majorLower.includes('软件') || majorLower.includes('信息')) {
    return CS_FALLBACK
  }
  if (majorLower.includes('数学') || majorLower.includes('应用数学')) {
    return MATH_FALLBACK
  }
  if (majorLower.includes('物理') || majorLower.includes('应用物理')) {
    return PHYSICS_FALLBACK
  }
  if (majorLower.includes('历史') || majorLower.includes('考古')) {
    return HISTORY_FALLBACK
  }
  if (majorLower.includes('经济') || majorLower.includes('金融') || majorLower.includes('管理')) {
    return ECONOMICS_FALLBACK
  }
  
  // 默认使用通用题库
  return GENERAL_FALLBACK
}

export const useAssessStore = defineStore('assess', () => {
  // 模式
  const mode = ref<AssessMode | null>(null)

  // 题目
  const questions = ref<AssessQuestion[]>([])
  const currentIdx = ref(0)
  const answers = ref<AssessAnswer[]>([])

  // 计时
  const startTime = ref(0)
  const questionStartTime = ref(0)
  const questionTimeoutTriggered = ref(false)
  const elapsedSeconds = ref(0) // 每秒更新的计时器

  // 答疑
  const showQA = ref(false)
  const qaMessages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])

  // 状态
  const isGenerating = ref(false)
  const isTesting = ref(false)
  const hasReport = ref(false)

  // ===== CAT 自适应测评状态 =====
  const consecutiveCorrect = ref(0)
  const consecutiveWrong = ref(0)
  const currentDifficulty = ref<QuestionDifficulty>('intermediate')
  const adaptiveMessages = ref<string[]>([])
  const wrongKnowledgePoints = ref<string[]>([])
  const isGeneratingFollowUp = ref(false)

  const correctRate = computed(() => {
    const total = answers.value.length
    if (total === 0) return 0
    const correct = answers.value.filter(a => a.isCorrect).length
    return correct / total
  })

  // 追踪 AbortController，允许取消进行中的生成
  let assessAbortController: AbortController | null = null
  const report = ref<{
    overallScore: number
    correctCount: number
    totalCount: number
    timeUsed: number
    errorRate: number
    modules: AssessModule[]
    weakPoints: string[]
  } | null>(null)

  // Getters
  const currentQuestion = computed(() => questions.value[currentIdx.value] || null)
  const progress = computed(() => questions.value.length > 0 ? Math.round((currentIdx.value / questions.value.length) * 100) : 0)
  const isLastQuestion = computed(() => currentIdx.value >= questions.value.length - 1)

  /* ===== 解析 assess-questions 代码块 ===== */

  function parseAssessQuestions(raw: string): AssessQuestion[] | null {
    const match = raw.match(/```assess-questions\s*([\s\S]*?)```/)
    if (!match) return null
    try {
      const json = JSON.parse(match[1])
      if (!Array.isArray(json)) return null
      return json.map((q: any, i: number) => ({
        id: q.id || `q-${i + 1}`,
        type: q.type === 'fill' ? 'fill' : 'choice',
        question: q.question || '',
        options: q.options || undefined,
        answer: q.answer || '',
        explanation: q.explanation || q.explain || '',
        difficulty: q.difficulty === '基础' ? 'beginner' : q.difficulty === '中等' ? 'intermediate' : q.difficulty === '进阶' ? 'advanced' : (q.difficulty || 'intermediate'),
        knowledgePoints: q.knowledgePoints || [],
      }))
    } catch {
      // 尝试修复常见 JSON 错误（尾部逗号）
      try {
        const cleaned = match[1].replace(/,\s*([}\]])/g, '$1')
        const json = JSON.parse(cleaned)
        if (!Array.isArray(json)) return null
        return json.map((q: any, i: number) => ({
          id: q.id || `q-${i + 1}`,
          type: q.type === 'fill' ? 'fill' : 'choice',
          question: q.question || '',
          options: q.options || undefined,
          answer: q.answer || '',
          explanation: q.explanation || q.explain || '',
          difficulty: q.difficulty === '基础' ? 'beginner' : q.difficulty === '中等' ? 'intermediate' : q.difficulty === '进阶' ? 'advanced' : (q.difficulty || 'intermediate'),
          knowledgePoints: q.knowledgePoints || [],
        }))
      } catch { return null }
    }
  }

  /* ===== 选择模式 ===== */

  function selectMode(m: AssessMode) {
    mode.value = m
  }

  /* ===== 开始测评 ===== */

  function startAssess() {
    // 取消上一次未完成的生成
    if (assessAbortController) {
      assessAbortController.abort()
      assessAbortController = null
    }

    isGenerating.value = true
    startTime.value = Date.now()
    questionStartTime.value = Date.now()
    elapsedSeconds.value = 0
    questionTimeoutTriggered.value = false

    // 重置 CAT 自适应状态
    consecutiveCorrect.value = 0
    consecutiveWrong.value = 0
    currentDifficulty.value = 'intermediate'
    adaptiveMessages.value = []
    wrongKnowledgePoints.value = []
    isGeneratingFollowUp.value = false

    const profileStore = useProfileStore()
    const glmMessages = buildAssessMessages(profileStore.profileData, undefined, 10)

    // 获取用户专业，用于降级时选择相关题库
    const userMajor = profileStore.profileData.major || '通用'

    let rawContent = ''
    assessAbortController = chatGLM(
      glmMessages,
      (text: string) => { rawContent += text },
      () => {
        const parsed = parseAssessQuestions(rawContent)
        if (parsed && parsed.length >= 8) {
          questions.value = parsed.slice(0, 15)
        } else {
          // 降级：根据用户专业选择相关题库
          const fallbackQuestions = getFallbackByMajor(userMajor)
          const shuffled = [...fallbackQuestions].sort(() => Math.random() - 0.5)
          questions.value = shuffled.slice(0, Math.min(12, shuffled.length))
        }
        isGenerating.value = false
        isTesting.value = true
        currentIdx.value = 0
        answers.value = []
        questionStartTime.value = Date.now()
        elapsedSeconds.value = 0
        questionTimeoutTriggered.value = false
      },
      () => {
        // 降级：根据用户专业选择相关题库
        const fallbackQuestions = getFallbackByMajor(userMajor)
        const shuffled = [...fallbackQuestions].sort(() => Math.random() - 0.5)
        questions.value = shuffled.slice(0, Math.min(12, shuffled.length))
        isGenerating.value = false
        isTesting.value = true
        currentIdx.value = 0
        answers.value = []
        questionStartTime.value = Date.now()
        elapsedSeconds.value = 0
        questionTimeoutTriggered.value = false
      },
    )
  }

  /* ===== 提交答案 ===== */

  function submitAnswer(answer: string) {
    const question = currentQuestion.value
    if (!question) return

    let isCorrect = false

    if (question.type === 'choice') {
      isCorrect = answer.toUpperCase() === question.answer.toUpperCase()
    } else if (question.type === 'fill') {
      // 填空题：去除首尾空格，包含匹配（不区分大小写）
      const normalizedAnswer = answer.trim().toLowerCase()
      const normalizedCorrect = question.answer.trim().toLowerCase()
      isCorrect = normalizedAnswer.includes(normalizedCorrect) ||
                  normalizedCorrect.includes(normalizedAnswer)
    }

    answers.value.push({
      questionId: question.id,
      userAnswer: answer,
      isCorrect,
      timeSpent: elapsedSeconds.value,
    })

    // ===== CAT 自适应：更新计数器并评估规则 =====
    if (isCorrect) {
      consecutiveCorrect.value++
      consecutiveWrong.value = 0
    } else {
      consecutiveWrong.value++
      consecutiveCorrect.value = 0
      // 收集错误知识点
      if (question.knowledgePoints?.length) {
        for (const kp of question.knowledgePoints) {
          if (!wrongKnowledgePoints.value.includes(kp)) {
            wrongKnowledgePoints.value.push(kp)
          }
        }
      }
    }

    // 评估自适应规则
    const actions = evaluateAdaptiveRules({
      consecutiveCorrect: consecutiveCorrect.value,
      consecutiveWrong: consecutiveWrong.value,
      totalAnswered: answers.value.length,
      correctRate: correctRate.value,
      wrongKnowledgePoints: wrongKnowledgePoints.value,
      currentDifficulty: currentDifficulty.value,
    })

    for (const { action, params } of actions) {
      if (action === 'upgrade') {
        currentDifficulty.value = 'advanced'
        adaptiveMessages.value.push(params.message as string)
        message.info(params.message as string)
      } else if (action === 'downgrade') {
        currentDifficulty.value = 'beginner'
        adaptiveMessages.value.push(params.message as string)
        message.info(params.message as string)
      } else if (action === 'extend') {
        generateFollowUpQuestions(
          params.count as number,
          params.difficulty as QuestionDifficulty,
        )
      }
      // 'focus' 动作通过 extend 间接处理
    }
  }

  /** CAT: 生成追加题目 */
  async function generateFollowUpQuestions(count: number, difficulty: QuestionDifficulty) {
    if (isGeneratingFollowUp.value) return
    isGeneratingFollowUp.value = true

    const profileStore = useProfileStore()
    const existingQuestions = questions.value.map(q => q.question)
    const msgs = buildFollowUpMessages(
      profileStore.profileData,
      existingQuestions,
      count,
      difficulty,
      wrongKnowledgePoints.value.length > 0 ? wrongKnowledgePoints.value : undefined,
    )

    let rawContent = ''
    chatGLM(
      msgs,
      (text: string) => { rawContent += text },
      () => {
        const parsed = parseAssessQuestions(rawContent)
        if (parsed && parsed.length > 0) {
          questions.value.push(...parsed)
          message.info(`已追加 ${parsed.length} 道${difficulty === 'advanced' ? '进阶' : '基础'}题目 📝`)
          adaptiveMessages.value.push(`追加 ${parsed.length} 道题目（难度：${difficulty}）`)
        }
        isGeneratingFollowUp.value = false
      },
      () => {
        isGeneratingFollowUp.value = false
      },
    )
  }

  /* ===== 下一题 ===== */

  function nextQuestion() {
    if (isLastQuestion.value) {
      finishAssess()
    } else {
      currentIdx.value++
      questionStartTime.value = Date.now()
      elapsedSeconds.value = 0
      questionTimeoutTriggered.value = false
      showQA.value = false
      qaMessages.value = []
    }
  }

  /* ===== 完成测评 ===== */

  function finishAssess() {
    const timeUsed = Math.round((Date.now() - startTime.value) / 1000)
    const correctCount = answers.value.filter(a => a.isCorrect).length
    const totalCount = questions.value.length
    const errorRate = totalCount > 0 ? (totalCount - correctCount) / totalCount : 0
    const overallScore = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0

    // 按知识点统计
    const moduleStats = new Map<string, { correct: number; total: number }>()
    for (let i = 0; i < questions.value.length; i++) {
      const q = questions.value[i]
      const a = answers.value[i]
      for (const kp of q.knowledgePoints) {
        const stat = moduleStats.get(kp) || { correct: 0, total: 0 }
        stat.total++
        if (a?.isCorrect) stat.correct++
        moduleStats.set(kp, stat)
      }
    }

    // 找出薄弱点（正确率 < 50%）
    const weakPoints = Array.from(moduleStats.entries())
      .filter(([_, stat]) => stat.total > 0 && stat.correct / stat.total < 0.5)
      .map(([name]) => name)

    // 转为 AssessModule 格式（兼容 AssessChart）
    const colorMap: Record<string, string> = {
      '栈': '#34d399', '队列': '#34d399', '链表': '#00d4ff', '数组': '#00d4ff',
      '树': '#f59e0b', '二叉树': '#f59e0b', 'BST': '#f59e0b', '堆': '#f59e0b',
      '图': '#EA5455', '排序': '#22d3ee', '查找': '#22d3ee', '综合': '#a78bfa',
    }
    const modules: AssessModule[] = Array.from(moduleStats.entries()).map(([name, stat]) => ({
      name,
      score: stat.total > 0 ? Math.round((stat.correct / stat.total) * 100) : 0,
      color: colorMap[name] || '#00d4ff',
    }))

    report.value = { overallScore, correctCount, totalCount, timeUsed, errorRate, modules, weakPoints }

    isTesting.value = false
    hasReport.value = true

    // 记录错题到错题本
    recordWrongAnswers()

    // 更新画像
    const profileStore = useProfileStore()
    const allKnowledgePoints = [...new Set(questions.value.flatMap(q => q.knowledgePoints))]
    const event: LearningEvent = {
      type: 'assess_complete',
      timestamp: new Date().toISOString(),
      sourceId: `assess-${Date.now()}`,
      description: `完成测评，得分 ${overallScore}分（${correctCount}/${totalCount}题正确）`,
      knowledgePoints: allKnowledgePoints,
      score: overallScore,
    }
    profileStore.applyLearningEvent(event)

    // 错误率 >= 50% 触发降级（必须在 applyLearningEvent 之后，否则会被覆盖）
    if (errorRate >= 0.5) {
      triggerDowngrade(overallScore, weakPoints)
    }
  }

  /* ===== 触发降级资源生成 ===== */

  function triggerDowngrade(score: number, weakPoints: string[]) {
    const profileStore = useProfileStore()
    profileStore.profileChangeInfo = {
      event: {
        type: 'assess_complete',
        timestamp: new Date().toISOString(),
        sourceId: `assess-${Date.now()}`,
        description: `测评得分低(${score}分)，触发降级`,
        knowledgePoints: weakPoints,
        score,
      },
      changedDims: ['weak_points', 'base_level'],
      changeType: 'downgrade',
    }
  }

  /* ===== 答疑模式 ===== */

  function triggerQA() {
    if (questionTimeoutTriggered.value) return
    questionTimeoutTriggered.value = true
    showQA.value = true
    
    // 不添加任何消息到 qaMessages，让中央区域显示空状态提示
    qaMessages.value = []
  }

  async function sendQAMessage(message: string) {
    qaMessages.value.push({ role: 'user', content: message })

    const question = currentQuestion.value
    let questionContext = `题目：${question?.question}`
    if (question?.type === 'choice' && question?.options) {
      questionContext += `\n选项：\n${question.options.map((o, i) => `${['A', 'B', 'C', 'D'][i]}. ${o}`).join('\n')}`
    }

    const prompt = `你是学习助手。学生在做题时遇到困难，请帮助解答。

${questionContext}

学生问题：${message}

请用简洁易懂的方式解答，不要直接给出答案，而是引导学生思考。`

    let rawContent = ''
    chatGLM(
      [{ role: 'system', content: prompt }],
      (text: string) => { rawContent += text },
      () => {
        qaMessages.value.push({ role: 'assistant', content: rawContent || '让我换个方式解释...' })
      },
      () => {
        qaMessages.value.push({ role: 'assistant', content: '抱歉，网络出了点问题。你可以先跳过这道题，稍后再来复习。' })
      },
    )
  }

  function closeQA() {
    showQA.value = false
  }

  /* ===== 重置 ===== */

  function reset() {
    mode.value = null
    questions.value = []
    currentIdx.value = 0
    answers.value = []
    startTime.value = 0
    questionStartTime.value = 0
    elapsedSeconds.value = 0
    questionTimeoutTriggered.value = false
    showQA.value = false
    qaMessages.value = []
    isGenerating.value = false
    isTesting.value = false
    hasReport.value = false
    report.value = null
  }

  /* ===== 错题本 ===== */

  const WRONG_ANSWERS_KEY = 'ai_learning_wrong_answers'

  interface WrongAnswerRecord {
    questionId: string
    question: string
    type: 'choice' | 'fill'
    userAnswer: string
    correctAnswer: string
    explanation: string
    knowledgePoints: string[]
    difficulty: string
    timestamp: string
  }

  const wrongAnswers = ref<WrongAnswerRecord[]>(loadWrongAnswers())

  function loadWrongAnswers(): WrongAnswerRecord[] {
    try {
      const stored = localStorage.getItem(WRONG_ANSWERS_KEY)
      if (stored) return JSON.parse(stored)
    } catch { /* ignore */ }
    return []
  }

  function saveWrongAnswers() {
    try {
      localStorage.setItem(WRONG_ANSWERS_KEY, JSON.stringify(wrongAnswers.value.slice(-100)))
    } catch { /* ignore */ }
  }

  function recordWrongAnswers() {
    const wrongs: WrongAnswerRecord[] = []
    for (let i = 0; i < questions.value.length; i++) {
      const q = questions.value[i]
      const a = answers.value[i]
      if (a && !a.isCorrect) {
        wrongs.push({
          questionId: q.id,
          question: q.question,
          type: q.type,
          userAnswer: a.userAnswer,
          correctAnswer: q.answer,
          explanation: q.explanation,
          knowledgePoints: q.knowledgePoints,
          difficulty: q.difficulty,
          timestamp: new Date().toISOString(),
        })
      }
    }
    if (wrongs.length > 0) {
      wrongAnswers.value.push(...wrongs)
      saveWrongAnswers()
    }
  }

  function clearWrongAnswers() {
    wrongAnswers.value = []
    saveWrongAnswers()
  }

  // 按知识点统计错题
  const wrongPointsStats = computed(() => {
    const stats: Record<string, { total: number; recent: number }> = {}
    const week = 7 * 24 * 60 * 60 * 1000
    for (const w of wrongAnswers.value) {
      for (const kp of w.knowledgePoints) {
        if (!stats[kp]) stats[kp] = { total: 0, recent: 0 }
        stats[kp].total++
        if (Date.now() - new Date(w.timestamp).getTime() < week) {
          stats[kp].recent++
        }
      }
    }
    return stats
  })

  // ===== P0优化：学习效果评估状态 =====
  const learningEffectReport = ref<any>(null)
  const isGeneratingEffect = ref(false)

  async function fetchLearningEffect() {
    isGeneratingEffect.value = true
    try {
      const { getLearningEffect } = await import('../api/assessApi')
      const res = await getLearningEffect()
      if (res && res.data) {
        learningEffectReport.value = res.data
      }
    } catch (error) {
      console.error('获取学习效果评估失败:', error)
      // 降级：显示默认数据
      learningEffectReport.value = {
        overall_mastery: 0,
        learning_efficiency: 0,
        total_learning_duration: 0,
        modules: [
          { name: '文档学习', score: 0, color: '#34d399', count: 0, study_time_hours: 0 },
          { name: '视频学习', score: 0, color: '#00d4ff', count: 0, study_time_hours: 0 },
          { name: '代码实践', score: 0, color: '#a78bfa', count: 0, study_time_hours: 0 },
          { name: '练习题', score: 0, color: '#f59e0b', count: 0, study_time_hours: 0 },
        ],
        weak_points: [],
        adjustment_recommendations: [],
        strengths: ['暂无学习记录，请开始学习'],
        weaknesses: ['暂无学习数据'],
        suggestions: ['建议从基础资源开始学习', '定期回顾学习内容'],
        statistics: {
          total_resources: 0,
          completed_resources: 0,
          completion_rate: 0,
          quiz_accuracy: 0,
          streak_days: 0,
        }
      }
    } finally {
      isGeneratingEffect.value = false
    }
  }

  return {
    mode, questions, currentIdx, answers, startTime, questionStartTime,
    elapsedSeconds, questionTimeoutTriggered, showQA, qaMessages,
    isGenerating, isTesting, hasReport, report,
    currentQuestion, progress, isLastQuestion,
    // CAT 自适应
    consecutiveCorrect, consecutiveWrong, currentDifficulty,
    adaptiveMessages, wrongKnowledgePoints, correctRate,
    isGeneratingFollowUp,
    selectMode, startAssess, submitAnswer, nextQuestion, finishAssess,
    triggerQA, sendQAMessage, closeQA, reset,
    wrongAnswers, wrongPointsStats, clearWrongAnswers,
    // P0优化：学习效果评估
    learningEffectReport, isGeneratingEffect, fetchLearningEffect,
  }
})