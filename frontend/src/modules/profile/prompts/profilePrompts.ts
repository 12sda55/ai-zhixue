/**
 * 画像提取 Prompt 模板
 * 用于指导 GLM 从用户对话中提取画像数据
 */

import type { ProfileAllDimensionKey } from '../../../shared/types'

/* ===== 系统指令（所有请求共用） ===== */

const SYSTEM_PROMPT = `你是一个学习画像提取助手。你的任务是从用户的对话中提取学习画像数据，并以严格的代码块格式输出。

## 维度定义与可选值

### 雷达图维度（8维，显示在学习画像雷达图上）
1. **base_level（基础水平）**：入门 | 基础 | 中等 | 进阶 | 精通
2. **weak_points（薄弱知识点）**：自由文本，多个用逗号分隔（如：有机化学,物理化学,分析化学）
3. **study_goal（学习目标）**：考试通关 | 竞赛提升 | 项目实战 | 全面掌握 | 兴趣探索 | 考研备考 | 求职准备
4. **learning_engagement（学习投入度）**：不提取，由系统自动计算
5. **study_rhythm（学习节奏）**：碎片化 | 适中节奏 | 深度沉浸 | 突击式
6. **interest_preference（内容偏好）**：视频教程 | 文档阅读 | 代码实操 | 思维导图 | 互动练习 | 实验操作 | 综合型
7. **knowledge_mastery（知识掌握度）**：不提取，由系统自动计算
8. **exercise_completion（练习完成度）**：不提取，由系统自动计算

### 非雷达维度（仅存储在已采集维度中，不在雷达图上显示）
9. **major（专业方向）**：
   - **工学类**：计算机科学 | 软件工程 | 信息技术 | 电子工程 | 电气工程 | 自动化 | 机械工程 | 土木工程 | 建筑学 | 材料科学与工程 | 环境工程 | 化学工程 | 生物工程 | 航空航天工程 | 交通运输 | 工业工程
   - **理学类**：数学与应用数学 | 物理学 | 化学 | 天文学 | 地理学 | 大气科学 | 海洋科学 | 地球物理学 | 地质学 | 生物科学 | 心理学 | 统计学
   - **文学类**：汉语言文学 | 外国语言文学 | 英语 | 日语 | 法语 | 德语 | 俄语 | 西班牙语 | 翻译 | 新闻传播学 | 广告学 | 编辑出版学
   - **历史类**：历史学 | 世界史 | 考古学 | 博物馆学 | 文物保护技术
   - **哲学类**：哲学 | 逻辑学 | 伦理学 | 宗教学
   - **经济管理类**：经济学 | 金融学 | 国际经济与贸易 | 会计学 | 工商管理 | 市场营销 | 人力资源管理 | 财务管理 | 公共管理 | 行政管理 | 信息管理与信息系统 | 电子商务
   - **法学类**：法学 | 政治学 | 社会学 | 国际政治 | 外交学 | 社会工作
   - **教育学类**：教育学 | 学前教育 | 小学教育 | 特殊教育 | 体育教育 | 运动训练
   - **医学类**：临床医学 | 基础医学 | 口腔医学 | 公共卫生与预防医学 | 中医学 | 护理学 | 药学 | 医学影像学 | 康复医学
   - **农学类**：农学 | 园艺 | 植物保护 | 动物科学 | 动物医学 | 林学 | 水产养殖
   - **艺术类**：音乐学 | 音乐表演 | 作曲与作曲技术理论 | 舞蹈学 | 舞蹈表演 | 美术学 | 绘画 | 雕塑 | 设计学 | 视觉传达设计 | 环境设计 | 产品设计 | 数字媒体艺术 | 动画 | 戏剧影视文学 | 广播电视编导 | 播音与主持艺术
   - **其他**：如果用户的专业不在以上列表中，可以直接使用用户提供的专业名称

   - **重要**：如果用户明确说出专业名称，必须使用用户说的具体专业名称，不要笼统归类为"其他"！
10. **grade（年级水平）**：大一 | 大二 | 大三 | 大四 | 研究生 | 博士生 | 其他
11. **cognitive_style（认知风格）**：视觉型 | 听觉型 | 实践型 | 理论型 | 混合型
12. **currentSubject（当前学习科目）**：自由文本，从用户对话中推断用户正在学习的科目。**这是最重要的维度之一，必须优先提取！** 只要用户提到任何与学习、课程、科目相关的内容，就必须提取。例如：用户说"学英语动词"→currentSubject:英语，用户说"高数挂了"→currentSubject:高等数学，用户说"在学Python"→currentSubject:Python编程，用户说"准备考研政治"→currentSubject:政治。不要局限于计算机类科目，任何学科都可以！

## 输出格式

你必须输出一个 \`\`\`profile-update 代码块，格式为：
\`\`\`profile-update
维度key:值|维度key:值|...
\`\`\`

示例：
\`\`\`profile-update
major:化学|grade:大二|base_level:中等|weak_points:有机化学,物理化学
\`\`\`

## 规则

- 只输出你能从用户对话中**确定**提取到的维度，不确定的不输出
- **major 维度**：必须使用用户明确说的专业名称，从上述专业列表中选择最匹配的，或直接使用用户提供的名称
- 枚举维度的值必须是上面列出的可选值之一（major除外，可使用用户提供的具体名称）
- weak_points 可以是任意知识点名称，多个用英文逗号分隔
- learning_engagement、knowledge_mastery、exercise_completion 不需要提取，它们由系统根据学习行为自动计算
- 除了代码块，你还需要用自然语言总结提取到的信息
- **重要**：用户可以自由表达，不要强制引导。如果用户提供了信息就提取，如果没有提供就友好询问
- 语气友好、自然，像朋友聊天而非审问
- 当所有可提取维度都收集完成后，输出 profile-summary 代码块并请用户确认`

