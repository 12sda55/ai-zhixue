import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ResourceItem, PathStageExtended, PathResource } from '../../../shared/types'
import { usePathStore } from '../../path/stores/pathStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { sortByMatchScore } from '../../../shared/utils/matchScorer'
import { isCSSubject } from '../../../shared/utils/subjectFilter'

export const useWorkspaceStore = defineStore('workspace', () => {
  const selectedResourceId = ref<string | null>(null)
  const expandedStages = ref<Set<string>>(new Set())

  const pathStore = usePathStore()
  const resourceStore = useResourceStore()
  const profileStore = useProfileStore()

  const stages = computed(() => pathStore.stages || [])
  const allResources = computed(() => resourceStore.resources)

  /** 获取每个阶段的资源（按匹配度排序） */
  function getStageResources(stage: PathStageExtended): ResourceItem[] {
    const stageResources: ResourceItem[] = []
    const usedResourceIds = new Set<string>()
    let needSavePath = false

    if (stage.resources && stage.resources.length > 0) {
      for (const sr of stage.resources) {
        let found: ResourceItem | null = null

        // 优先级1: resourceRef 显式引用（最可靠），但类型不匹配或已被其他阶段占用时清除
        if (sr.resourceRef) {
          const refResource = allResources.value.find(r => r.id === sr.resourceRef)
          if (refResource && !usedResourceIds.has(refResource.id) && refResource.type === sr.type) {
            found = refResource
          } else {
            // 类型不匹配 或 已被其他阶段占用 → 清除旧引用，重新匹配
            sr.resourceRef = null
            needSavePath = true
          }
        }

        // 优先级2: ID 不以 res- 开头（旧数据兼容：之前的 linkResourcesToGenerated 替换了 id）
        if (!found && !sr.id.startsWith('res-')) {
          const byId = allResources.value.find(r => r.id === sr.id && !usedResourceIds.has(r.id))
          if (byId) {
            // 迁移：设置 resourceRef，保持 id 不变
            sr.resourceRef = byId.id
            needSavePath = true
            found = byId
          }
        }

        // 优先级3: 名称模糊匹配
        if (!found) {
          found = findBestResourceMatch(sr, allResources.value, usedResourceIds)
          if (found) {
            // 匹配成功，设置 resourceRef 供下次直接查找
            sr.resourceRef = found.id
            sr.status = 'active'
            needSavePath = true
          }
        }

        if (found) {
          stageResources.push(found)
          usedResourceIds.add(found.id)
        } else {
          // 兜底：PathResource 转为 ResourceItem 显示（有名称但无内容）
          stageResources.push(pathResourceToItem(sr, stage))
        }
      }
    } else {
      // 没有显式关联的阶段资源，从资源库按阶段标题关键词匹配
      const currentSubject = profileStore.profileData.currentSubject || ''
      const currentIsCS = isCSSubject(currentSubject)
      const keywords = extractCoreWords(stage.title).filter(w => w.length >= 2)
      const matched = allResources.value.filter(r => {
        // 科目兼容性检查：防止跨科目资源混入
        if (r.subject && currentSubject) {
          const resIsCS = isCSSubject(r.subject)
          if (currentIsCS !== resIsCS) return false
        }
        const text = `${r.title} ${r.description || ''} ${r.module || ''}`.toLowerCase()
        return keywords.some(kw => text.includes(kw))
      })
      if (matched.length > 0) {
        stageResources.push(...matched)
      }
    }

    if (needSavePath) {
      pathStore.saveStages()
    }

    // 按类型优先排序，同类型内按匹配度排序
    const typeOrder: Record<string, number> = { document: 0, video: 1, exercise: 2, code: 3, mindmap: 4, 'knowledge-graph': 5, extension: 6 }
    const sorted = sortByMatchScore(stageResources, profileStore.profileData)
    sorted.sort((a, b) => {
      const orderA = typeOrder[a.type] ?? 99
      const orderB = typeOrder[b.type] ?? 99
      return orderA - orderB
    })
    return sorted
  }

  /** 为 PathResource 找到最佳匹配的 ResourceItem */
  function findBestResourceMatch(pr: PathResource, allResources: ResourceItem[], usedIds: Set<string>): ResourceItem | null {
    // 过滤掉不同科目类别的资源（防止跨科目污染：如英语资源匹配到CS阶段）
    const currentSubject = profileStore.profileData.currentSubject || ''
    const currentIsCS = isCSSubject(currentSubject)
    const available = allResources.filter(r => {
      if (usedIds.has(r.id)) return false
      // 科目兼容性检查：CS资源只能匹配CS科目，非CS资源只能匹配非CS科目
      if (r.subject && currentSubject) {
        const resIsCS = isCSSubject(r.subject)
        if (currentIsCS !== resIsCS) return false
      }
      return true
    })
    const normalizeStr = (s: string) => s.replace(/\s+/g, '')
    const prNameNorm = normalizeStr(pr.name || '')
    const prWords = extractCoreWords(pr.name).filter(w => w.length >= 2)

    // 1. 同类型+名称匹配（去除空格后比较）
    const sameTypeByName = available.find(r => {
      if (r.type !== pr.type) return false
      const rtNorm = normalizeStr(r.title || '')
      return rtNorm === prNameNorm || rtNorm.includes(prNameNorm) || prNameNorm.includes(rtNorm)
    })
    if (sameTypeByName) return sameTypeByName

    // 2. 同类型+核心词匹配
    if (prWords.length > 0) {
      const coreMatch = available.find(r => {
        if (r.type !== pr.type) return false
        const text = `${r.title} ${r.description || ''} ${r.module || ''}`.toLowerCase()
        return prWords.some(w => text.includes(w))
      })
      if (coreMatch) return coreMatch
    }

    // 3. 跨类型+类型关键词匹配（PathResource type 可能不准确）
    const typeKeywords: Record<string, string[]> = {
      'video': ['视频', '教学视频', '动画', '演示视频'],
      'exercise': ['练习', '题', '测试', '习题', '测验'],
      'code': ['代码', '编程', '实战', '示例', '程序'],
      'mindmap': ['导图', '思维导图', '知识图谱', '概念图'],
      'document': ['文档', '讲解', '详解', '教程', '笔记'],
      'extension': ['拓展', '延伸', '进阶', '参考'],
    }
    if (pr.type !== 'document' && typeKeywords[pr.type]) {
      const typeKws = typeKeywords[pr.type]
      const crossTypeMatch = available.find(r => {
        const rt = (r.title || '').toLowerCase()
        return typeKws.some(kw => rt.includes(kw)) && prWords.some(w => w.length >= 2 && rt.includes(w))
      })
      if (crossTypeMatch) return crossTypeMatch
    }

    // 4. 纯核心词匹配（最终兜底）
    if (prWords.length > 0) {
      const wordMatch = available.find(r => {
        const text = `${r.title} ${r.description || ''} ${r.module || ''}`.toLowerCase()
        return prWords.filter(w => w.length >= 2 && text.includes(w)).length >= 2
      })
      if (wordMatch) return wordMatch
    }

    return null
  }

  /** 从文本中提取核心词（去掉通用后缀，保留 2-4 字的子串） */
  function extractCoreWords(text: string): string[] {
    const stripped = text
      .replace(/基础|进阶|综合|专项|突破|概念|应用|实战|复习|入门|高级|中级|初级|详解|教程|指南|笔记|讲解|演示|练习|实战|模板|导图|图谱|视频|代码/g, '')
      .trim()
    const words: string[] = []
    if (stripped.length >= 2) {
      words.push(stripped.toLowerCase())
    }
    for (let len = 2; len <= Math.min(4, text.length); len++) {
      for (let i = 0; i <= text.length - len; i++) {
        const sub = text.substring(i, i + len)
        if (!/基础|进阶|综合|专项|实战|详解|教程|指南|讲解|演示|练习/.test(sub)) {
          words.push(sub.toLowerCase())
        }
      }
    }
    return [...new Set(words)]
  }

  /** 将 PathResource 转为 ResourceItem（未在资源库中匹配到时使用） */
  function pathResourceToItem(pr: PathResource, stage: PathStageExtended): ResourceItem {
    return {
      id: pr.id,
      title: pr.name,
      type: pr.type,
      module: stage.title,
      createdAt: new Date().toISOString(),
      content: '',
      status: pr.status,
    }
  }

  /** 当前选中的资源（带完整 content） */
  const selectedResource = computed<ResourceItem | null>(() => {
    if (!selectedResourceId.value) return null

    // 1. 按 ID 精确匹配资源库
    const found = allResources.value.find(r => r.id === selectedResourceId.value)
    if (found) return found

    // 2. 从路径阶段找到 PathResource，通过 resourceRef 查找（不再做模糊匹配，避免跨阶段复用同一资源）
    for (const stage of stages.value) {
      const pr = stage.resources?.find(r => r.id === selectedResourceId.value)
      if (pr) {
        // 通过 resourceRef 查找
        if (pr.resourceRef) {
          const byRef = allResources.value.find(r => r.id === pr.resourceRef)
          if (byRef) return byRef
        }
        // 没有 resourceRef → 返回 fallback（无内容）
        return pathResourceToItem(pr, stage)
      }
    }
    return null
  })

  /** 选中资源 */
  function selectResource(resourceId: string) {
    selectedResourceId.value = resourceId
  }

  /** 清除选中 */
  function clearSelection() {
    selectedResourceId.value = null
  }

  /** 切换阶段展开/折叠 */
  function toggleStage(stageId: string) {
    const set = new Set(expandedStages.value)
    if (set.has(stageId)) {
      set.delete(stageId)
    } else {
      set.add(stageId)
    }
    expandedStages.value = set
  }

  /** 是否展开 */
  function isStageExpanded(stageId: string): boolean {
    return expandedStages.value.has(stageId)
  }

  /** 阶段的完成进度 */
  function getStageProgress(stage: PathStageExtended): number {
    if (stage.progress !== undefined && stage.progress > 0) return stage.progress
    if (!stage.resources || stage.resources.length === 0) return 0
    const completed = stage.resources.filter(r => r.status === 'completed').length
    return Math.round((completed / stage.resources.length) * 100)
  }

  /** 标记资源完成（同时更新 pathStore 和 resourceStore） */
  function markResourceComplete(resourceId: string) {
    // 在路径阶段中找到资源并调用 pathStore.completeResource
    for (const stage of stages.value) {
      const pr = stage.resources?.find(r => r.id === resourceId || r.resourceRef === resourceId)
      if (pr) {
        pathStore.completeResource(stage.id, pr.id)
        break
      }
    }
    // 如果资源库中也有这个资源，更新其状态
    const resItem = allResources.value.find(r => r.id === resourceId)
    if (resItem) {
      resourceStore.completeResource(resourceId)
    }
  }

  return {
    selectedResourceId, expandedStages,
    stages, allResources, selectedResource,
    getStageResources, selectResource, clearSelection,
    toggleStage, isStageExpanded, getStageProgress,
    markResourceComplete,
  }
})
