/**
 * 学习路径生成 Prompt 模板
 * 用于指导 GLM 根据用户 8 维画像生成个性化学习路径
 */

import type { ProfileData, ProfileAllDimensionKey } from '../../../shared/types'
import { DIMENSION_META } from '../../../shared/types'

/* ===== 系统指令（动态生成） ===== */

function buildSystemPrompt(profileData: ProfileData): string {
  // 优先使用当前学习科目，其次用专业
  const subject = profileData.currentSubject || profileData.major || '计算机科学'
  const major = profileData.major || '计算机科学'
  const weakPoints = profileData.weak_points || []
  
  // 根据专业确定学习领域和示例资源
  let learningDomain = '计算机核心知识'
  let exampleResources: string[] = ['数据结构与算法详解', '编程实战练习', '算法思维导图']
  
  // 专业与示例资源映射
  const majorExamples: Record<string, { domain: string; examples: string[] }> = {
    '化学': {
      domain: '化学原理与实验',
      examples: ['化学反应原理详解', '有机化学官能团性质', '化学实验操作指南', '分子结构思维导图', '化学计算练习题']
    },
    '有机化学': {
      domain: '有机化学与合成',
      examples: ['有机反应机理详解', '官能团性质总结', '有机合成路线设计', '有机物命名规则', '有机化学思维导图']
    },
    '计算机': {
      domain: '计算机科学与软件工程',
      examples: ['数据结构与算法详解', '编程语言基础教程', '操作系统原理', '计算机网络协议', '算法思维导图']
    },
    '数学': {
      domain: '数学与应用数学',
      examples: ['高等数学原理详解', '线性代数基础', '概率论与统计', '数学证明方法', '数学公式思维导图']
    },
    '物理': {
      domain: '物理学与实验',
      examples: ['力学原理详解', '电磁学基础', '光学与波动', '物理实验操作', '物理定律思维导图']
    },
    '生物': {
      domain: '生物学与实验',
      examples: ['细胞生物学详解', '遗传与进化原理', '分子生物学基础', '生物实验操作', '生物知识思维导图']
    },
    '历史': {
      domain: '历史学与文献研究',
      examples: ['中国古代史详解', '近代史重要事件', '历史文献解读', '历史时间线导图', '历史人物传记']
    },
    '经济': {
      domain: '经济学与金融',
      examples: ['微观经济学原理', '宏观经济学基础', '金融市场分析', '经济学思维导图', '经济案例分析']
    },
    '金融': {
      domain: '金融学与投资',
      examples: ['金融市场原理', '投资学基础', '风险管理', '金融案例分析', '金融知识导图']
    },
    '法律': {
      domain: '法学与法律实务',
      examples: ['民法原理详解', '刑法基础知识', '法律条文解读', '法律案例分析', '法律知识导图']
    },
    '医学': {
      domain: '医学与临床',
      examples: ['人体解剖学详解', '病理学基础', '临床诊断方法', '医学实验操作', '医学知识导图']
    },
    '教育': {
      domain: '教育学与教学法',
      examples: ['教育心理学原理', '教学方法论', '课程设计基础', '教育案例分析', '教育知识导图']
    },
    '心理': {
      domain: '心理学与应用',
      examples: ['心理学基础理论', '认知心理学', '发展心理学', '心理实验方法', '心理学导图']
    },
    '文学': {
      domain: '文学与写作',
      examples: ['文学理论详解', '写作技巧指南', '文学作品赏析', '文学史导图', '创作案例分析']
    },
    '外语': {
      domain: '外语学习与翻译',
      examples: ['语法详解教程', '词汇记忆方法', '听力训练材料', '口语练习指南', '翻译技巧导图']
    },
    '英语': {
      domain: '英语学习与应试',
      examples: ['英语语法详解', '核心词汇记忆法', '阅读理解技巧', '听力训练材料', '写作范文赏析', '英语思维导图']
    },
    '艺术': {
      domain: '艺术与设计',
      examples: ['艺术史详解', '设计原理基础', '色彩与构图', '艺术案例分析', '艺术知识导图']
    },
    '体育': {
      domain: '体育与运动科学',
      examples: ['运动生理学原理', '训练方法指南', '运动营养学', '体育案例分析', '运动知识导图']
    },
  }

  // 查找匹配的科目/专业示例
  for (const [key, value] of Object.entries(majorExamples)) {
    if (subject.includes(key) || major.includes(key)) {
      learningDomain = value.domain
      exampleResources = value.examples
      break
    }
  }
  
  // 如果有薄弱点，优先聚焦薄弱点领域
  if (weakPoints.length > 0) {
    const weakTopics = weakPoints.slice(0, 3).join('、')
    learningDomain = `${weakTopics}等薄弱知识点的突破`
    // 根据薄弱点生成示例资源
    exampleResources = weakPoints.slice(0, 3).map(wp => [
      `${wp}基础原理详解`,
      `${wp}重点难点突破`,
      `${wp}练习与测试`,
      `${wp}思维导图总结`
    ]).flat()
  }

  return `你是一个专业的学习路径规划师。你的任务是根据用户的学习画像数据，规划一条结构清晰、循序渐进的${learningDomain}学习路径。

## 输出格式

你必须输出一个 \`\`\`path-plan 代码块，内容为严格合法的 JSON，格式如下：

\`\`\`path-plan
{
  "summary": "一句话总结路径规划思路",
  "stages": [
    {
      "title": "阶段标题",
      "suggestedDays": 7,
      "reasonType": "foundation",
      "reason": "推荐理由",
      "learningTips": "学习建议，2-3句",
      "resources": [
        { "type": "document", "name": "资源名称" }
      ]
    }
  ]
}
\`\`\`

## 字段说明

- **title**: 阶段标题，简洁明确，必须与用户的当前学习科目和专业方向相关（如"${weakPoints[0] || subject}基础概念"）
- **suggestedDays**: 建议学习天数（1-30），根据基础水平和学习节奏调整
- **reasonType**: 推荐依据类型，必须是以下之一：
  - "foundation" — 基础夯实
  - "weakness" — 薄弱点突破
  - "advanced" — 进阶提升
- **reason**: 1-2 句推荐理由，关联画像维度
- **learningTips**: 该阶段的学习方法和注意事项
- **resources**: 推荐学习资源列表（每个阶段 3-5 个资源）
  - type 必须是: "document" | "mindmap" | "exercise" | "code" | "video" | "extension"
  - **name**: 资源名称，必须具体明确且与用户专业相关！

## 资源名称示例（${subject}）

以下是${subject}相关的资源名称示例，请严格参考这些格式生成具体的资源名称：

${exampleResources.map(r => `- "${r}"`).join('\n')}

**强制要求**：资源名称必须包含具体的专业知识点名称，例如：
- 正确："有机化学反应机理详解"、"官能团性质思维导图"
- 错误："练习题"、"教程"、"资料"、"学习资料"、"未命名资源"、"资源名称"

**警告**：如果资源名称为空、模糊或使用了以上禁止的名称，将导致解析失败！

## 规划规则

1. 生成 3-6 个阶段，覆盖从基础到进阶的完整学习链路
2. **重要：如果用户有薄弱知识点，必须优先安排薄弱点突破阶段，阶段标题要包含薄弱知识点名称**
3. 阶段内容必须与用户的专业方向相关，不要生成无关内容
4. 基础水平低则增加基础阶段天数，基础好则缩短基础、增加进阶
5. 资源类型要匹配认知风格和内容偏好（如偏好代码实操则多推荐 code 类型）
6. 建议天数要匹配学习节奏（碎片化→每阶段短天数，深度沉浸→长天数）
7. 学习目标影响路径终点：考试通关侧重重点考点，项目实战侧重工程应用，全面掌握覆盖所有核心知识点
8. 每个阶段 3-5 个资源，类型尽量多样但侧重用户偏好
9. 阶段之间应有逻辑递进关系

## 注意

- 只输出 path-plan 代码块和简短的自然语言路径规划说明
- 不要输出与路径无关的内容
- JSON 必须合法，不要有尾逗号或注释
- **所有阶段标题和资源名称必须与用户专业方向和薄弱点相关，禁止生成无关内容**
- **资源名称必须具体明确，禁止使用"练习题"、"教程"、"资料"等模糊名称**`
}

