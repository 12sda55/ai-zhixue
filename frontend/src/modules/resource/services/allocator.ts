/**
 * 资源分配器（深模块）
 *
 * 接口：allocate(stages, pool, profile) → AllocateResult
 * 实现：遍历每个小节的每个 PathResource，调 recommender 推荐候选，
 *      已分配的加入 exclude 集合，确保不同小节不会拿到同一个资源。
 *
 * 这是解决"每小节内容一样"的核心：
 *  - 旧的 linkResourcesToGenerated + findMatchingResource 是运行时各自匹配
 *  - 新的 allocator 是显式的一次性分配决策，exclude 跨小节累积
 *  - 缺口（无候选）记录到 gaps，由调用方决定是否触发生成
 *
 * 设计原则（codebase-design）：
 *  - 分配是"一次决策"，不是"各处运行时匹配"
 *  - recommender 负责"单个资源 vs 单个小节"的匹配评分
 *  - allocator 负责"全局供需平衡"——一个小节拿了，下一个小节的 exclude 就多一项
 */

import type { ResourceItem, ResourceType, ProfileData, PathStageExtended } from '../../../shared/types'
import { recommend, filterRelevantWeakPoints } from './recommender'

export interface AllocateResult {
  /** 每个 PathResource.id → 分配的 ResourceItem.id（null 表示无匹配，需生成） */
  assignments: Map<string, string | null>
  /** 缺口列表：无候选资源的 PathResource，需要触发 agent 生成 */
  gaps: Array<{
    stageId: string
    stageTitle: string
    prId: string
    prName: string
    type: ResourceType
    topic: string
  }>
}

/**
 * 为路径的每个小节分配资源
 * - 已有 resourceRef 的保留（用户手动关联的不覆盖）
 * - 无 resourceRef 的调 recommender 推荐
 * - 推荐不到的记入 gaps
 */
export function allocate(
  stages: PathStageExtended[],
  pool: ResourceItem[],
  profile: ProfileData,
): AllocateResult {
  const assignments = new Map<string, string | null>()
  const gaps: AllocateResult['gaps'] = []
  const usedResourceIds = new Set<string>()

  const subject = profile.currentSubject || profile.major || ''
  const weakPoints = filterRelevantWeakPoints(profile.weak_points || [], subject)

  for (const stage of stages) {
    if (!stage.resources) continue

    for (const pr of stage.resources) {
      // 保留已有 resourceRef
      if (pr.resourceRef) {
        assignments.set(pr.id, pr.resourceRef)
        usedResourceIds.add(pr.resourceRef)
        continue
      }

      // 调 recommender 推荐
      // 'extension' 归一化为 'document'：没有 extension 资源生成器，用 document 资源填充
      const matchType = pr.type === 'extension' ? 'document' : pr.type
      const ranked = recommend({
        profile,
        stageContext: {
          title: stage.title,
          reasonType: stage.reasonType as 'foundation' | 'weakness' | 'advanced' | undefined,
        },
        pool,
        exclude: usedResourceIds,
        type: matchType,
        resourceName: pr.name,
      })

      if (ranked.length > 0) {
        const best = ranked[0]
        assignments.set(pr.id, best.resource.id)
        usedResourceIds.add(best.resource.id)
      } else {
        // 无候选 → 记录缺口
        assignments.set(pr.id, null)
        gaps.push({
          stageId: stage.id,
          stageTitle: stage.title,
          prId: pr.id,
          prName: pr.name,
          type: matchType,
          topic: extractTopicFromStage(stage.title, weakPoints, subject),
        })
      }
    }
  }

  return { assignments, gaps }
}

/** 从阶段标题提取主题词 */
function extractTopicFromStage(title: string, weakPoints: string[], subject: string): string {
  const topic = title
    .replace(/基础|进阶|综合|专项|突破|概念|应用|实战|复习|阶段|第[一二三四五六七八九十]章|第[1-9]\d?/g, '')
    .trim()
  if (topic.length >= 2) return topic
  return weakPoints[0] || subject || '学习内容'
}

/**
 * 应用分配结果到 stages（设置 resourceRef）
 * 返回是否有变更（用于判断是否需要 saveStages）
 */
export function applyAssignments(
  stages: PathStageExtended[],
  assignments: Map<string, string | null>,
): boolean {
  let changed = false
  for (const stage of stages) {
    if (!stage.resources) continue
    for (const pr of stage.resources) {
      const assigned = assignments.get(pr.id)
      if (assigned === undefined) continue  // 未分配的不动
      if (pr.resourceRef !== assigned) {
        pr.resourceRef = assigned
        pr.status = assigned ? 'active' : 'pending'
        changed = true
      }
    }
  }
  return changed
}
