import type {
  ProfileData, ProfileDimensionKey, ProfileAllDimensionKey,
} from '../../../shared/types'
import { DIMENSION_META } from '../../../shared/types'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'

/** 清理画像数据中的跨科目污染（在从后端/localStorage 加载后调用） */
export function cleanContaminatedData(data: ProfileData): ProfileData {
  const currentSubject = data.currentSubject || ''
  data.weak_points = filterRelevantWeakPoints(data.weak_points || [], currentSubject)
  for (const ov of (data.subjectOverlays || [])) {
    ov.weak_points = filterRelevantWeakPoints(ov.weak_points || [], ov.subject || '')
  }
  return data
}

/** 迁移旧维度结构到新维度结构 */
export function migrateDimensions(data: ProfileData) {
  if (!data.dimensions || !Array.isArray(data.dimensions)) return

  const existingKeys = new Set(data.dimensions.map(d => d.key))

  const radarKeys: ProfileDimensionKey[] = [
    'base_level', 'weak_points', 'study_goal', 'learning_engagement',
    'study_rhythm', 'interest_preference', 'knowledge_mastery', 'exercise_completion',
  ]
  const nonRadarKeys: ProfileAllDimensionKey[] = ['major', 'grade', 'cognitive_style']
  const allNewKeys = [...radarKeys, ...nonRadarKeys]

  for (const key of allNewKeys) {
    if (!existingKeys.has(key)) {
      data.dimensions.push({
        key,
        name: DIMENSION_META[key].name,
        value: 0,
        label: key === 'knowledge_mastery' ? '待学习'
          : key === 'exercise_completion' ? '待练习'
          : key === 'learning_engagement' ? '待评估'
          : '待确定',
        color: DIMENSION_META[key].color,
        showOnRadar: DIMENSION_META[key].showOnRadar,
        baseScore: 0,
        bonus: 0,
      })
    } else {
      const dim = data.dimensions.find(d => d.key === key)
      if (dim && dim.showOnRadar === undefined) {
        dim.showOnRadar = DIMENSION_META[key]?.showOnRadar ?? true
      }
      if (dim && dim.baseScore === undefined) {
        dim.baseScore = dim.value || 0
        dim.bonus = 0
      }
    }
  }
}

export function createEmptyProfile(): ProfileData {
  const radarKeys: ProfileDimensionKey[] = [
    'base_level', 'weak_points', 'study_goal', 'learning_engagement',
    'study_rhythm', 'interest_preference', 'knowledge_mastery', 'exercise_completion',
  ]
  const nonRadarKeys: ProfileAllDimensionKey[] = ['major', 'grade', 'cognitive_style']

  const allKeys = [...radarKeys, ...nonRadarKeys]

  return {
    dimensions: allKeys.map(key => ({
      key,
      name: DIMENSION_META[key].name,
      value: 0,
      label: key === 'knowledge_mastery' ? '待学习'
        : key === 'exercise_completion' ? '待练习'
        : key === 'learning_engagement' ? '待评估'
        : '待确定',
      color: DIMENSION_META[key].color,
      showOnRadar: DIMENSION_META[key].showOnRadar,
      baseScore: 0,
      bonus: 0,
    })),
    major: '',
    grade: '',
    base_level: '',
    weak_points: [],
    study_goal: '',
    cognitive_style: '',
    study_rhythm: '',
    interest_preference: '',
    phase: 'initial',
    dialogueRound: 0,
    updateLogs: [],
    learningEvents: [],
    lastUpdatedAt: new Date().toISOString(),
    masteredPoints: [],
    totalStudyMinutes: 0,
    streakDays: 0,
    completedResourceCount: 0,
    completedStageCount: 0,
    completedAssessCount: 0,
    knowledge_mastery: 0,
    exercise_completion: 0,
    learning_engagement: 0,
  }
}

const SUBJECT_KEYWORD_MAP_MIGRATION: Record<string, string[]> = {
  '数据结构': ['数组', '链表', '栈', '队列', '树', '二叉树', '图', '哈希', '堆', '并查集', '字典树', '线段树', '散列表', '红黑树', 'AVL', 'B树'],
  '算法': ['排序', '查找', '递归', '动态规划', '贪心', '回溯', '分治', '时间复杂度', '空间复杂度'],
  '操作系统': ['进程', '线程', '内存管理', '调度', '死锁', '文件系统', '虚拟内存', '分页', '信号量'],
  '计算机网络': ['TCP', 'UDP', 'HTTP', 'IP', '路由', 'DNS', '套接字', '三次握手', '四次挥手'],
  '数据库': ['SQL', '索引', '事务', '锁', '范式', 'ER图', '关系模型'],
  '编译原理': ['词法分析', '语法分析', '语义分析', '中间代码', 'AST'],
  '计算机组成': ['CPU', '总线', '指令集', '流水线', '缓存', '寄存器'],
  '离散数学': ['集合', '逻辑', '命题', '谓词', '关系', '函数', '图论', '组合'],
  '线性代数': ['矩阵', '向量', '行列式', '特征值', '线性变换'],
  '概率论': ['概率', '随机变量', '分布', '期望', '方差', '贝叶斯'],
  '英语': ['英语', '动词', '名词', '形容词', '语法', '时态', '从句', '单词', '词汇', '阅读理解', '完形填空', '翻译', '写作', '听力', '口语', '虚拟语气', '被动语态', '非谓语', '定语从句', '状语从句', '宾语从句', '主语从句'],
  '日语': ['日语', '五十音', '助词', '动词变形', '敬语', '片假名', '平假名', '汉字', 'N1', 'N2', 'N3'],
  '高等数学': ['极限', '导数', '积分', '微积分', '微分', '泰勒', '洛必达', '中值定理', '不定积分', '定积分', '级数'],
  '大学物理': ['力学', '电磁学', '光学', '热学', '量子', '相对论', '波动', '电场', '磁场', '电路'],
  '政治': ['马原', '毛概', '思政', '政治经济学', '科学社会主义', '时事', '近现代史', '思修'],
}

export function inferSubjectForMigration(data: ProfileData): string {
  if (data.currentSubject) return data.currentSubject

  const weakPoints = data.weak_points?.length > 0 ? data.weak_points : []

  for (const [subject, keywords] of Object.entries(SUBJECT_KEYWORD_MAP_MIGRATION)) {
    if (weakPoints.some(wp =>
      keywords.some(kw => wp.toLowerCase().includes(kw.toLowerCase()) || kw.toLowerCase().includes(wp.toLowerCase()))
    )) {
      return subject
    }
  }

  const major = data.major || ''
  if (major.includes('计算机') || major.includes('软件') || major.includes('信息')) return '数据结构'
  if (major.includes('数学')) return '离散数学'
  if (major.includes('外语') || major.includes('英语') || major.includes('文学')) return '英语'
  if (major.includes('物理')) return '大学物理'

  if (weakPoints.length > 0) return weakPoints[0]

  return ''
}