/* ===== 画像数据格式化 ===== */

function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []
  const dimensions = profileData.dimensions || []
  const weakPoints = profileData.weak_points || []

  const dimLines = dimensions
    .filter(d => d.value > 0)
    .map(d => {
      if (d.key === 'weak_points') {
        return `- ⚡ 薄弱知识点：${weakPoints.join('、')}（掌握度 ${d.value}/100）`
      }
      const meta = DIMENSION_META[d.key]
      return meta ? `- ${meta.icon} ${d.label}（${d.value}/100）` : `- ${d.label}（${d.value}/100）`
    })

  lines.push('## 用户画像数据')
  lines.push(dimLines.join('\n'))

  lines.push(`\n## 详细信息`)
  lines.push(`- 当前学习科目：${profileData.currentSubject || '未设置'}`)
  lines.push(`- 专业：${profileData.major || '未设置'}`)
  lines.push(`- 年级：${profileData.grade || '未设置'}`)
  lines.push(`- 基础水平：${profileData.base_level || '未设置'}`)
  if (weakPoints.length > 0) {
    lines.push(`- **薄弱知识点（重点）**：${weakPoints.join('、')}`)
  }
  lines.push(`- 学习目标：${profileData.study_goal || '未设置'}`)
  lines.push(`- 认知风格：${profileData.cognitive_style || '未设置'}`)
  lines.push(`- 学习节奏：${profileData.study_rhythm || '未设置'}`)
  lines.push(`- 内容偏好：${profileData.interest_preference || '未设置'}`)

  return lines.join('\n')
}

