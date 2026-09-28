/**
 * CAT 自适应测评规则引擎
 *
 * 基于答题状态动态调整难度和题目数量
 * 规则在每次提交答案后评估
 */

export type QuestionDifficulty = 'beginner' | 'intermediate' | 'advanced'

export interface AssessState {
  consecutiveCorrect: number
  consecutiveWrong: number
  totalAnswered: number
  correctRate: number
  wrongKnowledgePoints: string[]
  currentDifficulty: QuestionDifficulty
}

export interface AdaptiveRule {
  condition: (state: AssessState) => boolean
  action: 'upgrade' | 'downgrade' | 'focus' | 'extend'
  params: Record<string, unknown>
}

export const ADAPTIVE_RULES: AdaptiveRule[] = [
  // 连续 3 题答对 → 难度升级
  {
    condition: (s) => s.consecutiveCorrect >= 3,
    action: 'upgrade',
    params: { message: '表现出色！挑战更高难度题目 ⬆' },
  },
  // 连续 2 题答错 → 难度降级
  {
    condition: (s) => s.consecutiveWrong >= 2,
    action: 'downgrade',
    params: { message: '别灰心，来些基础题巩固一下 ⬇' },
  },
  // 同一知识点答错 → 聚焦该知识点
  {
    condition: (s) => s.wrongKnowledgePoints.length > 0,
    action: 'focus',
    params: {},  // points 从 state 动态获取
  },
  // 正确率 > 80% 且答了 8 题 → 追加 2 道进阶题
  {
    condition: (s) => s.totalAnswered >= 8 && s.correctRate > 0.8,
    action: 'extend',
    params: { count: 2, difficulty: 'advanced', message: '掌握得不错！追加进阶挑战题 🚀' },
  },
  // 正确率 < 40% 且答了 5 题 → 追加 2 道基础题
  {
    condition: (s) => s.totalAnswered >= 5 && s.correctRate < 0.4,
    action: 'extend',
    params: { count: 2, difficulty: 'beginner', message: '再加几道基础题帮你巩固 💪' },
  },
]

/**
 * 评估当前状态，返回所有触发的规则动作
 */
export function evaluateAdaptiveRules(state: AssessState): { action: AdaptiveRule['action']; params: Record<string, unknown> }[] {
  const triggered: { action: AdaptiveRule['action']; params: Record<string, unknown> }[] = []

  for (const rule of ADAPTIVE_RULES) {
    if (rule.condition(state)) {
      const params = { ...rule.params }
      // focus 动作需要传入当前薄弱知识点
      if (rule.action === 'focus') {
        params.points = state.wrongKnowledgePoints
      }
      triggered.push({ action: rule.action, params })
    }
  }

  return triggered
}
