/**
 * 资源推荐 Prompt 模板
 * 包含：资源推荐、思维导图、代码实战、视频推荐
 */

import type { ProfileData } from '../../../shared/types'

function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []
  const filled = profileData.dimensions.filter(d => d.value > 0)
  if (filled.length === 0) return '（画像尚未建立）'

  lines.push(`- 专业：${profileData.major}，年级：${profileData.grade}，基础：${profileData.base_level}`)
  if (profileData.currentSubject) {
    lines.push(`- 当前学习科目：${profileData.currentSubject}`)
  }
  if (profileData.weak_points.length > 0) {
    lines.push(`- 薄弱知识点：${profileData.weak_points.join('、')}`)
  }
  lines.push(`- 学习目标：${profileData.study_goal}`)
  lines.push(`- 认知风格：${profileData.cognitive_style}，节奏：${profileData.study_rhythm}，偏好：${profileData.interest_preference}`)
  return lines.join('\n')
}

/* ===== 资源推荐 ===== */

const RESOURCE_SYSTEM_PROMPT = `你是一个学习资源推荐专家。根据学生的学习画像和当前学习科目，推荐最匹配的学习资源。

## 输出格式

输出 \`\`\`resource-list 代码块，内容为严格合法的 JSON 数组：

\`\`\`resource-list
[
  {
    "title": "资源描述性标题",
    "type": "document",
    "difficulty": "中等",
    "description": "简短描述资源内容和适用场景",
    "module": "知识点模块"
  }
]
\`\`\`

字段说明：
- title: 资源描述性标题（如"《教材名》章节：知识点"、"B站-科目-知识点讲解"）；video 类型需额外提供 url 字段
- type: 必须是 "document" | "mindmap" | "exercise" | "code" | "video" | "extension"
- difficulty: "基础" | "中等" | "进阶"
- description: 1-2 句描述
- module: 所属知识点模块

## 规则

1. 推荐 5-8 个资源，类型多样但侧重用户的 content preference
2. 资源标题用描述性名称；video 类型必须包含 url 字段（B站搜索链接，格式：https://search.bilibili.com/all?keyword=关键词1+关键词2）
3. 基础低 → 多推荐基础入门资源；基础好 → 多推荐进阶资源
4. 薄弱知识点 → 重点推荐该方向的资源
5. 偏好代码实操 → 多推荐 code 类型；偏好视频 → 多推荐 video 类型
6. 学习目标为考试 → 推荐习题类；竞赛 → 推荐竞赛题；项目 → 推荐实战类`

export function buildResourceMessages(
  profileData: ProfileData,
  currentStage?: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)
  const stageHint = currentStage ? `\n当前学习阶段：${currentStage}` : ''

  return [
    { role: 'system', content: RESOURCE_SYSTEM_PROMPT },
    { role: 'user', content: `## 学生画像\n${ctx}${stageHint}\n\n请推荐最适合该学生的学习资源。` },
  ]
}

/* ===== 思维导图 ===== */

const MINDMAP_SYSTEM_PROMPT = `你是一个知识体系梳理专家。根据学生的学习画像和当前学习科目，生成该科目知识体系的思维导图。

## 输出格式

输出 \`\`\`mindmap-data 代码块，JSON 树结构。

每个节点包含：
- name: 节点名称
- desc: 一句话描述该知识点（10-30字）
- highlight: 可选，true 表示薄弱点
- children: 子节点数组

\`\`\`mindmap-data
{
  "name": "科目名称",
  "desc": "科目简介",
  "children": [
    {
      "name": "知识模块",
      "desc": "模块描述",
      "children": [
        { "name": "知识点1", "desc": "知识点描述", "highlight": true },
        { "name": "知识点2", "desc": "知识点描述" }
      ]
    }
  ]
}
\`\`\`

## 规则

1. 导图的根节点名称必须与给定的学习主题一致
2. 3-4 层深度，总计 15-25 个节点
3. 每个节点必须有 name 和 desc
4. 薄弱知识点加 highlight: true
5. 从基础概念到进阶应用的逻辑顺序
6. 只输出 JSON，不要其他文字`