/* ===== 生成请求 ===== */

/**
 * 构建首次路径生成的 messages
 */
export function buildPathGenerationMessages(
  profileData: ProfileData,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const profileContext = buildProfileContext(profileData)
  const systemPrompt = buildSystemPrompt(profileData)

  // 根据用户画像确定学习重点
  const weakPoints = profileData.weak_points || []
  const subject = profileData.currentSubject || profileData.major || '计算机科学'

  let focusArea = '核心知识'
  if (weakPoints.length > 0) {
    focusArea = `薄弱知识点：${weakPoints.join('、')}`
  }

  const userPrompt = `${profileContext}

## 任务

请根据以上学习画像数据，为该用户规划一条与「${subject}」相关的学习路径。要求：
1. **最重要：路径阶段和资源必须聚焦于「${subject}」的${focusArea}，不要生成其他科目的内容**
2. 如果用户有薄弱知识点，必须优先安排薄弱点突破阶段
3. 路径阶段数和内容要贴合用户的实际水平
4. 资源推荐要匹配用户的内容偏好和「${subject}」的知识方向
5. 时间安排要适合用户的学习节奏

输出 path-plan 代码块和简要说明。`

  return [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ]
}

/**
 * 构建画像变更后重新生成路径的 messages
 */
export function buildPathRegenerationMessages(
  profileData: ProfileData,
  previousStages: { title: string; suggestedDays: number; reason: string; resources: { type: string; name: string }[] }[],
  changeDescription: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const profileContext = buildProfileContext(profileData)
  const systemPrompt = buildSystemPrompt(profileData)

  const prevSummary = previousStages.map((s, i) =>
    `${i + 1}. ${s.title}（${s.suggestedDays}天）— ${s.reason}`
  ).join('\n')

  const weakPoints = profileData.weak_points || []
  const subject = profileData.currentSubject || profileData.major || '计算机科学'
  const focusArea = weakPoints.length > 0 ? `${subject}的薄弱知识点：${weakPoints.join('、')}` : `${subject}的核心知识`

  // 检测是否包含科目切换
  const isSubjectChange = changeDescription.includes('当前学习科目') || changeDescription.includes('科目切换')

  const subjectChangeInstruction = isSubjectChange
    ? `\n**⚠️ 重要：检测到科目切换！当前科目为「${subject}」，必须完全删除旧科目的所有阶段和资源，重新生成与「${subject}」相关的全新路径。不要保留任何旧科目的阶段！**`
    : ''

  const userPrompt = `${profileContext}

## 用户画像变更

${changeDescription}${subjectChangeInstruction}

## 当前路径

${prevSummary}

## 任务

用户画像发生了变更，请根据最新的画像数据调整学习路径。要求：
1. **最重要：调整后的路径必须聚焦于${focusArea}，删除无关的阶段**
2. 如果新增了薄弱知识点，必须增加对应的突破阶段
3. 尽量保留仍然合理的阶段，只调整受影响的部分
4. 如果基础水平变化，调整各阶段天数
5. 如果学习目标或偏好变化，调整资源推荐
6. 输出完整的新路径（不是增量）
7. **所有阶段标题和资源名称必须与当前科目「${subject}」相关**

输出 path-plan 代码块和变更说明。`

  return [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ]
}

/**
 * 生成画像变更描述
 */
export function buildChangeDescription(
  oldData: ProfileData,
  newData: ProfileData,
): string {
  const changes: string[] = []

  // 检测科目切换（优先级最高）
  const oldSubject = oldData.currentSubject || ''
  const newSubject = newData.currentSubject || ''
  if (oldSubject !== newSubject) {
    changes.push(`当前学习科目切换：${oldSubject || '未设置'} → ${newSubject || '未设置'}`)
  }

  const dimKeys: ProfileAllDimensionKey[] = [
    'major', 'grade', 'base_level', 'study_goal',
    'cognitive_style', 'study_rhythm', 'interest_preference',
    'learning_engagement', 'knowledge_mastery', 'exercise_completion',
  ]

  for (const key of dimKeys) {
    const oldVal = (oldData as any)[key]
    const newVal = (newData as any)[key]
    if (oldVal !== newVal) {
      const name = DIMENSION_META[key].name
      changes.push(`${name}：${oldVal} → ${newVal}`)
    }
  }

  const oldWeak = oldData.weak_points.join('、')
  const newWeak = newData.weak_points.join('、')
  if (oldWeak !== newWeak) {
    changes.push(`薄弱知识点：${oldWeak || '无'} → ${newWeak || '无'}`)
  }

  return changes.length > 0 ? changes.join('\n') : '画像有微调'
}