import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import request from '../../../shared/utils/request'
import type { ResourceItem, LearningEvent } from '../../../shared/types'
import { chatGLM } from '../../../shared/api/glmApi'
import {
  buildResourceMessages, buildMindmapMessages,
  buildCodeMessages, buildVideoMessages,
  buildKnowledgeGraphMessages,
} from '../prompts/resourcePrompts'
import { useProfileStore } from '../../profile/stores/profileStore'
import { useAuthStore } from '../../auth/stores/authStore'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'
import {
  extractCodeBlock,
  safeJsonParse,
  parseResourceList,
} from '../../../shared/utils/llmParsing'

const RESOURCE_STORAGE_KEY = 'ai_learning_resources'

// 按 subject 隔离的 storage key（修复跨科目资源污染）
function _currentSubject(): string {
  try {
    const profileStore = useProfileStore()
    return profileStore.profileData.currentSubject || profileStore.profileData.major || 'default'
  } catch { return 'default' }
}

function resourceStorageKey(userId: string): string {
  return `${RESOURCE_STORAGE_KEY}_${userId}_${_currentSubject()}`
}

/** 迁移旧格式存储（无 subject 后缀）到当前 subject 的 key */
function migrateLegacyResourceStorage(userId: string) {
  const newKey = resourceStorageKey(userId)
  if (localStorage.getItem(newKey)) return
  const legacyKey = `${RESOURCE_STORAGE_KEY}_${userId}`
  const legacy = localStorage.getItem(legacyKey)
  if (legacy) {
    try {
      const parsed = JSON.parse(legacy)
      if (Array.isArray(parsed) && parsed.length > 0) {
        localStorage.setItem(newKey, legacy)
        console.log(`[Resource] 迁移旧资源数据到 subject=${_currentSubject()}（${parsed.length} 项）`)
      }
      localStorage.removeItem(legacyKey)
    } catch { /* ignore */ }
  }
}

const FALLBACK_RESOURCES: ResourceItem[] = [
  {
    id: 'fb-doc-1', title: '链表基础讲解', type: 'document', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    content: '## 链表基础\n\n**链表**是一种动态数据结构，每个节点包含数据和指向下一个节点的指针。\n\n### 基本操作\n- 插入：O(1)\n- 删除：O(1)\n- 查找：O(n)\n\n与数组对比：链表插入删除快，数组随机访问快。',
  },
  {
    id: 'fb-mindmap-1', title: '链表知识导图', type: 'mindmap', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    content: '# 链表知识体系\n\n## 基础概念\n### 节点结构\n数据域 + 指针域\n\n### 单链表\n每个节点指向下一个节点\n\n### 双链表\n节点同时指向前驱和后继\n\n### 循环链表\n尾节点指向头节点\n\n## 基本操作\n### 插入\n头插法 / 尾插法，O(1)\n\n### 删除\n修改指针指向，O(1)\n\n### 查找\n遍历链表，O(n)\n\n## 进阶应用\n### 跳表\n多级索引加速查找\n\n### 哨兵节点\n简化边界条件处理',
  },
  {
    id: 'fb-graph-1', title: '链表知识关联图谱', type: 'knowledge-graph', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    content: JSON.stringify({
      nodes: [
        { id: 'node', name: '节点', category: 'core', importance: 5, desc: '链表基本单元' },
        { id: 'pointer', name: '指针', category: 'core', importance: 5, desc: '连接节点的引用' },
        { id: 'singly', name: '单链表', category: 'algorithm', importance: 4, desc: '单向遍历链表' },
        { id: 'doubly', name: '双链表', category: 'algorithm', importance: 3, desc: '双向遍历链表' },
        { id: 'insert', name: '插入操作', category: 'application', importance: 4, desc: 'O(1) 时间复杂度' },
        { id: 'delete', name: '删除操作', category: 'application', importance: 4, desc: 'O(1) 时间复杂度' },
      ],
      edges: [
        { source: 'node', target: 'pointer', label: '包含' },
        { source: 'pointer', target: 'singly', label: '组成' },
        { source: 'pointer', target: 'doubly', label: '组成' },
        { source: 'singly', target: 'insert', label: '支持' },
        { source: 'singly', target: 'delete', label: '支持' },
      ],
    }),
  },
  {
    id: 'fb-code-1', title: '链表 Python 实现', type: 'code', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    content: 'class Node:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\nclass LinkedList:\n    def __init__(self):\n        self.head = None\n\n    def append(self, val):\n        if not self.head:\n            self.head = Node(val)\n            return\n        cur = self.head\n        while cur.next:\n            cur = cur.next\n        cur.next = Node(val)',
  },
  {
    id: 'fb-ex-1', title: '链表练习题', type: 'exercise', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    content: '### 题目1：反转链表\n给定单链表的头节点 head，反转链表并返回反转后的链表。\n\n**提示**：使用迭代或递归方法。\n\n### 题目2：合并两个有序链表\n将两个升序链表合并为一个新的升序链表并返回。',
  },
  {
    id: 'fb-vid-1', title: 'B站-数据结构-链表动画讲解', type: 'video', module: '链表',
    createdAt: new Date().toISOString(), aiGenerated: false, difficulty: 'beginner',
    description: '用动画方式演示链表的插入和删除过程',
    url: 'https://search.bilibili.com/all?keyword=数据结构+链表+动画讲解',
  },
]

