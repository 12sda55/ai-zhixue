/**
 * 报告数据 composable — 汇总画像+路径+资源+测评+Agent数据
 * 根据当前专业过滤相关数据
 */

import { computed } from 'vue'
import { useProfileStore } from '../../profile/stores/profileStore'
import { usePathStore } from '../../path/stores/pathStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { useAssessStore } from '../../assess/stores/assessStore'

/** 专业关键词映射：用于判断数据是否与当前专业相关 */
const MAJOR_KEYWORDS: Record<string, string[]> = {
  '软件工程': ['软件', '编程', '代码', '算法', '数据结构', '数组', '链表', '树', '图', '排序', '查找', '栈', '队列', '递归', '动态规划', '时间复杂度', '空间复杂度', '二叉树', '哈希', '堆', '字符串', '数据库', '操作系统', '计算机网络', '软件', '工程', '面向对象', '设计模式', '测试', '架构', '前端', '后端', 'Web', 'API', 'HTTP', 'TCP', 'IP'],
  '计算机科学': ['计算机', '编程', '代码', '算法', '数据结构', '数组', '链表', '树', '图', '排序', '查找', '栈', '队列', '递归', '动态规划', '时间复杂度', '空间复杂度', '二叉树', '哈希', '堆', '字符串', '数据库', '操作系统', '计算机网络', '编译', '原理', '体系结构'],
  '物理学': ['物理', '力学', '牛顿', '动能', '势能', '能量', '动量', '加速度', '速度', '力', '电磁', '光学', '折射', '反射', '波动', '量子', '热力学', '电场', '磁场', '电路', '欧姆', '库仑'],
  '化学': ['化学', '有机', '无机', '官能团', '羟基', '羧基', '醛基', '酮基', '酯化', '取代', '加成', '氧化', '还原', '烷烃', '烯烃', '芳香', '苯', '反应速率', '化学键', '离子', '共价', '分子'],
  '数学与应用数学': ['数学', '极限', '导数', '积分', '微积分', '线性代数', '矩阵', '向量', '概率', '统计', '函数', '方程', '微分', '几何', '拓扑', '数论', '复变函数'],
  '历史学': ['历史', '朝代', '秦', '汉', '唐', '宋', '明', '清', '近代史', '鸦片战争', '辛亥革命', '五四运动', '文艺复兴', '工业革命', '世界大战'],
  '经济学': ['经济', '供给', '需求', '市场', 'GDP', '通货膨胀', '货币政策', '财政', '利率', '汇率', '投资', '消费', '生产', '成本', '利润', '边际'],
  '医学': ['医学', '解剖', '生理', '病理', '细胞', '组织', '器官', '系统', '骨骼', '肌肉', '神经', '循环', '呼吸', '消化', '免疫', '药物', '治疗'],
}

/** 判断知识点是否与当前专业相关 */
function isRelatedToMajor(knowledgePoints: string[], major: string): boolean {
  if (!major || !knowledgePoints?.length) return true // 无专业或无知识点时不过滤
  
  const keywords = MAJOR_KEYWORDS[major] || []
  if (!keywords.length) return true // 未定义的专业不过滤
  
  // 检查知识点是否包含专业关键词
  return knowledgePoints.some(kp => 
    keywords.some(kw => kp.toLowerCase().includes(kw.toLowerCase()) || kw.toLowerCase().includes(kp.toLowerCase()))
  )
}

/** 判断题目是否与当前专业相关 */
function isQuestionRelatedToMajor(question: string, knowledgePoints: string[], major: string): boolean {
  if (!major) return true
  
  const keywords = MAJOR_KEYWORDS[major] || []
  if (!keywords.length) return true
  
  // 检查题目内容或知识点
  const questionLower = question.toLowerCase()
  const hasKeywordInQuestion = keywords.some(kw => questionLower.includes(kw.toLowerCase()))
  const hasKeywordInPoints = isRelatedToMajor(knowledgePoints, major)
  
  return hasKeywordInQuestion || hasKeywordInPoints
}

export function useReportData() {
  const profileStore = useProfileStore()
  const pathStore = usePathStore()
  const resourceStore = useResourceStore()
  const assessStore = useAssessStore()

  const currentMajor = computed(() => profileStore.profileData.major)

  const profileSection = computed(() => ({
    major: profileStore.profileData.major,
    grade: profileStore.profileData.grade,
    baseLevel: profileStore.profileData.base_level,
    weakPoints: profileStore.profileData.weak_points,
    masteredPoints: profileStore.profileData.masteredPoints || [],
    dimensions: profileStore.profileData.dimensions,
    streakDays: profileStore.profileData.streakDays ?? 0,
    totalStudyMinutes: profileStore.profileData.totalStudyMinutes ?? 0,
    completedResourceCount: profileStore.profileData.completedResourceCount ?? 0,
    completedStageCount: profileStore.profileData.completedStageCount ?? 0,
    completedAssessCount: profileStore.profileData.completedAssessCount ?? 0,
    studyGoal: profileStore.profileData.study_goal,
    cognitiveStyle: profileStore.profileData.cognitive_style,
    studyRhythm: profileStore.profileData.study_rhythm,
    interestPreference: profileStore.profileData.interest_preference,
  }))

  const pathSection = computed(() => ({
    completedStages: pathStore.stages.filter(s => s.status === 'completed').length,
    activeStages: pathStore.stages.filter(s => s.status === 'active').length,
    pendingStages: pathStore.stages.filter(s => s.status === 'pending').length,
    totalProgress: pathStore.totalProgress,
    stages: pathStore.stages,
  }))

  const resourceSection = computed(() => ({
    total: resourceStore.resources.length,
    byType: resourceStore.resourcesByType,
    completed: resourceStore.resources.filter(r => r.status === 'completed').length,
  }))

  /** 根据当前专业过滤错题 */
  const assessSection = computed(() => {
    const major = currentMajor.value
    const allWrongAnswers = assessStore.wrongAnswers
    
    // 过滤与当前专业相关的错题
    const filteredWrongAnswers = major 
      ? allWrongAnswers.filter(w => 
          isQuestionRelatedToMajor(w.question, w.knowledgePoints || [], major)
        )
      : allWrongAnswers
    
    // 过滤与当前专业相关的知识点统计
    const filteredStats: Record<string, { total: number; recent: number }> = {}
    const week = 7 * 24 * 60 * 60 * 1000
    for (const w of filteredWrongAnswers) {
      for (const kp of w.knowledgePoints || []) {
        if (!filteredStats[kp]) filteredStats[kp] = { total: 0, recent: 0 }
        filteredStats[kp].total++
        if (Date.now() - new Date(w.timestamp).getTime() < week) {
          filteredStats[kp].recent++
        }
      }
    }
    
    return {
      report: assessStore.report,
      totalAssessCount: profileStore.profileData.completedAssessCount ?? 0,
      wrongAnswers: filteredWrongAnswers,
      wrongPointsStats: filteredStats,
    }
  })

  const updateHistory = computed(() => ({
    logs: profileStore.getRecentLogs(20),
    events: profileStore.getRecentEvents(30),
  }))

  return {
    profileSection,
    pathSection,
    resourceSection,
    assessSection,
    updateHistory,
  }
}