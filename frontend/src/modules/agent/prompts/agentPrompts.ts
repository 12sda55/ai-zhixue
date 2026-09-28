/**
 * Agent 面板 Prompt 模板
 * 为每个智能体定义独立的系统提示
 */

import type { ProfileData } from '../../../shared/types'
import { filterRelevantWeakPoints, isCSSubject } from '../../../shared/utils/subjectFilter'

function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []
  const dimensions = profileData.dimensions || []
  const filled = dimensions.filter(d => d.value > 0)
  if (filled.length === 0) return '（画像尚未建立）'

  lines.push(`- 专业：${profileData.major}，年级：${profileData.grade}`)
  if (profileData.currentSubject) {
    lines.push(`- 当前学习科目：${profileData.currentSubject}`)
    lines.push(`- 该科目基础水平：${profileData.base_level}`)
    // 只传当前科目相关的薄弱点，过滤跨科目污染内容
    const subjectOverlay = profileData.subjectOverlays?.find(o => o.subject === profileData.currentSubject)
    const overlayWeak = subjectOverlay?.weak_points || []
    const globalWeak = profileData.weak_points || []
    const merged = [...new Set([...overlayWeak, ...globalWeak])]
    const relevantWeakPoints = filterRelevantWeakPoints(merged, profileData.currentSubject)
    if (relevantWeakPoints.length > 0) {
      lines.push(`- 当前科目薄弱知识点：${relevantWeakPoints.join('、')}`)
    }
    const relevantGoal = subjectOverlay?.study_goal || profileData.study_goal
    lines.push(`- 学习目标：${relevantGoal}`)
  } else {
    lines.push(`- 基础：${profileData.base_level}`)
    const weakPoints = filterRelevantWeakPoints(profileData.weak_points || [], profileData.major || '')
    if (weakPoints.length > 0) {
      lines.push(`- 薄弱知识点：${weakPoints.join('、')}`)
    }
    lines.push(`- 学习目标：${profileData.study_goal}`)
  }
  lines.push(`- 认知风格：${profileData.cognitive_style}，偏好：${profileData.interest_preference}`)
  return lines.join('\n')
}

/* ===== 文档生成 Agent ===== */

export function buildDocAgentMessages(profileData: ProfileData, topic: string) {
  const subject = profileData.currentSubject || ''
  const isCS = isCSSubject(subject)

  const systemPrompt = isCS
    ? `你是一个知识点文档生成专家。根据学生的学习画像，生成结构清晰的知识讲解文档。

## 输出格式

用 Markdown 格式输出知识点讲解文档，包含：
- 标题和概述
- 核心概念（加粗关键术语）
- 代码示例（Python/C++）
- 常见误区
- 与其他知识点的关系

## 规则

1. 基础水平低 → 用类比和图解描述，代码加详细注释
2. 薄弱知识点 → 重点展开，多给示例
3. 认知风格：实践型→代码先行，理论型→原理先行
4. 文档 300-600 字`
    : `你是一个知识点文档生成专家。根据学生的学习画像，生成结构清晰的知识讲解文档。

## 输出格式

用 Markdown 格式输出知识点讲解文档，包含：
- 标题和概述
- 核心概念（加粗关键术语）
- 丰富的自然语言示例（非代码，除非主题本身就是编程）
- 常见误区与易混淆点
- 学习建议与记忆技巧

## 规则

1. 基础水平低 → 用生活类比和简单例子，循序渐进
2. 薄弱知识点 → 重点展开，多给示例
3. 认知风格：实践型→多给练习示例，理论型→原理先行
4. **不要强行用编程类比**，除非用户专业是计算机且主题与编程相关
5. 内容要贴合学科本身的特点，用该学科的常规教学方式
6. 文档 300-600 字`

  return [
    { role: 'system' as const, content: systemPrompt },
    { role: 'user' as const, content: `## 学生画像\n${buildProfileContext(profileData)}\n\n## 知识主题\n${topic}\n\n请生成知识点讲解文档。` },
  ]
}

/* ===== 导图生成 Agent ===== */

