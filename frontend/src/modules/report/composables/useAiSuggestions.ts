/**
 * AI 学习报告生成 composable
 * 调用专职报告Agent生成专业的Word文档式报告
 */

import { ref } from 'vue'
import { chatGLM } from '../../../shared/api/glmApi'
import { buildReportMessages, getFallbackReport } from '../prompts/reportPrompts'
import { useQaStore } from '../../qa/stores/qaStore'
import { useAssessStore } from '../../assess/stores/assessStore'
import { usePathStore } from '../../path/stores/pathStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import type { ProfileData } from '../../../shared/types'

export function useAiSuggestions() {
  const suggestions = ref('')
  const isGenerating = ref(false)

  async function generateSuggestions(profileData: ProfileData): Promise<string> {
    isGenerating.value = true
    suggestions.value = ''

    // 收集各模块数据
    const qaStore = useQaStore()
    const assessStore = useAssessStore()
    const pathStore = usePathStore()
    const resourceStore = useResourceStore()

    // 答疑数据
    const qaData = {
      totalQuestions: qaStore.history.length,
      recentTopics: qaStore.history.slice(0, 5).map(h => h.question?.replace('...', '') || ''),
    }

    // 测评数据
    const assessData = {
      totalAssessCount: profileData.completedAssessCount ?? 0,
      wrongAnswers: assessStore.wrongAnswers,
      avgScore: assessStore.report?.overallScore,
    }

    // 路径数据
    const pathData = {
      completedStages: pathStore.stages.filter(s => s.status === 'completed').length,
      activeStages: pathStore.stages.filter(s => s.status === 'active').length,
      pendingStages: pathStore.stages.filter(s => s.status === 'pending').length,
      totalProgress: pathStore.totalProgress,
      stages: pathStore.stages.slice(0, 5),
    }

    // 资源数据
    const resourceData = {
      total: resourceStore.resources.length,
      completed: resourceStore.resources.filter(r => r.status === 'completed').length,
      byType: resourceStore.resourcesByType,
    }

    // 构建报告生成消息
    const messages = buildReportMessages(profileData, pathData, assessData, qaData, resourceData)

    return new Promise((resolve) => {
      let content = ''
      let hasContent = false
      let fallbackTimer: ReturnType<typeof setTimeout> | null = null

      // 15秒超时降级
      fallbackTimer = setTimeout(() => {
        if (!hasContent && isGenerating.value) {
          console.warn('[Report] AI超时，使用降级报告')
          const fallback = getFallbackReport(profileData, pathData, assessData, qaData, resourceData)
          suggestions.value = fallback
          isGenerating.value = false
          resolve(fallback)
        }
      }, 15000)

      chatGLM(
        messages,
        (text: string) => {
          hasContent = true
          if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
          content += text
          suggestions.value = content
        },
        () => {
          if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
          isGenerating.value = false
          if (!content.trim()) {
            const fallback = getFallbackReport(profileData, pathData, assessData, qaData, resourceData)
            suggestions.value = fallback
            resolve(fallback)
          } else {
            resolve(content)
          }
        },
        () => {
          if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
          console.warn('[Report] AI生成失败，使用降级报告')
          const fallback = getFallbackReport(profileData, pathData, assessData, qaData, resourceData)
          suggestions.value = fallback
          isGenerating.value = false
          resolve(fallback)
        },
      )
    })
  }

  return { suggestions, isGenerating, generateSuggestions }
}