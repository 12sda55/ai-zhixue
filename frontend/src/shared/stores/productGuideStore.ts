import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from '../../modules/auth/stores/authStore'

/** 聚光灯导览步骤配置 */
export interface TourStep {
  target: string   // data-guide 属性值
  title: string
  description: string
  icon: string
}

export const TOUR_STEPS: TourStep[] = [
  {
    target: 'nav-overview',
    title: '导航面板',
    description: '这是你的导航面板，所有功能都可以从这里快速访问。让我为你逐一介绍每个功能。',
    icon: 'menu',
  },
  {
    target: 'nav-home',
    title: '首页',
    description: '首页是你的仪表盘，可以查看学习进度、能力分布雷达图和最近的学习活动。',
    icon: 'home',
  },
  {
    target: 'nav-profile',
    title: '画像',
    description: '通过 AI 对话构建你的 8 维学习画像，画像数据驱动所有的个性化推荐。',
    icon: 'profile',
  },
  {
    target: 'nav-agent',
    title: '智能体',
    description: '7 个 AI 智能体协同为你工作：生成资源、规划路径、构建评估等。',
    icon: 'robot',
  },
  {
    target: 'nav-resource',
    title: '资源',
    description: '资源中心为你推荐个性化学习内容：视频、文档、代码练习和思维导图。',
    icon: 'book',
  },
  {
    target: 'nav-path',
    title: '路径',
    description: '根据你的画像数据，AI 生成专属学习路径，按阶段推进，跟踪进度。',
    icon: 'path',
  },
  {
    target: 'nav-qa',
    title: '答疑',
    description: '随时向 AI 提问，获得即时的、结合你画像上下文的精准解答。',
    icon: 'chat',
  },
  {
    target: 'nav-assess',
    title: '评估',
    description: '自适应测评根据你的水平调整难度，精准定位薄弱知识点并追踪提升。',
    icon: 'assess',
  },
]

const STORAGE_KEY_PREFIX = 'ai_learning_product_guide_'

export const useProductGuideStore = defineStore('productGuide', () => {
  const authStore = useAuthStore()

  // ===== 状态 =====
  const visible = ref(false)
  const phase = ref<'welcome' | 'tour' | 'done'>('welcome')
  const currentStep = ref(0)
  const completed = ref(false)

  // ===== 计算属性 =====

  /** 当前用户的 localStorage key */
  const storageKey = computed(() => {
    const userId = authStore.user?.id || 'anonymous'
    return `${STORAGE_KEY_PREFIX}${userId}_completed`
  })

  /** 是否应该显示产品引导 */
  const shouldShowGuide = computed(() => {
    return authStore.isLoggedIn && !completed.value
  })

  /** 总步骤数 */
  const totalSteps = computed(() => TOUR_STEPS.length)

  /** 是否是第一步 */
  const isFirstStep = computed(() => currentStep.value === 0)

  /** 是否是最后一步 */
  const isLastStep = computed(() => currentStep.value === totalSteps.value - 1)

  /** 当前步骤配置 */
  const currentStepConfig = computed(() => TOUR_STEPS[currentStep.value])

  // ===== 方法 =====

  /** 从 localStorage 读取完成状态 */
  function loadState() {
    const flag = localStorage.getItem(storageKey.value)
    if (flag === 'true') {
      completed.value = true
    }
  }

  /** 将完成状态写入 localStorage */
  function persistCompleted() {
    localStorage.setItem(storageKey.value, 'true')
    completed.value = true
  }

  /** 显示引导 */
  function showGuide() {
    if (completed.value) return
    phase.value = 'welcome'
    currentStep.value = 0
    visible.value = true
  }

  /** 开始聚光灯导览 */
  function startTour() {
    phase.value = 'tour'
    currentStep.value = 0
  }

  /** 下一步 */
  function nextStep() {
    if (currentStep.value < totalSteps.value - 1) {
      currentStep.value++
    }
  }

  /** 上一步 */
  function prevStep() {
    if (currentStep.value > 0) {
      currentStep.value--
    }
  }

  /** 跳过引导 */
  function skipGuide() {
    visible.value = false
    phase.value = 'done'
    persistCompleted()
  }

  /** 完成引导 */
  function completeGuide() {
    visible.value = false
    phase.value = 'done'
    persistCompleted()
  }

  /** 重置引导（用于测试） */
  function resetGuide() {
    localStorage.removeItem(storageKey.value)
    completed.value = false
    visible.value = false
    phase.value = 'welcome'
    currentStep.value = 0
  }

  return {
    visible,
    phase,
    currentStep,
    completed,
    shouldShowGuide,
    totalSteps,
    isFirstStep,
    isLastStep,
    currentStepConfig,
    TOUR_STEPS,
    loadState,
    showGuide,
    startTour,
    nextStep,
    prevStep,
    skipGuide,
    completeGuide,
    resetGuide,
  }
})