export function buildMindmapMessages(
  profileData: ProfileData,
  topic?: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)
  const actualTopic = topic || profileData.weak_points[0] || profileData.currentSubject || profileData.major || '综合学习'

  return [
    { role: 'system', content: MINDMAP_SYSTEM_PROMPT },
    { role: 'user', content: `## 学生画像\n${ctx}\n\n## 学习主题\n${actualTopic}\n\n请生成围绕「${actualTopic}」的思维导图。` },
  ]
}

/* ===== 代码实战 ===== */

const CODE_SYSTEM_PROMPT = `你是一个代码教学专家。根据学生的学习画像和当前学习科目，生成代码实战示例。

## 输出格式

输出 \`\`\`code-example 代码块，内容为严格合法的 JSON：

\`\`\`code-example
{
  "title": "代码示例标题",
  "language": "python",
  "code": "实现代码...",
  "explanation": "简要说明代码逻辑和关键点",
  "difficulty": "中等"
}
\`\`\`

## 规则

1. 认知风格为实践型 → 代码详细，注释多，逐步引导
2. 认知风格为理论型 → 代码简洁，注释侧重原理
3. 基础水平 → 代码简单，加详细注释；进阶 → 代码高效，分析复杂度
4. 薄弱知识点 → 生成针对性代码，重点突破
5. 语言默认用 Python，如用户偏好可用 C++
6. 代码内容必须与当前学习科目相关，不要生成无关科目的代码`

export function buildCodeMessages(
  profileData: ProfileData,
  topic: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)

  return [
    { role: 'system', content: CODE_SYSTEM_PROMPT },
    { role: 'user', content: `## 学生画像\n${ctx}\n\n## 代码主题\n${topic}\n\n请生成代码实战示例。` },
  ]
}

/* ===== 视频推荐 ===== */

const VIDEO_SYSTEM_PROMPT = `你是一个学习视频推荐专家。根据学生的学习画像和当前学习科目，推荐最匹配的B站学习视频。

## 输出格式

输出 \`\`\`resource-list 代码块，type 全部为 "video"，必须包含 url 字段：

\`\`\`resource-list
[
  {
    "title": "B站-学习视频标题",
    "type": "video",
    "difficulty": "基础",
    "description": "视频内容简介",
    "module": "知识点",
    "url": "https://search.bilibili.com/all?keyword=搜索关键词"
  }
]
\`\`\`

url 字段格式：https://search.bilibili.com/all?keyword=关键词1+关键词2+关键词3

## 规则

1. 推荐 3-5 个视频资源，每个必须包含 url 字段
2. url 使用B站搜索链接，关键词用 + 连接，如：https://search.bilibili.com/all?keyword=英语+语法+讲解
3. 视觉型学习者 → 多推荐动画演示类，关键词加"动画"
4. 入门级 → 推荐概念讲解类；进阶 → 推荐算法分析类
5. 标题用描述性格式（如"平台-主题-内容"）`

export function buildVideoMessages(
  profileData: ProfileData,
  topic?: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)
  const topicHint = topic ? `\n重点主题：${topic}` : ''

  return [
    { role: 'system', content: VIDEO_SYSTEM_PROMPT },
    { role: 'user', content: `## 学生画像\n${ctx}${topicHint}\n\n请推荐学习视频。` },
  ]
}

/* ===== 知识图谱 ===== */

const KNOWLEDGE_GRAPH_SYSTEM_PROMPT = `你是知识图谱生成专家。根据学生的学习画像，生成知识点关联图谱。

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

## 规则

1. 图谱内容必须紧扣给定的学习主题，不要生成无关知识点
2. 15-25 个节点，20-35 条边
3. 薄弱点相关节点 importance 设为 5
4. 确保连通：无孤立节点
5. 只输出 JSON`

export function buildKnowledgeGraphMessages(
  profileData: ProfileData,
  topic?: string,
): { role: 'system' | 'user' | 'assistant'; content: string }[] {
  const ctx = buildProfileContext(profileData)
  const actualTopic = topic || profileData.weak_points[0] || profileData.currentSubject || profileData.major || '综合学习'

  return [
    { role: 'system', content: KNOWLEDGE_GRAPH_SYSTEM_PROMPT },
    { role: 'user', content: `## 学生画像\n${ctx}\n\n## 学习主题\n${actualTopic}\n\n请生成围绕「${actualTopic}」的知识关联图谱。` },
  ]
}