/** 从 JSON 树结构递归转为 Markdown 标题（供 markmap 渲染） */
function treeToMarkdown(node: any, depth = 0): string {
  if (!node || !node.name) return ''
  const indent = '#'.repeat(Math.min(depth + 1, 6))
  const highlight = node.highlight ? '🔴 ' : ''
  let md = `${indent} ${highlight}${node.name}\n`
  if (node.desc) {
    md += `${node.desc}\n\n`
  }
  if (node.children && Array.isArray(node.children)) {
    for (const child of node.children) {
      md += treeToMarkdown(child, depth + 1)
    }
  }
  return md
}

/** 解析导图原始输出：提取 mindmap-data 代码块 → JSON 解析 → treeToMarkdown 转换 */
function parseMindmapData(raw: string, topic: string, weakPoints: string[]): string {
  const block = extractCodeBlock(raw, 'mindmap-data')
  if (block) {
    const tree = safeJsonParse(block)
    if (tree && tree.name) {
      const md = treeToMarkdown(tree)
      if (md.trim()) return md
    }
  }
  // fallback：尝试从原始文本中提取 JSON 对象
  const objMatch = raw.match(/\{[\s\S]*"name"[\s\S]*\}/)
  if (objMatch) {
    const tree = safeJsonParse(objMatch[0])
    if (tree && tree.name) {
      const md = treeToMarkdown(tree)
      if (md.trim()) return md
    }
  }
  // fallback：将原始文本中每个 # 标题行提取出来拼成简易导图
  return getFallbackMindmap(topic, weakPoints)
}

/** 导图 fallback 模板 */
function getFallbackMindmap(topic: string, _weakPoints: string[] = []): string {
  return `# ${topic} 知识体系

## 基础概念
### 核心定义
### 术语解释

## 基本原理
### 工作机制
### 核心思想

## 常用方法
### 经典算法
### 实现技巧

## 实践应用
### 典型场景
### 工具框架

## 进阶拓展
### 高级主题
### 前沿方向`
}

