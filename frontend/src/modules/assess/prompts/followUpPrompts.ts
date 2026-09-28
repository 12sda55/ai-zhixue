/**
 * CAT 追加题目生成 Prompt
 */

import type { ProfileData } from '../../../shared/types'

export function buildFollowUpMessages(
  profileData: ProfileData,
  existingQuestions: string[],
  count: number,
  difficulty: 'beginner' | 'intermediate' | 'advanced',
  focusPoints?: string[],
): { role: 'system' | 'user'; content: string }[] {
  const difficultyDesc = {
    beginner: '基础',
    intermediate: '中等',
    advanced: '进阶',
  }[difficulty]

  const focusHint = focusPoints?.length
    ? `\n重点关注以下知识点：${focusPoints.join('、')}。围绕这些知识点出题。`
    : ''

  return [
    {
      role: 'system',
      content: `你是一位数据结构题目生成专家。根据学生画像和当前测评状态，生成追加的${difficultyDesc}难度题目。

输出格式：使用 \`\`\`assess-questions 代码块包裹 JSON 数组，每道题包含：
- id: 题目ID
- type: "choice"（选择题）
- question: 题目文本
- options: 4个选项数组
- answer: 正确答案字母（A/B/C/D）
- explanation: 答案解析
- difficulty: "${difficulty}"
- knowledgePoints: 涉及的知识点数组

注意：不要与已有题目重复。`,
    },
    {
      role: 'user',
      content: `学生画像：专业${profileData.major}，${profileData.grade}，基础水平${profileData.base_level}。
薄弱知识点：${profileData.weak_points.join('、') || '无'}。
${focusHint}

已有题目（不要重复）：
${existingQuestions.slice(0, 20).join('\n')}

请生成 ${count} 道${difficultyDesc}难度的数据结构题目。`,
    },
  ]
}
