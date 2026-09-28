/**
 * 资源推荐器（深模块）
 *
 * 接口：recommend(input) → RankedResource[]
 * 实现：科目匹配 + 类型匹配 + 薄弱点匹配 + 名称核心词 + 难度 + 内容就绪度
 *
 * 一个接口服务三个消费者：
 *  - pathStore.allocator 分配小节资源
 *  - ResourceLearningModal 兜底查找
 *  - 社区/资源库浏览排序
 *
 * 设计原则（codebase-design）：把"画像→资源匹配"这个分散在三处的能力收敛成一个深模块，
 * 接口小（一个 recommend 函数），实现大（多维评分 + 过滤 + 排序）。
 * 改一处评分规则，所有消费者受益。
 */

import type { ResourceItem, ResourceType, ProfileData } from '../../../shared/types'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'

export interface RecommendInput {
  /** 用户画像（科目、薄弱点、难度偏好） */
  profile: ProfileData
  /** 当前小节上下文（标题、类型、原因） */
  stageContext: {
    title: string
    reasonType?: 'foundation' | 'weakness' | 'advanced'
  }
  /** 候选资源池 */
  pool: ResourceItem[]
  /** 已用资源 ID 集合（避免一个小节拿了的资源下个小节又拿到） */
  exclude?: Set<string>
  /** 限定资源类型（不传则不限） */
  type?: ResourceType
  /** PathResource 的名称（用于名称匹配评分） */
  resourceName?: string
}

export interface RankedResource {
  resource: ResourceItem
  score: number
  reasons: string[]
}

/** 科目匹配关键词权重 */
const SUBJECT_MATCH_SCORE = 30
const TYPE_MATCH_SCORE = 20
const WEAK_POINT_SCORE = 25
const NAME_MATCH_SCORE = 15
const DIFFICULTY_MATCH_SCORE = 10
const CONTENT_READY_SCORE = 5

/** reasonType → 期望难度 */
const REASON_TYPE_DIFFICULTY: Record<string, 'beginner' | 'intermediate' | 'advanced'> = {
  foundation: 'beginner',
  weakness: 'intermediate',
  advanced: 'advanced',
}

/**
 * 推荐资源：按画像+小节上下文给候选池打分排序
 * exclude 集合中的资源会被过滤掉
 */
export function recommend(input: RecommendInput): RankedResource[] {
  const { profile, stageContext, pool, exclude, type, resourceName } = input

  const subject = (profile.currentSubject || profile.major || '').toLowerCase()
  const weakPoints = filterRelevantWeakPoints(profile.weak_points || [], subject)
  const expectedDifficulty = stageContext.reasonType
    ? REASON_TYPE_DIFFICULTY[stageContext.reasonType]
    : undefined

  const candidates = pool.filter(r => {
    if (exclude?.has(r.id)) return false
    if (type && r.type !== type) return false
    return true
  })

  const scored: RankedResource[] = []
  for (const r of candidates) {
    const result = scoreResource(r, {
      subject,
      weakPoints,
      expectedDifficulty,
      resourceName,
    })
    if (result.score > 0) {
      scored.push(result)
    }
  }

  scored.sort((a, b) => b.score - a.score)
  return scored
}

interface ScoreContext {
  subject: string
  weakPoints: string[]
  expectedDifficulty?: 'beginner' | 'intermediate' | 'advanced'
  resourceName?: string
}

function scoreResource(r: ResourceItem, ctx: ScoreContext): RankedResource {
  let score = 0
  const reasons: string[] = []

  // 1. 科目匹配
  const rSubject = (r.subject || '').toLowerCase()
  const rModule = (r.module || '').toLowerCase()
  if (ctx.subject && (rSubject.includes(ctx.subject) || rModule.includes(ctx.subject))) {
    score += SUBJECT_MATCH_SCORE
    reasons.push('科目匹配')
  }

  // 2. 薄弱点匹配
  const rTitle = (r.title || '').toLowerCase()
  const rDesc = (r.description || '').toLowerCase()
  const matchedWp = ctx.weakPoints.find(
    wp => wp.length >= 2 && (rTitle.includes(wp.toLowerCase()) || rModule.includes(wp.toLowerCase()) || rDesc.includes(wp.toLowerCase()))
  )
  if (matchedWp) {
    score += WEAK_POINT_SCORE
    reasons.push(`薄弱点: ${matchedWp}`)
  }

  // 3. 名称匹配（PathResource name vs ResourceItem title）
  if (ctx.resourceName) {
    const prName = ctx.resourceName.toLowerCase()
    const rTitleNorm = rTitle.replace(/\s+/g, '')
    const prNameNorm = prName.replace(/\s+/g, '')
    if (rTitleNorm.includes(prNameNorm) || prNameNorm.includes(rTitleNorm)) {
      score += NAME_MATCH_SCORE
      reasons.push('名称匹配')
    } else {
      // 核心词匹配（去掉类型后缀后的词）
      const coreWord = extractCoreWord(ctx.resourceName)
      if (coreWord.length >= 2 && rTitle.includes(coreWord.toLowerCase())) {
        score += Math.floor(NAME_MATCH_SCORE / 2)
        reasons.push(`核心词: ${coreWord}`)
      }
    }
  }

  // 4. 难度匹配
  if (ctx.expectedDifficulty && r.difficulty === ctx.expectedDifficulty) {
    score += DIFFICULTY_MATCH_SCORE
    reasons.push('难度匹配')
  }

  // 5. 内容就绪度（有内容/有URL的优先）
  if (r.content && r.content.length > 50) {
    score += CONTENT_READY_SCORE
    reasons.push('内容已就绪')
  }
  if (r.type === 'video' && r.videoStatus === 'done' && r.url) {
    score += CONTENT_READY_SCORE
    reasons.push('视频已生成')
  }

  return { resource: r, score, reasons }
}

/** 提取名称核心词（去掉类型后缀） */
function extractCoreWord(name: string): string {
  return name
    .replace(/基础|进阶|综合|专项|突破|概念|应用|实战|复习|入门|高级|中级|初级|详解|教程|指南|笔记|讲解|演示|练习|模板|导图|图谱|视频|代码|教学视频|动画演示/g, '')
    .trim()
}

/**
 * 过滤跨科目污染的薄弱点 — 从 shared/utils/subjectFilter 导入并 re-export
 * allocator.ts 从此文件导入 filterRelevantWeakPoints，保持 re-export 不破坏消费者
 */
export { filterRelevantWeakPoints }