/** 解析知识图谱原始输出：提取 knowledge-graph 代码块 → JSON 验证 */
function parseKnowledgeGraphData(raw: string, topic: string, weakPoints: string[]): string {
  const block = extractCodeBlock(raw, 'knowledge-graph')
  if (block) {
    const graph = safeJsonParse(block)
    if (graph && graph.nodes && Array.isArray(graph.nodes) && graph.nodes.length > 0 &&
        graph.edges && Array.isArray(graph.edges)) {
      // 验证节点 ID 唯一性
      const nodeIds = new Set(graph.nodes.map((n: any) => n.id))
      if (nodeIds.size === graph.nodes.length) {
        // 验证边的 source/target 存在
        const edgesValid = graph.edges.every(
          (e: any) => nodeIds.has(e.source) && nodeIds.has(e.target)
        )
        if (edgesValid) {
          return JSON.stringify(graph)
        }
      }
    }
  }
  // fallback：尝试从原始文本中提取 JSON 对象
  const objMatch = raw.match(/\{[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}/)
  if (objMatch) {
    const graph = safeJsonParse(objMatch[0])
    if (graph && graph.nodes && Array.isArray(graph.nodes) && graph.nodes.length > 0 &&
        graph.edges && Array.isArray(graph.edges)) {
      const nodeIds = new Set(graph.nodes.map((n: any) => n.id))
      if (nodeIds.size === graph.nodes.length) {
        const edgesValid = graph.edges.every(
          (e: any) => nodeIds.has(e.source) && nodeIds.has(e.target)
        )
        if (edgesValid) {
          return JSON.stringify(graph)
        }
      }
    }
  }
  return getFallbackKnowledgeGraph(topic, weakPoints)
}

/** 知识图谱 fallback 模板 */
function getFallbackKnowledgeGraph(_topic: string, _weakPoints: string[] = []): string {
  const graph = {
    nodes: [
      { id: 'basics', name: '基础概念', category: 'core', importance: 5, desc: '核心定义和术语' },
      { id: 'principles', name: '基本原理', category: 'core', importance: 4, desc: '核心工作机制' },
      { id: 'methods', name: '主要方法', category: 'algorithm', importance: 4, desc: '常用技术方法' },
      { id: 'tools', name: '工具框架', category: 'application', importance: 3, desc: '相关工具和框架' },
      { id: 'practice', name: '实践应用', category: 'application', importance: 3, desc: '典型应用场景' },
      { id: 'advanced', name: '进阶内容', category: 'advanced', importance: 2, desc: '深入扩展知识' },
    ],
    edges: [
      { source: 'basics', target: 'principles', label: '基础' },
      { source: 'principles', target: 'methods', label: '支撑' },
      { source: 'methods', target: 'tools', label: '实现' },
      { source: 'tools', target: 'practice', label: '应用' },
      { source: 'practice', target: 'advanced', label: '进阶' },
    ],
  }
  return JSON.stringify(graph)
}

export const useResourceStore = defineStore('resource', () => {
  /* ===== 从后端加载资源（优先），失败时 fallback localStorage ===== */
  async function loadResources(): Promise<ResourceItem[]> {
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'

      // 1. 从 localStorage 加载（本地可能有完整的 content）
      let localResources: ResourceItem[] = []
      try {
        migrateLegacyResourceStorage(userId)
        const stored = localStorage.getItem(resourceStorageKey(userId))
        if (stored) {
          const parsed = JSON.parse(stored)
          if (Array.isArray(parsed) && parsed.length > 0) localResources = parsed
        }
      } catch { /* ignore */ }

      // 2. 如果已登录，也从后端加载
      if (authStore.token && authStore.user?.id) {
        try {
          const res = await request.get('/data/resources')
          if (res.data && Array.isArray(res.data.resources) && res.data.resources.length > 0) {
            const backendResources: ResourceItem[] = res.data.resources

            // 合并策略：本地有 content 的资源优先，后端无 content 的种子资源降级
            const localById = new Map(localResources.map(r => [r.id, r]))
            const localByType = new Map<string, ResourceItem[]>()
            for (const lr of localResources) {
              if (!localByType.has(lr.type)) localByType.set(lr.type, [])
              localByType.get(lr.type)!.push(lr)
            }

            const merged: ResourceItem[] = []

            // 先添加本地有 content 的资源（AI 生成的真实数据）
            for (const lr of localResources) {
              merged.push(lr)
            }

            // 再添加后端资源，但跳过同类型已有本地 content 的（避免匹配到无 content 种子资源）
            const mergedIds = new Set(merged.map(r => r.id))
            for (const br of backendResources) {
              // 已存在同 ID 的本地资源，跳过
              if (mergedIds.has(br.id)) continue

              // 同类型本地已有带 content 的资源，跳过后端无 content 的种子
              const sameTypeLocals = localByType.get(br.type) || []
              if (!br.content && sameTypeLocals.some(l => l.content)) continue

              merged.push(br)
              mergedIds.add(br.id)
            }

            return merged
          }
        } catch (e: any) {
          if (e.response?.status !== 401 && e.response?.status !== 403) {
            console.warn('[Resource] 后端加载失败，fallback 到 localStorage', e)
          }
        }
      }

      // 3. 后端无数据或未登录，直接用 localStorage
      if (localResources.length > 0) return localResources
    } catch (e) {
      console.warn('[Resource] 加载资源失败', e)
    }
    // 无数据时返回空数组，不返回 fallback 种子资源
    // 种子资源只在首次使用时由智能体生成，不应在用户删除后自动恢复
    return []
  }

  const resources = ref<ResourceItem[]>([])
  const resourcesReady = ref(false)
  const selectedId = ref<string | null>(null)
  const isGenerating = ref(false)
  const generationStatus = ref<'idle' | 'generating' | 'done' | 'error'>('idle')

  // 异步初始化
  ;(async () => {
    const loaded = await loadResources()
    // 数据迁移：taskId → video_task_id
    for (const r of loaded) {
      if ((r as any).taskId && !r.video_task_id) {
        r.video_task_id = (r as any).taskId
      }
    }
    resources.value = loaded
    resourcesReady.value = true
  })()

  /* ===== 持久化到 localStorage + 同步到后端 ===== */
  function saveResources() {
    // 1. 先存 localStorage（同步，快速）
    try {
      const authStore = useAuthStore()
      const userId = authStore.user?.id || 'guest'
      localStorage.setItem(resourceStorageKey(userId), JSON.stringify(resources.value))
    } catch (e) {
      console.warn('[Resource] localStorage 保存失败', e)
    }

    // 2. 异步同步到后端（不阻塞 UI）
    syncToBackend()
  }

  let syncTimer: ReturnType<typeof setTimeout> | null = null
  function syncToBackend() {
    const authStore = useAuthStore()
    if (!authStore.token || !authStore.user?.id) return // 未登录不同步

    if (syncTimer) clearTimeout(syncTimer)
    syncTimer = setTimeout(async () => {
      try {
        await request.put('/data/resources', {
          data: { resources: JSON.parse(JSON.stringify(resources.value)) },
        })
        console.log('[Resource] 后端同步完成')
      } catch (e) {
        console.warn('[Resource] 后端同步失败', e)
      }
    }, 2000) // 2秒防抖，减少请求频率
  }

  // 监听资源变化自动持久化（防抖 500ms → localStorage；2s → 后端）
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    () => resources.value,
    () => {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => saveResources(), 500)
    },
    { deep: true },
  )

  // 监听用户切换，重新加载资源
  watch(
    () => {
      try {
        const authStore = useAuthStore()
        return authStore.user?.id || 'guest'
      } catch { return 'guest' }
    },
    async () => {
      resources.value = await loadResources()
    },
  )

  // 监听科目切换，自动重新加载资源（架构加固：兜底机制）
  // 即使不通过 switchSubject 显式调用，任何 currentSubject 变化都能触发 reload
  watch(
    () => {
      try {
        const profileStore = useProfileStore()
        return profileStore.profileData.currentSubject || ''
      } catch { return '' }
    },
    async (newSubject, oldSubject) => {
      if (newSubject && oldSubject && newSubject !== oldSubject) {
        console.log(`[Resource] 检测到科目切换: ${oldSubject} → ${newSubject}, 重新加载资源`)
        await reloadForCurrentSubject()
      }
    },
  )

  const selectedResource = computed(() =>
    resources.value.find(r => r.id === selectedId.value) || null
  )

  const resourcesByType = computed(() => {
    const map: Record<string, ResourceItem[]> = {}
    for (const r of resources.value) {
      const key = r.type || 'document'
      if (!map[key]) map[key] = []
      map[key].push(r)
    }
    return map
  })

  function selectResource(id: string) {
    selectedId.value = id
  }

  /** 智能体调用：批量添加资源 */
  function addResources(items: ResourceItem[]) {
    resources.value.push(...items)
  }

  /** ★ 随学随新：增量添加资源，不清空已有资源 */
  function addIncrementalResources(items: ResourceItem[], subject?: string) {
    // 为没有 subject 的资源补充科目信息
    if (subject) {
      for (const item of items) {
        if (!item.subject) item.subject = subject
      }
    }
    const newItems: ResourceItem[] = []
    for (const item of items) {
      let matched = false

      // Level 1: ID 精确匹配（最可靠，视频占位资源与完成资源 ID 相同）
      const byId = resources.value.find(r => r.id === item.id)
      if (byId) {
        if (item.url) byId.url = item.url
        if (item.videoStatus) byId.videoStatus = item.videoStatus
        if (item.video_task_id) byId.video_task_id = item.video_task_id
        if (item.description) byId.description = item.description
        matched = true
      }

      // Level 2: video_task_id 匹配（视频场景：占位资源和完成资源可能有不同 ID 但共享 task_id）
      if (!matched && item.video_task_id) {
        const byTaskId = resources.value.find(r => r.video_task_id === item.video_task_id)
        if (byTaskId) {
          if (item.url) byTaskId.url = item.url
          if (item.videoStatus) byTaskId.videoStatus = item.videoStatus
          matched = true
        }
      }

      // Level 3: title 匹配（兜底：不同 ID 但同标题的资源）
      if (!matched) {
        const existing = resources.value.find(r => r.title === item.title)
        if (existing) {
          if (item.url) existing.url = item.url
          if (item.videoStatus) existing.videoStatus = item.videoStatus
          if (item.video_task_id) existing.video_task_id = item.video_task_id
          matched = true
        }
      }

      if (!matched) {
        newItems.push(item)
      }
    }
    if (newItems.length > 0) {
      resources.value.push(...newItems)
    }
  }

  /** 智能体调用：清空并设置全部资源（合并已有URL，防止覆盖用户重新生成的视频） */
  function clearAndSetResources(items: ResourceItem[], subject?: string) {
    // 合并而非覆盖：保留旧资源中有 content/url/videoStatus 的，新资源优先
    const existingMap = new Map(resources.value.map(r => [r.id, r]))
    const mergedItems = items.map(item => {
      // 补充 subject（如果资源没有指定科目）
      if (!item.subject && subject) item.subject = subject
      const existing = existingMap.get(item.id)
      if (existing) {
        if (existing.content && !item.content) item.content = existing.content
        if (existing.url && !item.url) item.url = existing.url
        // 终态状态（done/failed）优先：不能被 placeholder 的 'pending' 覆盖
        // 否则后台轮询已更新的 'failed'/'done' 会被旧 placeholder 的 'pending' 重置，导致进度条卡住
        const TERMINAL = ['done', 'failed']
        if (existing.videoStatus) {
          if (!item.videoStatus || TERMINAL.includes(existing.videoStatus)) {
            item.videoStatus = existing.videoStatus
          }
        }
        if (existing.video_task_id && !item.video_task_id) item.video_task_id = existing.video_task_id
        existingMap.delete(item.id)
      }
      return item
    })
    for (const [, old] of existingMap) {
      if (!mergedItems.find(n => n.id === old.id)) {
        mergedItems.push(old)
      }
    }
    resources.value = mergedItems
    generationStatus.value = 'done'
  }

  /** 手动刷新：重新调用 GLM API 生成全部资源 */
  async function generateResources() {
    const profileStore = useProfileStore()
    isGenerating.value = true
    generationStatus.value = 'generating'

    const profileData = profileStore.profileData
    // 无薄弱点时使用当前科目作为默认主题，而非硬编码的"数据结构基础"
    const subject = profileData.currentSubject || profileData.major || '计算机'
    // ★ 过滤跨科目污染的薄弱点（如英语科目中的"递归"等CS内容）
    const rawWeakPoints = profileData.weak_points || []
    const relevantWeakPoints = filterRelevantWeakPoints(rawWeakPoints, subject)
    const weakPoints = relevantWeakPoints.length > 0 ? relevantWeakPoints : [`${subject}基础`]
    const topic = weakPoints[0]

    const allResources: ResourceItem[] = []

    const tasks = [
      { builder: buildResourceMessages, codeType: 'resource-list', label: '文档' },
      { builder: buildMindmapMessages, codeType: 'mindmap-data', label: '导图' },
      { builder: buildKnowledgeGraphMessages, codeType: 'knowledge-graph', label: '图谱' },
      { builder: buildCodeMessages, codeType: 'code-example', label: '代码' },
      { builder: buildVideoMessages, codeType: 'resource-list', label: '视频' },
    ]

    for (const task of tasks) {
      try {
        const raw = await callGLM(task.builder(profileData, topic))
        if (task.codeType === 'resource-list') {
          allResources.push(...parseResourceList(raw))
        } else if (task.codeType === 'mindmap-data') {
          const content = parseMindmapData(raw, topic, weakPoints)
          allResources.push({
            id: `res-mindmap-${Date.now()}`,
            title: `${topic} 知识导图`,
            type: 'mindmap',
            module: topic,
            content,
            createdAt: new Date().toISOString(),
            aiGenerated: true,
          })
        } else if (task.codeType === 'knowledge-graph') {
          const content = parseKnowledgeGraphData(raw, topic, weakPoints)
          allResources.push({
            id: `res-knowledge-graph-${Date.now()}`,
            title: `${topic} 知识关联图谱`,
            type: 'knowledge-graph',
            module: topic,
            content,
            createdAt: new Date().toISOString(),
            aiGenerated: true,
          })
        } else if (task.codeType === 'code-example') {
          const block = extractCodeBlock(raw, 'code-example')
          let codeContent = raw
          if (block) {
            const parsed = safeJsonParse(block)
            if (parsed && parsed.code) {
              codeContent = parsed.code
            } else if (parsed && parsed.explanation) {
              codeContent = `// ${parsed.title || '代码示例'}\n// ${parsed.explanation}\n\n${parsed.code || block}`
            } else {
              codeContent = block
            }
          }
          allResources.push({
            id: `res-code-${Date.now()}`,
            title: `${topic} 代码示例`,
            type: 'code',
            module: topic,
            content: codeContent,
            createdAt: new Date().toISOString(),
            aiGenerated: true,
          })
        }
      } catch (e) {
        console.warn(`[Resource] ${task.label}生成失败:`, e)
      }
    }

    if (allResources.length > 0) {
      resources.value = allResources
      generationStatus.value = 'done'
    } else {
      resources.value = []
      generationStatus.value = 'error'
    }

    isGenerating.value = false
  }

  function callGLM(messages: { role: 'system' | 'user' | 'assistant'; content: string }[]): Promise<string> {
    return new Promise((resolve, reject) => {
      let rawContent = ''
      let hasError = false
      chatGLM(
        messages,
        (text) => { rawContent += text },
        () => {
          // 流完成：即使内容很短也返回，让上层解析决定是否使用
          resolve(rawContent)
        },
        (error) => {
          hasError = true
          console.error('[Resource] GLM API 调用失败:', error.message)
          // 如果已经收到了部分内容，返回部分内容而非空字符串
          if (rawContent.trim()) {
            console.warn('[Resource] 使用已接收的部分内容（可能不完整）')
            resolve(rawContent)
          } else {
            reject(error)
          }
        },
      )
    })
  }

  /** 标记资源为已完成，并触绘画像增量更新 */
  function completeResource(resourceId: string) {
    const resource = resources.value.find(r => r.id === resourceId)
    if (!resource) return

    // 更新资源状态
    resource.status = 'completed'
    resource.completedAt = new Date().toISOString()

    // 触绘画像更新（仅用户主动完成才触发）
    const profileStore = useProfileStore()
    const event: LearningEvent = {
      type: 'resource_complete',
      timestamp: new Date().toISOString(),
      sourceId: resourceId,
      description: `完成学习资源：${resource.title}`,
      knowledgePoints: extractKnowledgePoints(resource.module || resource.title),
      resourceType: resource.type,
    }
    profileStore.applyLearningEvent(event)
  }

  /** 从资源标题/模块中提取知识点 */
  function extractKnowledgePoints(text: string): string[] {
    const keywords = ['数组', '链表', '栈', '队列', '树', '二叉树', '图', '哈希', '排序',
      '查找', '递归', '动态规划', '贪心', '回溯', '分治', '堆', '字符串', '基础', '进阶', '综合']
    return keywords.filter(kw => text.includes(kw))
  }

  /** 删除单个资源 */
  function removeResource(id: string) {
    const index = resources.value.findIndex(r => r.id === id)
    if (index > -1) {
      resources.value.splice(index, 1)
      saveResources()
    }
  }

  /** 清空所有资源 */
  function clearAllResources() {
    resources.value = []
    saveResources()
  }

  /** 切换科目时调用：按当前 subject 重新加载资源
   *  修复跨科目污染：不清空会导致英语会话资源中心显示数据结构视频
   */
  async function reloadForCurrentSubject() {
    const loaded = await loadResources()
    // 数据迁移：taskId → video_task_id
    for (const r of loaded) {
      if ((r as any).taskId && !r.video_task_id) {
        r.video_task_id = (r as any).taskId
      }
    }
    resources.value = loaded
    resourcesReady.value = true
  }

  // ===== 视频生成任务持久化状态 =====
  // 解决问题：点击生成视频后切换卡片再回来，进度消失
  interface VideoGenerationTask {
    taskId: string
    resourceId: string
    title: string
    progress: number
    statusMessage: string
    currentStage: string
    startTime: number
    retryCount: number
    generating: boolean
    estimatedTimeRemaining: string
  }

  const videoGenerationTasks = ref<Map<string, VideoGenerationTask>>(new Map())

  /** 开始视频生成任务 */
  function startVideoGeneration(resourceId: string, title: string, taskId: string) {
    videoGenerationTasks.value.set(resourceId, {
      taskId,
      resourceId,
      title,
      progress: 0,
      statusMessage: '任务已创建，开始生成...',
      currentStage: '正在初始化任务...',
      startTime: Date.now(),
      retryCount: 0,
      generating: true,
      estimatedTimeRemaining: '计算中...',
    })
  }

  /** 更新视频生成进度 */
  function updateVideoGenerationProgress(resourceId: string, progress: number, message: string, stage: string) {
    const task = videoGenerationTasks.value.get(resourceId)
    if (task) {
      task.progress = progress
      task.statusMessage = message
      task.currentStage = stage

      // 计算预计剩余时间
      if (progress > 0) {
        const elapsed = Date.now() - task.startTime
        const totalEstimated = (elapsed / progress) * 100
        const remaining = totalEstimated - elapsed
        if (remaining < 60000) {
          task.estimatedTimeRemaining = `约 ${Math.ceil(remaining / 1000)} 秒`
        } else {
          task.estimatedTimeRemaining = `约 ${Math.ceil(remaining / 60000)} 分钟`
        }
      }
    }
  }

  /** 完成视频生成 */
  function completeVideoGeneration(resourceId: string) {
    videoGenerationTasks.value.delete(resourceId)
    // 更新资源的 videoStatus
    const resource = resources.value.find(r => r.id === resourceId)
    if (resource) {
      resource.videoStatus = 'done'
      saveResources()
    }
  }

  /** 取消视频生成 */
  function cancelVideoGeneration(resourceId: string) {
    videoGenerationTasks.value.delete(resourceId)
  }

  /** 获取视频生成任务状态 */
  function getVideoGenerationTask(resourceId: string): VideoGenerationTask | undefined {
    return videoGenerationTasks.value.get(resourceId)
  }

  /** 更新重试次数 */
  function updateVideoRetryCount(resourceId: string, count: number) {
    const task = videoGenerationTasks.value.get(resourceId)
    if (task) {
      task.retryCount = count
    }
  }

  /** 标记视频生成失败 */
  function failVideoGeneration(resourceId: string, message: string) {
    const task = videoGenerationTasks.value.get(resourceId)
    if (task) {
      task.generating = false
      task.statusMessage = message
      task.currentStage = '生成失败'
    }
    // 更新资源的 videoStatus
    const resource = resources.value.find(r => r.id === resourceId)
    if (resource) {
      resource.videoStatus = 'failed'
      resource.description = message
      saveResources()
    }
  }

  /* ===== 资源管理：收藏 / 掌握 / 评分 ===== */

  function toggleFavorite(id: string) {
    const r = resources.value.find(item => item.id === id)
    if (!r) return
    r.favorited = !r.favorited
    saveResources()
  }

  function markMastered(id: string, mastered = true) {
    const r = resources.value.find(item => item.id === id)
    if (!r) return
    r.mastered = mastered
    r.completedAt = mastered ? new Date().toISOString() : undefined
    saveResources()
  }

  function rateResource(id: string, rating: number) {
    const r = resources.value.find(item => item.id === id)
    if (!r) return
    const clamped = Math.max(0, Math.min(5, Math.round(rating)))
    r.rating = clamped
    saveResources()
  }

  return {
    resources, resourcesReady, selectedId, selectedResource, resourcesByType,
    isGenerating, generationStatus,
    selectResource, addResources, addIncrementalResources, clearAndSetResources, generateResources,
    completeResource, saveResources, removeResource, clearAllResources, reloadForCurrentSubject,
    // 视频生成任务持久化
    videoGenerationTasks,
    startVideoGeneration, updateVideoGenerationProgress, completeVideoGeneration,
    cancelVideoGeneration, getVideoGenerationTask, updateVideoRetryCount, failVideoGeneration,
    // 资源管理
    toggleFavorite, markMastered, rateResource,
  }
})