export function buildMindmapPrompt(profileData: ProfileData, topic?: string): string {
  const weakPoints = profileData.weak_points.length > 0 ? profileData.weak_points.join('、') : '暂无'
  const baseLevel = profileData.base_level || '入门'
  const actualTopic = topic || profileData.currentSubject || profileData.weak_points[0] || profileData.major || '综合学习'

  const levelLabel = baseLevel === '入门' ? '初学者' : baseLevel === '基础' ? '初级' : baseLevel === '中等' ? '中级' : baseLevel === '进阶' ? '进阶' : '精通'

  return `你是知识体系导图生成专家。根据学生的学习画像，生成结构化的知识体系导图。

## 学习画像

- **学习主题**: ${actualTopic}
- **基础水平**: ${levelLabel}
- **薄弱知识点**: ${weakPoints}

## 输出格式

输出 \`\`\`mindmap-data 代码块，JSON 树结构。

### Schema

每个节点包含：
- name: 节点名称，简洁明确
- desc: 一句话描述该知识点（10-30字）
- highlight: 仅薄弱点相关节点设 true（可选）
- children: 子节点数组（可选）

### 示例输出

\`\`\`mindmap-data
{
  "name": "数据结构",
  "desc": "计算机存储和组织数据的方式",
  "children": [
    {
      "name": "线性结构",
      "desc": "元素按顺序排列的结构",
      "children": [
        { "name": "数组", "desc": "连续内存，随机访问 O(1)", "highlight": true },
        { "name": "链表", "desc": "动态结构，插入删除 O(1)" },
        { "name": "栈", "desc": "后进先出 LIFO" },
        { "name": "队列", "desc": "先进先出 FIFO" }
      ]
    },
    {
      "name": "树形结构",
      "desc": "分层非线性结构",
      "children": [
        { "name": "二叉树", "desc": "每个节点最多两个子节点", "highlight": true },
        { "name": "二叉搜索树", "desc": "左小右大的有序树" },
        { "name": "堆", "desc": "完全二叉树，优先队列基础" }
      ]
    }
  ]
}
\`\`\`

## 要求

1. **深度**: 3-4 层，根节点为第1层
2. **节点数**: 总计 15-25 个节点（不含根节点）
3. **每个节点必须有 name 和 desc**
4. **薄弱点相关节点设 highlight: true**（2-4个节点）
5. **逻辑顺序**: 从基础概念到进阶应用
6. **描述质量**: desc 应解释该知识点的核心特征或用途
7. **只输出 JSON**: 不要输出其他任何文字，只输出 mindmap-data 代码块`
}

export function buildMindmapAgentMessages(profileData: ProfileData, topic?: string) {
  return [
    { role: 'system' as const, content: '你是一个知识体系导图生成专家，严格按照指定格式输出。' },
    { role: 'user' as const, content: buildMindmapPrompt(profileData, topic) },
  ]
}

/* ===== 题库生成 Agent ===== */

export function buildQuizPrompt(profileData: ProfileData): string {
  const weakPoints = profileData.weak_points.length > 0 ? profileData.weak_points.join('、') : '暂无'
  const baseLevel = profileData.base_level || '入门'
  const topic = profileData.currentSubject || profileData.major || '综合学习'

  const levelLabel = baseLevel === '入门' ? '初学者' : baseLevel === '基础' ? '初级' : baseLevel === '中等' ? '中级' : baseLevel === '进阶' ? '进阶' : '精通'

  const difficultyGuide = baseLevel === '入门' || baseLevel === '基础'
    ? '基础题 60%，中等题 30%，进阶题 10%'
    : baseLevel === '中等'
    ? '基础题 30%，中等题 50%，进阶题 20%'
    : '基础题 20%，中等题 40%，进阶题 40%'

  return `你是一个${topic}出题专家。根据学习画像生成个性化测评题目。

## 学习画像

- **学习主题**: ${topic}
- **基础水平**: ${levelLabel}
- **薄弱知识点**: ${weakPoints}

## 输出格式

输出 \`\`\`assess-questions 代码块，JSON 数组。

### 选择题格式

\`\`\`json
{
  "id": "q1",
  "type": "choice",
  "question": "以下哪个是栈的特点？",
  "options": ["先进先出", "后进先出", "随机访问", "双端操作"],
  "answer": "B",
  "explanation": "栈是后进先出(LIFO)的数据结构。",
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
  "explanation": "前序遍历：根→左→右",
  "difficulty": "beginner",
  "knowledgePoints": ["二叉树", "遍历"]
}
\`\`\`

## 要求

1. **题目数量**: 10-15 道
2. **题型分布**: 选择题 8-10 道，填空题 2-5 道
3. **难度分布**: ${difficultyGuide}
4. **薄弱点覆盖**: 薄弱知识点至少占 3-4 题
5. **选择题 options**: 4个选项，不要加 A/B/C/D 前缀
6. **选择题 answer**: 填字母 "A"/"B"/"C"/"D"
7. **填空题 answer**: 填标准答案文本
8. **只输出 JSON**: 不要输出其他文字`
}

