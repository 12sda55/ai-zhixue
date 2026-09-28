/**
 * 评估测评 Prompt 模板
 * 根据用户画像生成个性化题目
 */

import type { ProfileData } from '../../../shared/types'

function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []
  const filled = profileData.dimensions.filter(d => d.value > 0)
  if (filled.length === 0) return '（画像尚未建立）'

  lines.push(`- 专业：${profileData.major}，年级：${profileData.grade}，基础：${profileData.base_level}`)
  if (profileData.weak_points.length > 0) {
    lines.push(`- 薄弱知识点：${profileData.weak_points.join('、')}`)
  }
  lines.push(`- 学习目标：${profileData.study_goal}`)
  return lines.join('\n')
}

// 根据用户专业确定出题领域
function getDomainFromMajor(major: string): string {
  const majorLower = major.toLowerCase()
  
  // 计算机网络相关专业
  if (majorLower.includes('网络') || majorLower.includes('通信') || majorLower.includes('信息安全')) {
    return '计算机网络、HTTP协议、TCP/IP、网络安全、路由交换'
  }
  
  // 软件工程相关专业
  if (majorLower.includes('软件') || majorLower.includes('计算机科学') || majorLower.includes('计算机')) {
    return '数据结构、算法、软件工程、编程语言'
  }
  
  // 数据科学相关专业
  if (majorLower.includes('数据') || majorLower.includes('统计') || majorLower.includes('大数据')) {
    return '数据分析、统计学、机器学习、数据可视化'
  }
  
  // 人工智能相关专业
  if (majorLower.includes('人工智能') || majorLower.includes('ai') || majorLower.includes('智能')) {
    return '机器学习、深度学习、自然语言处理、计算机视觉'
  }
  
  // 电子信息相关专业
  if (majorLower.includes('电子') || majorLower.includes('电气') || majorLower.includes('自动化')) {
    return '电路分析、信号处理、嵌入式系统、控制理论'
  }
  
  // 机械工程相关专业
  if (majorLower.includes('机械') || majorLower.includes('车辆') || majorLower.includes('工业')) {
    return '机械设计、工程力学、材料科学、制造工艺'
  }
  
  // 经济管理相关专业
  if (majorLower.includes('经济') || majorLower.includes('金融') || majorLower.includes('管理') || majorLower.includes('会计') || majorLower.includes('商')) {
    return '经济学原理、财务管理、市场营销、企业管理'
  }
  
  // 法律相关专业
  if (majorLower.includes('法律') || majorLower.includes('法学')) {
    return '宪法、民法、刑法、行政法、法律实务'
  }
  
  // 历史相关专业
  if (majorLower.includes('历史') || majorLower.includes('考古')) {
    return '中国古代史、中国近现代史、世界史、史学理论'
  }
  
  // 文学相关专业
  if (majorLower.includes('文学') || majorLower.includes('中文') || majorLower.includes('汉语言')) {
    return '中国古代文学、现代文学、文学理论、语言学'
  }
  
  // 外语相关专业
  if (majorLower.includes('英语') || majorLower.includes('外语') || majorLower.includes('翻译') || majorLower.includes('日语') || majorLower.includes('法语')) {
    return '语言语法、翻译技巧、文学阅读、跨文化交际'
  }
  
  // 教育相关专业
  if (majorLower.includes('教育') || majorLower.includes('师范') || majorLower.includes('心理')) {
    return '教育学原理、心理学、教学法、教育心理学'
  }
  
  // 医学相关专业
  if (majorLower.includes('医学') || majorLower.includes('临床') || majorLower.includes('护理') || majorLower.includes('药学')) {
    return '基础医学、临床医学、病理学、药理学'
  }
  
  // 数学相关专业
  if (majorLower.includes('数学') || majorLower.includes('应用数学')) {
    return '高等数学、线性代数、概率论、数学分析'
  }
  
  // 物理相关专业
  if (majorLower.includes('物理') || majorLower.includes('应用物理')) {
    return '力学、电磁学、光学、量子物理'
  }
  
  // 化学相关专业
  if (majorLower.includes('化学') || majorLower.includes('材料化学')) {
    return '无机化学、有机化学、分析化学、物理化学'
  }
  
  // 生物相关专业
  if (majorLower.includes('生物') || majorLower.includes('生命科学')) {
    return '细胞生物学、遗传学、生态学、分子生物学'
  }
  
  // 环境相关专业
  if (majorLower.includes('环境') || majorLower.includes('生态')) {
    return '环境科学、生态学、环境工程、可持续发展'
  }
  
  // 建筑相关专业
  if (majorLower.includes('建筑') || majorLower.includes('土木') || majorLower.includes('城市规划')) {
    return '建筑设计、结构力学、城市规划、建筑历史'
  }
  
  // 艺术相关专业
  if (majorLower.includes('艺术') || majorLower.includes('设计') || majorLower.includes('美术') || majorLower.includes('音乐')) {
    return '艺术史、设计原理、美学理论、艺术创作'
  }
  
  // 新闻传播相关专业
  if (majorLower.includes('新闻') || majorLower.includes('传播') || majorLower.includes('媒体') || majorLower.includes('广告')) {
    return '新闻学、传播学、媒体研究、广告学'
  }
  
  // 体育相关专业
  if (majorLower.includes('体育') || majorLower.includes('运动')) {
    return '运动生理学、体育训练、运动心理学、体育管理'
  }
  
  // 农业相关专业
  if (majorLower.includes('农业') || majorLower.includes('农学') || majorLower.includes('园艺') || majorLower.includes('林业')) {
    return '植物学、作物栽培、农业经济、农业技术'
  }
  
  // 如果专业名称不匹配任何预设领域，使用专业名称本身作为出题领域
  if (major && major.length > 0) {
    return `${major}专业知识、核心理论、应用实践`
  }
  
  // 默认：通用知识
  return '通用知识、逻辑推理、基础知识'
}