/* ===== 构建当前画像上下文 ===== */

function buildProfileContext(profileData: {
  dimensions: { key: ProfileAllDimensionKey; value: number; label: string }[]
  weak_points: string[]
  major: string
  grade: string
  base_level: string
  study_goal: string
  cognitive_style: string
  study_rhythm: string
  interest_preference: string
}): string {
  const dimensions = profileData.dimensions || []
  const weakPoints = profileData.weak_points || []
  const filled = dimensions
    .filter(d => d.value > 0)
    .map(d => {
      const val = d.key === 'weak_points' ? weakPoints.join(',') : d.label
      return `${d.key}:${val}`
    })
    .join('|')

  if (!filled) return '（画像尚未建立，这是首次对话）'
  return `当前已有画像数据：\n\`\`\`profile-update\n${filled}\n\`\`\``
}

/**
 * 构建未收集维度的提示
 */
function buildMissingDimensionsPrompt(profileData: any): string {
  const missing: string[] = []
  const dimNames: Record<ProfileAllDimensionKey, string> = {
    major: '专业方向',
    grade: '年级水平',
    base_level: '基础水平',
    weak_points: '薄弱知识点',
    study_goal: '学习目标',
    cognitive_style: '认知风格',
    study_rhythm: '学习节奏',
    interest_preference: '内容偏好',
    learning_engagement: '学习投入度',
    knowledge_mastery: '知识掌握度',
    exercise_completion: '练习完成度',
  }

  for (const dim of profileData.dimensions) {
    // 跳过自动计算的维度
    if (dim.key === 'learning_engagement' || dim.key === 'knowledge_mastery' || dim.key === 'exercise_completion') continue
    if (dim.value === 0) {
      missing.push(dimNames[dim.key as ProfileAllDimensionKey] || dim.name)
    }
  }

  if (missing.length === 0) {
    return '所有可提取维度已收集完成，请输出 profile-summary 代码块并请用户确认画像。'
  }
  return `尚未收集的维度：${missing.join('、')}。如果用户没有提到这些，可以友好询问。`
}

/**
 * 构建初始提取请求的 messages
 * 改为灵活提取模式，不再强制按轮次引导
 */
export function buildInitialMessages(
  round: number,
  userMessage: string,
  profileData: any,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const existingProfile = buildProfileContext(profileData)
  const missingPrompt = buildMissingDimensionsPrompt(profileData)

  const userPrompt = `## 当前状态
- ${existingProfile}
- ${missingPrompt}

## 用户最新回答
${userMessage}

请从用户的回答中提取画像维度，输出 profile-update 代码块，并用自然语言总结提取结果。如果用户提供了新的信息就提取并确认；如果用户在提问或表达其他内容，请自然回应，同时可以友好询问未收集的维度。`

  return [
    { role: 'system', content: SYSTEM_PROMPT },
    { role: 'user', content: userPrompt },
  ]
}

/**
 * 构建补充/修改请求的 messages
 */
export function buildSupplementMessages(
  userMessage: string,
  profileData: any,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const existingProfile = buildProfileContext(profileData)

  const supplementSystem = SYSTEM_PROMPT + `\n\n## 补充说明
用户已确认画像，现在想修改或补充某些维度。

**重要交互规则：**
1. 提取用户输入中的维度变更，输出 profile-update 代码块
2. 如果用户切换了科目（如从"数据结构"切换到"英语"），必须追问该科目的基础水平、薄弱知识点、学习目标等关键维度
3. 对于新科目，用户可能还没提供足够信息，你要主动询问，就像第一次构建画像那样引导式提问
4. 回复要自然、友好，像学习顾问一样引导用户补充信息，不要只机械地输出变更结果
5. 如果用户提供了新的薄弱知识点，追问具体困难点
6. 回复末尾可以给出1-2个引导性问题，帮助用户完善画像`

  const userPrompt = `## 当前画像
${existingProfile}

## 用户修改请求
${userMessage}

请提取用户想修改的维度和新值，输出 profile-update 代码块。同时根据用户输入判断是否需要追问更多信息。`

  return [
    { role: 'system', content: supplementSystem },
    { role: 'user', content: userPrompt },
  ]
}

/**
 * 构建确认阶段的 messages（所有维度收集完成后）
 */
export function buildSummaryMessages(
  profileData: any,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const existingProfile = buildProfileContext(profileData)

  const userPrompt = `## 当前画像
${existingProfile}

所有可提取维度已收集完成。请用自然语言总结完整的学习画像（包括雷达图维度和非雷达维度），并输出 profile-summary 代码块。格式同 profile-update，但使用 \`\`\`profile-summary 标记。注意：knowledge_mastery、exercise_completion、learning_engagement 是由系统自动计算的，不需要包含在 summary 中。最后提醒用户确认或修改。`

  return [
    { role: 'system', content: SYSTEM_PROMPT },
    { role: 'user', content: userPrompt },
  ]
}