export function buildQuizAgentMessages(profileData: ProfileData, topic?: string) {
  const topicHint = topic ? `\n重点主题：${topic}` : ''
  return [
    { role: 'system' as const, content: `你是一个出题专家，严格按照指定格式输出。` },
    { role: 'user' as const, content: `${buildQuizPrompt(profileData)}${topicHint}` },
  ]
}

/* ===== 代码生成 Agent ===== */

export const CODE_AGENT_PROMPT = `你是一个数据结构代码教学专家。根据学习画像生成代码实战示例。

## 输出格式

输出 \`\`\`code-example 代码块（JSON），含 title/language/code/explanation/difficulty。

实践型→详细代码+多注释；理论型→简洁代码+原理注释。`

export function buildCodeAgentMessages(profileData: ProfileData, topic: string) {
  return [
    { role: 'system' as const, content: CODE_AGENT_PROMPT },
    { role: 'user' as const, content: `## 学生画像\n${buildProfileContext(profileData)}\n\n## 代码主题\n${topic}\n\n请生成代码实战示例。` },
  ]
}

/* ===== 视频推荐 Agent ===== */

export const VIDEO_AGENT_PROMPT = `你是一个学习视频推荐专家。根据学习画像推荐B站学习视频，生成可直接点击观看的B站链接。

## 输出格式

直接输出 Markdown 格式的视频推荐列表，格式如下：

**推荐视频（点击标题即可跳转B站观看）**

---

### 1. 【基础】视频标题
> 📺 频道/UP主名称 | ⏱️ 时长 | 📊 难度：基础
> 
> 视频简介：1-2句话描述视频内容和适用场景
> 
> 🎯 点击观看：[https://www.bilibili.com/video/BVxxxxxxxx](https://www.bilibili.com/video/BVxxxxxxxx)

---

### 2. 【进阶】视频标题
> 📺 频道/UP主名称 | ⏱️ 时长 | 📊 难度：进阶
> 
> 视频简介：视频内容和适用场景
> 
> 🎯 点击观看：[https://www.bilibili.com/video/BVxxxxxxxx](https://www.bilibili.com/video/BVxxxxxxxx)

---

## 要求

1. **推荐数量**: 3-5 个视频
2. **链接格式**: 必须提供具体的B站视频链接，格式为 https://www.bilibili.com/video/BVxxxxxxxx
3. **视频选择**: 
   - 入门级 → 推荐概念讲解类、动画演示类视频
   - 进阶 → 推荐算法分析、实战项目类视频
4. **薄弱知识点**: 重点推荐与薄弱知识点相关的视频
5. **认知风格**:
   - 视觉型 → 多推荐动画演示、可视化类
   - 实践型 → 多推荐代码实现、项目实战类
6. **搜索建议**: 如果没有确切视频链接，可以用B站搜索链接作为备选
7. **只输出视频推荐**: 不要输出其他任何无关内容
`

export function buildVideoAgentMessages(profileData: ProfileData, topic?: string) {
  const topicHint = topic ? `\n重点主题：${topic}` : ''
  return [
    { role: 'system' as const, content: VIDEO_AGENT_PROMPT },
    { role: 'user' as const, content: `## 学生画像\n${buildProfileContext(profileData)}${topicHint}\n\n请推荐学习视频，直接输出 Markdown 格式的视频推荐列表，链接必须是可点击的B站链接。` },
  ]
}

/* ===== 知识图谱生成 Agent ===== */