// 根据用户薄弱点确定重点考查内容
function getFocusFromWeakPoints(weakPoints: string[]): string {
  if (weakPoints.length === 0) return ''
  return `**重点考查薄弱知识点：${weakPoints.join('、')}**，这些内容必须占题目总数的 40% 以上！`
}

function buildAssessSystemPrompt(profileData: ProfileData): string {
  const domain = getDomainFromMajor(profileData.major)
  const focusHint = getFocusFromWeakPoints(profileData.weak_points)
  
  return `你是一个专业的教育测评出题专家。根据学生的学习画像生成个性化测评题目。

## 出题领域
根据用户专业方向，题目应聚焦于：${domain}

## 重点考查
${focusHint || '根据用户基础水平合理分布题目难度'}

## 输出格式

输出 \`\`\`assess-questions 代码块，内容为严格合法的 JSON 数组：

### 选择题格式

\`\`\`json
{
  "id": "q1",
  "type": "choice",
  "question": "以下哪个是栈的特点？",
  "options": ["先进先出", "后进先出", "随机访问", "双端操作"],
  "answer": "B",
  "explanation": "栈是后进先出(LIFO)的数据结构，最后入栈的元素最先出栈。",
  "difficulty": "beginner",
  "knowledgePoints": ["栈"]
}
\`\`\`

### 填空题格式

\`\`\`json
{
  "id": "q6",
  "type": "fill",
  "question": "二叉树的前序遍历顺序是：___、左子树、右子树",
  "answer": "根节点",
  "explanation": "前序遍历的顺序是：根节点→左子树→右子树。",
  "difficulty": "beginner",
  "knowledgePoints": ["二叉树", "遍历"]
}
\`\`\`

字段说明：
- type: "choice"（选择题）| "fill"（填空题）
- question: 题目文本（填空题空格用 ___ 表示）
- options: 选项数组（仅 choice 类型需要，4个选项，不要加 A/B/C/D 前缀）
- answer: 选择题填选项字母 "A"/"B"/"C"/"D"，填空题填标准答案文本
- explanation: 答案解析，2-3 句
- difficulty: "beginner" | "intermediate" | "advanced"
- knowledgePoints: 涉及的知识点标签

## 规则

1. 生成 10-15 题目（选择题 8-10 道，填空题 2-5 道）
2. **必须根据用户专业方向出题，不要出其他专业的题目**
3. **如果用户有薄弱知识点，必须重点考查这些内容（占40%以上）**
4. 基础水平 → 控制难度分布：入门/基础→60%beginner+30%intermediate+10%advanced；中等→30%beginner+50%intermediate+20%advanced；进阶/精通→20%beginner+40%intermediate+40%advanced
5. 学习目标为考试 → 题目贴近常见考点和考法
6. 学习目标为竞赛 → 题目偏难，考察算法思维
7. 解析要清晰，帮助理解而非死记
8. 只输出 JSON，不要输出其他文字`
}

export function buildAssessMessages(
  profileData: ProfileData,
  topic?: string,
  questionCount: number = 12,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)
  const topicHint = topic ? `\n重点主题：${topic}` : ''
  const systemPrompt = buildAssessSystemPrompt(profileData)

  return [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: `## 学生画像\n${ctx}${topicHint}\n\n请生成 ${questionCount} 道个性化测评题目。**题目必须与用户专业方向相关，重点考查用户薄弱知识点！**` },
  ]
}

/**
 * 构建答案评判请求
 */
export function buildJudgeMessages(
  _profileData: ProfileData,
  question: string,
  userAnswer: string,
  correctAnswer: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  return [
    { role: 'system', content: '你是数据结构教师。根据学生答案给出评判和详细解析。回复格式：先判断对错（✓ 或 ✗），然后给出解析。' },
    { role: 'user', content: `题目：${question}\n学生答案：${userAnswer}\n正确答案：${correctAnswer}\n\n请评判并解析。` },
  ]
}
