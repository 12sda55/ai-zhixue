import type { ProfileAllDimensionKey } from '../../../shared/types'

export interface DialogueRound {
  round: number
  focusDimensions: ProfileAllDimensionKey[]
  prompt: string
  quickReplies: string[]
}

export const DIALOGUE_ROUNDS: DialogueRound[] = [
  {
    round: 1,
    focusDimensions: ['major', 'grade', 'base_level'],
    prompt: '你好！我是你的 AI 学习画像助手 🤖\n\n我将通过对话帮你构建学习画像，涵盖 8 个维度：基础水平、薄弱知识点、学习目标、学习投入度、学习节奏、内容偏好、知识掌握度、练习完成度。\n\n其中专业方向和年级水平也会采集，但不在雷达图上展示，而是体现在已采集维度中。\n\n你可以自由告诉我你的情况，我会从中提取信息。比如：你的专业、年级、基础水平、学习目标、遇到的困难等。\n\n提示词只是参考，你可以按自己的方式回答！',
    quickReplies: ['计算机科学大二，基础中等', '软件工程大三，基础较好', '我是大一新生，刚入门'],
  },
  {
    round: 2,
    focusDimensions: ['weak_points'],
    prompt: '了解了你的基础信息 ✓\n\n接下来，在学习中哪些知识点让你感到困难？可以具体描述遇到的困难。',
    quickReplies: ['树和图比较吃力', '递归总是搞不明白', '排序算法容易混淆', '指针和链表概念模糊'],
  },
  {
    round: 3,
    focusDimensions: ['study_goal', 'cognitive_style'],
    prompt: '薄弱点已记录 ✓\n\n你学习的主要目标是什么？你更偏好哪种学习方式？',
    quickReplies: ['目标：全面掌握，偏好代码实操', '目标：考试通关，偏好视频教程', '目标：项目实战，偏好理论+实践混合'],
  },
  {
    round: 4,
    focusDimensions: ['study_rhythm', 'interest_preference'],
    prompt: '目标与风格已确认 ✓\n\n你通常的学习节奏是怎样的？对哪种类型的学习内容最感兴趣？',
    quickReplies: ['每天1-2小时适中节奏，喜欢视频+实操', '碎片化学习，偏好互动练习', '周末深度沉浸，喜欢文档阅读+代码'],
  },
]

const KEYWORD_MAP: Record<string, Record<string, string[]>> = {
  major: {
    '计算机科学': ['计算机', '计科', 'cs'],
    '软件工程': ['软件', '软工', 'se'],
    '信息技术': ['信息', '信科', 'it'],
    '电子工程': ['电子', '电信', 'ee'],
    '数学': ['数学', '应数'],
  },
  grade: {
    '大一': ['大一', '新生', '刚入学'],
    '大二': ['大二'],
    '大三': ['大三'],
    '大四': ['大四', '毕业'],
    '研究生': ['研究生', '硕士', '读研'],
  },
  base_level: {
    '入门': ['入门', '零基础', '刚学', '小白', '什么都不懂'],
    '基础': ['基础', '一般', '懂一点', '了解一些', '简单'],
    '中等': ['中等', '尚可', '有一定', '学过'],
    '进阶': ['进阶', '较好', '不错', '扎实', '熟练'],
    '精通': ['精通', '很好', '很强', '深入', '优秀'],
  },
  study_goal: {
    '考试通关': ['考试', '期末', '绩点', '及格', '考研基础'],
    '竞赛提升': ['竞赛', 'acm', '蓝桥', 'leetcode', '刷题'],
    '项目实战': ['项目', '实战', '工程', '开发'],
    '全面掌握': ['全面', '系统', '精通', '全面掌握'],
    '兴趣探索': ['兴趣', '好奇', '了解', '探索'],
  },
  cognitive_style: {
    '视觉型': ['视频', '看', '图表', '图解', '动画'],
    '听觉型': ['听', '讲', '音频', '听课'],
    '实践型': ['动手', '实操', '代码', '练习', '实践', '敲代码'],
    '理论型': ['理论', '原理', '推导', '理解', '看书'],
    '混合型': ['混合', '都行', '综合', '结合'],
  },
  study_rhythm: {
    '碎片化': ['碎片', '零散', '随时', '几分钟'],
    '适中节奏': ['适中', '每天', '规律', '1-2', '一两小时', '定时'],
    '深度沉浸': ['沉浸', '集中', '周末', '长时间', '专注', '深度'],
    '突击式': ['突击', '考前', '临时', '冲刺'],
  },
  interest_preference: {
    '视频教程': ['视频', '看视频', 'b站', '网课'],
    '文档阅读': ['文档', '看书', '阅读', '文字', '博客'],
    '代码实操': ['代码', '实操', '编程', '写代码', '动手'],
    '思维导图': ['导图', '思维导图', '脑图'],
    '互动练习': ['练习', '做题', '互动', '测验'],
    '综合型': ['综合', '都行', '都要', '多种'],
  },
}

const WEAK_POINT_KEYWORDS = [
  '数据结构', '算法', '数组', '链表', '栈', '队列', '树', '二叉树', 'bst', 'avl', '红黑树',
  '图', 'bfs', 'dfs', '哈希', '散列', '排序', '快排', '归并', '冒泡',
  '查找', '搜索', '递归', '动态规划', 'dp', '贪心', '回溯', '分治',
  '堆', '优先队列', '并查集', '字典树', '线段树',
  '指针', '引用', '时间复杂度', '空间复杂度',
  '编程', '代码', '调试', 'bug', '逻辑', '思维',
]

export function extractDimension(userMsg: string, dimKey: ProfileAllDimensionKey): string | null {
  const map = KEYWORD_MAP[dimKey]
  if (!map) return null
  const msg = userMsg.toLowerCase()
  for (const [enumVal, keywords] of Object.entries(map)) {
    for (const kw of keywords) {
      if (msg.includes(kw.toLowerCase())) return enumVal
    }
  }
  return null
}

export function extractWeakPoints(userMsg: string): string[] {
  const found: string[] = []
  for (const kw of WEAK_POINT_KEYWORDS) {
    if (userMsg.toLowerCase().includes(kw.toLowerCase()) && !found.includes(kw)) {
      found.push(kw)
    }
  }
  return found
}
