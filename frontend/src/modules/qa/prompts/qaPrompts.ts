/**
 * 智能答疑 Prompt 模板
 * 根据用户画像调整回答策略
 */

import type { ProfileData } from '../../../shared/types'

function buildSystemPrompt(major: string): string {
  // 根据专业确定学科领域
  const subjectMap: Record<string, string> = {
    '计算机科学': '计算机科学与编程',
    '软件工程': '软件工程与系统设计',
    '信息技术': '信息技术与网络',
    '电子工程': '电子工程与电路',
    '电气工程': '电气工程与电力系统',
    '自动化': '自动化与控制工程',
    '机械工程': '机械工程与力学',
    '土木工程': '土木工程与建筑',
    '建筑学': '建筑设计与城市规划',
    '数学与应用数学': '数学与应用数学',
    '物理学': '物理学与力学',
    '化学': '化学与分子科学',
    '生物科学': '生物科学与生命科学',
    '天文学': '天文学与宇宙科学',
    '地理学': '地理学与地球科学',
    '心理学': '心理学与认知科学',
    '统计学': '统计学与数据分析',
    '经济学': '经济学与金融',
    '金融学': '金融学与投资',
    '会计学': '会计学与财务管理',
    '工商管理': '工商管理与企业运营',
    '法学': '法学与法律实务',
    '医学': '医学与临床科学',
    '临床医学': '临床医学与诊断',
    '药学': '药学与药物科学',
    '护理学': '护理学与护理实践',
    '教育学': '教育学与教学法',
    '体育教育': '体育教育与运动科学',
    '汉语言文学': '汉语言文学与文学研究',
    '英语': '英语语言学习与翻译',
    '历史学': '历史学与历史研究',
    '哲学': '哲学与逻辑思维',
    '音乐学': '音乐学与音乐理论',
    '美术学': '美术学与艺术创作',
    '设计学': '设计学与创意设计',
    '农学': '农学与农业科学',
    '林学': '林学与森林科学',
  }
  
  const subject = subjectMap[major] || major || '通用学科知识'
  
  return `你是一个${subject}领域的答疑专家。你的任务是根据学生的学习画像，提供个性化的答疑回答。

## 回答策略

根据用户的画像数据调整回答方式：

1. **基础水平**：
   - 入门/基础 → 用通俗语言，多用类比和日常例子，避免过多术语
   - 中等 → 适度使用术语，配合示例和公式
   - 进阶/精通 → 可以深入理论分析，讨论复杂概念

2. **薄弱知识点**：
   - 如果问题涉及用户的薄弱点，提供额外的详细解释和多个示例
   - 主动指出常见误区和易错点
   - 针对薄弱点给出专项练习建议

3. **认知风格**：
   - 视觉型 → 多描述图示、动画过程，用"想象一下"引导
   - 实践型 → 优先给实验/操作示例，边做边学
   - 理论型 → 先讲原理和推导，再给应用
   - 听觉型 → 用对话式语气，逐步引导思考
   - 混合型 → 综合使用以上方式

4. **学习目标**：
   - 考试通关 → 强调考点、常见题型、易考细节
   - 竞赛提升 → 给出竞赛难度题目和解题技巧
   - 项目实战 → 结合实际应用场景
   - 全面掌握 → 系统讲解，补充扩展知识
   - 考研备考 → 强调考研重点、真题分析、复习策略
   - 求职准备 → 结合面试考点、实际工作场景

5. **专业相关性**：
   - 回答必须与用户的专业方向相关
   - 如果用户是${major}专业，回答应该结合${subject}的知识体系
   - 不要回答与用户专业无关的内容

## 输出格式

用 Markdown 格式回答，可以包含：
- 公式（LaTeX 格式，如 $E=mc^2$）
- 代码块（如 Python、C++、MATLAB 等）
- 表格对比
- 重点加粗
- 引用块（提示/注意）
- 思维导图结构（如需要）

保持回答简洁但完整，一般 200-500 字。如果问题复杂，分点说明。`
}

function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []

  const filled = profileData.dimensions.filter(d => d.value > 0)
  if (filled.length === 0) return '（画像尚未建立）'

  lines.push(`- 专业：${profileData.major}，年级：${profileData.grade}，基础：${profileData.base_level}`)
  if (profileData.weak_points.length > 0) {
    lines.push(`- 薄弱知识点：${profileData.weak_points.join('、')}`)
  }
  lines.push(`- 学习目标：${profileData.study_goal}`)
  lines.push(`- 认知风格：${profileData.cognitive_style}，偏好：${profileData.interest_preference}`)

  return lines.join('\n')
}

/**
 * 构建答疑请求的 messages
 */
export function buildQAMessages(
  userQuestion: string,
  profileData: ProfileData,
  chatHistory?: { role: 'user' | 'assistant'; content: string }[],
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const profileContext = buildProfileContext(profileData)
  const systemPrompt = buildSystemPrompt(profileData.major || '通用学科')

  const userPrompt = `## 当前学生画像
${profileContext}

## 学生提问
${userQuestion}

请根据学生的画像数据和专业方向，提供个性化的答疑回答。回答必须与学生的专业相关！`

  const messages: { role: 'system' | 'user' | 'assistant'; content: string }[] = [
    { role: 'system', content: systemPrompt },
  ]

  // 加入历史对话（最近 10 轮）
  if (chatHistory && chatHistory.length > 0) {
    const recent = chatHistory.slice(-20)
    for (const msg of recent) {
      messages.push(msg)
    }
  }

  messages.push({ role: 'user', content: userPrompt })

  return messages
}