export function buildKnowledgeGraphPrompt(profileData: ProfileData, topic?: string): string {
  const weakPoints = profileData.weak_points.length > 0 ? profileData.weak_points.join('、') : '暂无'
  const actualTopic = topic || profileData.currentSubject || profileData.weak_points[0] || profileData.major || '综合学习'

  return `你是知识图谱生成专家。根据学生的学习画像，生成知识点关联图谱。

## 学习画像

- **学习主题**: ${actualTopic}
- **薄弱知识点**: ${weakPoints}

## 输出格式

输出 \`\`\`knowledge-graph 代码块，JSON 格式。

### Schema

- nodes 数组，每个节点含：
  - id: 唯一标识，英文小写+连字符
  - name: 知识点名称
  - category: "core"（核心概念）| "advanced"（进阶知识）| "algorithm"（算法方法）| "application"（应用实践）
  - importance: 1-5，5最重要
  - desc: 一句话描述

- edges 数组，每条边含：
  - source: 起点节点 id
  - target: 终点节点 id
  - label: 关系描述（包含/依赖/前置/应用/对比）

### 示例输出

\`\`\`knowledge-graph
{
  "nodes": [
    { "id": "tree", "name": "树", "category": "core", "importance": 5, "desc": "分层非线性结构" },
    { "id": "binary-tree", "name": "二叉树", "category": "core", "importance": 5, "desc": "每个节点最多两个子节点" },
    { "id": "bst", "name": "BST", "category": "advanced", "importance": 4, "desc": "左小右大的搜索树" },
    { "id": "heap", "name": "堆", "category": "advanced", "importance": 4, "desc": "完全二叉树，优先队列基础" },
    { "id": "traversal", "name": "遍历", "category": "algorithm", "importance": 5, "desc": "前序/中序/后序/层序" }
  ],
  "edges": [
    { "source": "tree", "target": "binary-tree", "label": "特例" },
    { "source": "binary-tree", "target": "bst", "label": "应用" },
    { "source": "binary-tree", "target": "heap", "label": "应用" },
    { "source": "binary-tree", "target": "traversal", "label": "操作" }
  ]
}
\`\`\`

## 要求

1. **节点数**: 15-25 个
2. **边数**: 20-35 条
3. **关系类型**: 包含、依赖、前置知识、应用、对比
4. **薄弱点相关节点 importance 设为 5**
5. **确保连通**: 无孤立节点，所有节点至少有一条边
6. **只输出 JSON**: 不要输出其他任何文字`
}

export function buildKnowledgeGraphAgentMessages(profileData: ProfileData, topic?: string) {
  return [
    { role: 'system' as const, content: '你是一个知识图谱生成专家，严格按照指定格式输出。' },
    { role: 'user' as const, content: buildKnowledgeGraphPrompt(profileData, topic) },
  ]
}

/* ===== 路径规划 Agent ===== */

export function buildPathAgentMessages(
  profileData: ProfileData,
  generatedTopics?: string[],
  availableResourceTypes?: string[],
) {
  const subject = profileData.currentSubject || ''
  const isCS = isCSSubject(subject)

  // 根据已生成资源的类型约束路径可选类型；未提供时用默认全类型
  const defaultTypes = isCS
    ? ['document', 'mindmap', 'exercise', 'code', 'video']
    : ['document', 'mindmap', 'exercise', 'video']
  const allowedTypes = (availableResourceTypes && availableResourceTypes.length > 0)
    ? availableResourceTypes
    : defaultTypes
  const resourceTypesStr = allowedTypes.map(t => `"${t}"`).join(' | ')

  const pathPrompt = `你是一个学习路径规划专家。根据学习画像和已生成的学习资料，规划学习路径。

## 输出格式

输出 \`\`\`path-plan 代码块（JSON），含 summary + stages 数组。

每阶段含 title/suggestedDays/reasonType/reason/learningTips/resources。

每个 resource 必须包含：
- type: 资源类型，只能从以下已生成的类型中选择: ${resourceTypesStr}
- name: 资源名称（具体描述，如"动词时态变化规则讲解"，不要用模糊名称如"练习题"）

**重要：只能使用上述列出的资源类型，不要生成未列出的类型。** 这些类型对应已由智能体生成或可在线生成的学习资料。
每个阶段应包含多种类型的资源（至少 2 种不同类型）。
${!isCS ? '\n注意：当前为非编程科目，不要生成 code 类型资源。' : ''}`

  const topicsHint = generatedTopics?.length ? `\n已覆盖知识点：${generatedTopics.join('、')}` : ''
  return [
    { role: 'system' as const, content: pathPrompt },
    { role: 'user' as const, content: `## 学生画像\n${buildProfileContext(profileData)}${topicsHint}\n\n请规划学习路径。` },
  ]
}
