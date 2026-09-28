import type { ResourceItem, ProfileData } from '../../shared/types'

/**
 * 计算资源与用户画像的匹配度
 *
 * 匹配度 = 基础分(40%) + 薄弱点加成(0-35%) + 认知风格加成(0-15%) + 专业匹配(0-10%)
 * 最高：100%（全匹配）
 * 最低：40%（仅基础分）
 */
export function calcMatchScore(resource: ResourceItem, profile: ProfileData | null): number {
  if (!profile || !profile.weak_points || profile.weak_points.length === 0) {
    return 65 // 无画像或无薄弱点时给默认中等偏下分数
  }

  let score = 40 // 基础分

  // === 薄弱点加成 (0-35分) ===
  if (resource.isWeakPoint) {
    score += 35
  } else {
    const title = resource.title.toLowerCase()
    const desc = (resource.description || '').toLowerCase()
    const module = (resource.module || '').toLowerCase()
    const fullText = `${title} ${desc} ${module}`
    const matched = profile.weak_points.some(wp => {
      const w = wp.toLowerCase()
      return fullText.includes(w)
    })
    if (matched) {
      score += 25
    } else {
      // 间接关联：资源模块与薄弱点同领域
      const major = (profile.major || '').toLowerCase()
      if (major && module.includes(major.split('')[0])) {
        score += 10
      }
    }
  }

  // === 认知风格加成 (0-15分) ===
  const style = profile.cognitive_style || ''

  if (style.includes('视觉') || style === 'visual') {
    if (resource.type === 'video' || resource.type === 'mindmap' || resource.type === 'knowledge-graph') {
      score += 15
    } else if (resource.type === 'code') {
      score += 5
    }
  } else if (style.includes('实践') || style === 'practical') {
    if (resource.type === 'code' || resource.type === 'exercise' || resource.type === 'quiz') {
      score += 15
    } else if (resource.type === 'video') {
      score += 8
    }
  } else if (style.includes('理论') || style === 'theoretical') {
    if (resource.type === 'document' || resource.type === 'knowledge-graph' || resource.type === 'extension') {
      score += 15
    }
  } else {
    // 无认知风格时，根据资源类型给少量基础加成
    if (resource.type === 'document' || resource.type === 'video') {
      score += 5
    }
  }

  // === 专业匹配加成 (0-10分) ===
  const major = (profile.major || '').toLowerCase()
  if (major) {
    const resourceText = `${resource.title} ${resource.module || ''} ${resource.description || ''}`.toLowerCase()
    // 专业关键词匹配
    const majorKeywords: Record<string, string[]> = {
      '软件工程': ['软件', '编程', '代码', '开发', '工程', '设计模式', '架构'],
      '计算机': ['算法', '数据结构', '编程', '计算机', '网络', '操作系统'],
      '人工智能': ['机器学习', '深度学习', 'ai', '神经网络', '模型'],
      '数学': ['数学', '统计', '概率', '微积分', '线性代数'],
    }
    const keywords = majorKeywords[major] || major.split('')
    if (keywords.some(kw => resourceText.includes(kw))) {
      score += 10
    }
  }

  return Math.min(score, 100)
}

/**
 * 按匹配度排序（高到低）
 */
export function sortByMatchScore(resources: ResourceItem[], profile: ProfileData | null): ResourceItem[] {
  return [...resources].sort((a, b) => {
    const scoreA = a.match_score ?? calcMatchScore(a, profile)
    const scoreB = b.match_score ?? calcMatchScore(b, profile)
    return scoreB - scoreA
  })
}

/**
 * 获取匹配度标签
 */
export function getMatchLabel(score: number): { text: string; class: string } {
  if (score >= 85) return { text: '强烈推荐', class: 'match-high' }
  if (score >= 65) return { text: '推荐', class: 'match-medium' }
  if (score >= 50) return { text: '可学', class: 'match-normal' }
  return { text: '', class: '' }
}
