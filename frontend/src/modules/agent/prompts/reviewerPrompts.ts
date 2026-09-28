/**
 * 审查 Agent Prompt — 审查所有生成内容的质量
 *
 * Stage 5 执行：在所有其他 Agent 完成后，审查输出质量
 * 输出格式：review-report JSON 代码块
 */

import type { ProfileData } from '../../../shared/types'
import { filterRelevantWeakPoints } from '../../profile/stores/profileStore'

/** 构建画像上下文文本 — 以"当前学习科目"为内容相关性审查基准（非专业） */
function buildProfileContext(profileData: ProfileData): string {
  const lines: string[] = []
  const dimensions = profileData.dimensions || []
  const filled = dimensions.filter(d => d.value > 0)
  if (filled.length === 0) return '（画像尚未建立）'

  // 当前学习科目是内容相关性的唯一基准：学生可能在学与其专业不同的科目
  const currentSubject = profileData.currentSubject || profileData.major || ''
  lines.push(`- 当前学习科目：${currentSubject}（内容相关性以此为准）`)
  lines.push(`- 学生专业：${profileData.major}（仅作背景参考，不可据此判定内容不匹配）`)
  lines.push(`- 年级：${profileData.grade}，基础：${profileData.base_level}`)

  // 合并当前科目 overlay + 全局薄弱点，并过滤跨科目污染
  const subjectOverlay = profileData.subjectOverlays?.find(o => o.subject === currentSubject)
  const overlayWeak = subjectOverlay?.weak_points || []
  const globalWeak = profileData.weak_points || []
  const mergedWeak = filterRelevantWeakPoints(
    [...new Set([...overlayWeak, ...globalWeak])],
    currentSubject,
  )
  if (mergedWeak.length > 0) {
    lines.push(`- 薄弱知识点：${mergedWeak.join('、')}`)
  }
  lines.push(`- 学习目标：${profileData.study_goal}`)
  lines.push(`- 认知风格：${profileData.cognitive_style}，偏好：${profileData.interest_preference}`)
  return lines.join('\n')
}

export interface ReviewItem {
  resourceId: string
  type: string
  status: 'pass' | 'revise'
  issues: string[]
  suggestion: string
}

export interface ReviewReport {
  items: ReviewItem[]
  summary: string
}

export function buildReviewerMessages(
  profileData: ProfileData,
  generatedResources: { id: string; type: string; title: string; contentPreview: string }[],
): { role: 'system' | 'user'; content: string }[] {
  const profileContext = buildProfileContext(profileData)

  const resourceList = generatedResources.map(r =>
    `### ${r.title} (${r.type})\nID: ${r.id}\n内容摘要: ${r.contentPreview.slice(0, 300)}...`
  ).join('\n\n')

  return [
    {
      role: 'system',
      content: `你是一位严格的教学内容审查专家。你的职责是审查 AI 生成的学习资源质量。

审查维度：
1. **题库审查**：答案是否正确、选项是否有合理干扰项、难度是否匹配学生水平
2. **文档审查**：知识点覆盖是否完整、与画像匹配度、是否有明显错误
3. **代码审查**：代码是否能正确运行、算法复杂度标注是否准确、解释是否清晰
4. **导图审查**：知识点逻辑层级是否合理、是否有遗漏的关键概念
5. **图谱审查**：节点间关联是否合理、是否有孤立节点

审查标准：
- 只标注真正有问题的事项，不要过度审查
- **内容相关性以"当前学习科目"为唯一基准**。学生可能正在学习与其专业不同的科目（例如计算机专业学生学英语/数学），这是正常学习行为，绝不可因"内容与学生专业不匹配"而要求修订。只有当内容与"当前学习科目"明显偏离时才可标注。
- "revise" 标记意味着内容有明确错误或重要遗漏，需要修正
- "pass" 意味着内容质量合格，可以使用

你必须输出以下格式的审查报告：

\`\`\`review-report
{
  "items": [
    {
      "resourceId": "资源ID",
      "type": "资源类型(document/mindmap/exercise/code/video/knowledge-graph)",
      "status": "pass 或 revise",
      "issues": ["问题描述1", "问题描述2"],
      "suggestion": "修正建议"
    }
  ],
  "summary": "共审查 N 项资源，X 项通过，Y 项需修订"
}
\`\`\``,
    },
    {
      role: 'user',
      content: `请审查以下 AI 生成的学习资源。

${profileContext}

## 待审查资源

${resourceList}

请逐项审查并输出 review-report。`,
    },
  ]
}

/** 解析 review-report 代码块 */
export function parseReviewReport(raw: string): ReviewReport | null {
  const match = raw.match(/```review-report\n([\s\S]*?)```/)
  if (!match) return null

  try {
    const json = JSON.parse(match[1])
    if (!json.items || !Array.isArray(json.items)) return null
    return json as ReviewReport
  } catch {
    try {
      const cleaned = match[1].replace(/,\s*([}\]])/g, '$1')
      const json = JSON.parse(cleaned)
      if (!json.items || !Array.isArray(json.items)) return null
      return json as ReviewReport
    } catch {
      return null
    }
  }
}
