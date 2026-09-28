<template>
  <Teleport to="body" :disabled="!isMounted">
    <Transition name="modal">
      <div v-if="visible && isMounted" class="modal-overlay" @click.self="handleClose">
        <div class="modal-box" role="dialog" aria-labelledby="learning-title">
          <!-- 头部 -->
          <div class="modal-header">
            <div class="header-left">
              <span class="res-type-icon">{{ typeIcon }}</span>
              <span id="learning-title" class="modal-title">{{ resource?.name }}</span>
            </div>
            <div class="header-right">
              <span class="reading-time" :class="{ warning: !contentReady || readingTime < minReadingTime }">
                {{ readingTimeFormatted }}
              </span>
              <button class="modal-close" aria-label="关闭弹窗" @click="handleClose">✕</button>
            </div>
          </div>

          <!-- 进度提示 -->
          <div class="progress-tip" :class="{ complete: canComplete, generating: isGenerating }">
            <span class="tip-icon">{{ canComplete ? '✅' : isGenerating ? '🤖' : '📖' }}</span>
            <span class="tip-text">
              {{ progressTip }}
            </span>
          </div>

          <!-- 内容区域 -->
          <div class="modal-body" ref="contentRef" @scroll="handleScroll">
            <div class="content-wrapper">
              <!-- 资源描述 -->
              <div v-if="resourceData?.description" class="resource-desc">
                {{ resourceData.description }}
              </div>

              <!-- Agent 生成状态 -->
              <div v-if="isGenerating" class="generating-tip">
                <span class="generating-icon">🤖</span>
                <span class="generating-text">正在生成学习内容...</span>
                <span class="generating-dots">
                  <span></span><span></span><span></span>
                </span>
              </div>

              <!-- 知识图谱：使用 ECharts 渲染（优先用已存储内容，回退到后端加载的 generatedContent） -->
              <div v-if="isKnowledgeGraph && (storedContent || generatedContent)" class="resource-content graph-content">
                <KnowledgeGraph :content="storedContent || generatedContent" :weak-points="weakPoints" />
              </div>

              <!-- 思维导图：使用 MindMapViewer（同上回退逻辑） -->
              <div v-else-if="isMindmap && (storedContent || generatedContent)" class="resource-content mindmap-content">
                <MindMapViewer :content="storedContent || generatedContent" />
              </div>

              <!-- 视频：展示视频播放器或渲染状态 -->
              <div v-else-if="isVideo && storedResource" class="resource-content video-content">
                <template v-if="storedResource.videoStatus === 'done' && storedResource.url">
                  <video controls :src="storedResource.url" class="video-player" style="width:100%;border-radius:8px;"></video>
                </template>
                <template v-else-if="storedResource.videoStatus === 'pending'">
                  <div class="video-pending">
                    <span class="pending-icon">🎬</span>
                    <span>视频正在后台渲染中，完成后将自动显示...</span>
                  </div>
                </template>
                <template v-else-if="storedResource.videoStatus === 'failed'">
                  <div class="video-failed">
                    <span class="failed-icon">⚠️</span>
                    <span>视频生成失败</span>
                    <a v-if="bilibiliSearchUrl" :href="bilibiliSearchUrl" target="_blank" class="video-link bilibili-search">
                      <span class="video-icon">🔍</span> 在B站搜索：{{ resource?.name }}
                    </a>
                  </div>
                </template>
                <template v-else>
                  <div class="markdown-body" v-html="renderMarkdown(generatedContent)"></div>
                </template>
              </div>

              <!-- Agent 生成的流式内容（文档/练习题等 Markdown） -->
              <div v-else-if="generatedContent" class="resource-content">
                <div class="markdown-body" v-html="renderMarkdown(generatedContent)"></div>
              </div>

              <!-- 暂无匹配资源（allocator 缺口：资源库中无适合此小节的资源） -->
              <div v-else-if="needsGeneration" class="no-content">
                <span class="no-content-icon">📭</span>
                <span class="no-content-text">该小节暂无匹配资源</span>
                <span class="no-content-hint">资源库中没有适合此小节的资源。点击下方按钮，为此小节单独生成。</span>
                <button class="retry-btn" @click="generateForStage">为此小节生成资源</button>
              </div>

              <!-- 无内容提示 -->
              <div v-else-if="!isGenerating && contentLoadFailed" class="no-content">
                <span class="no-content-icon">⚠️</span>
                <span class="no-content-text">内容生成失败</span>
                <button class="retry-btn" @click="loadResourceContent">重新生成</button>
              </div>

              <!-- 底部占位 -->
              <div class="content-footer"></div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="modal-footer">
            <button class="btn-cancel" aria-label="稍后继续" @click="handleClose">
              稍后继续
            </button>
            <button 
              class="btn-complete" 
              :disabled="!canComplete"
              aria-label="完成学习"
              @click="handleComplete"
            >
              {{ completeButtonText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import type { PathResource } from '../../../shared/types'
import { RESOURCE_TYPE_MAP } from '../../../shared/utils/constants'
import { getDetail } from '../../resource/api/resourceApi'
import { generateResourceContent } from '../../agent/api/agentApi'
import { completeLearning, saveContent } from '../api/learningApi'
import { useProfileStore } from '../../profile/stores/profileStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import KnowledgeGraph from '../../resource/components/KnowledgeGraph.vue'
import MindMapViewer from '../../resource/components/MindMapViewer.vue'

const props = defineProps<{
  visible: boolean
  resource: PathResource | null
  stageId: string
}>()

const emit = defineEmits<{
  close: []
  complete: [stageId: string, resourceId: string]
}>()

const profileStore = useProfileStore()
const resourceStore = useResourceStore()

// 状态
const isMounted = ref(false)
const contentRef = ref<HTMLElement | null>(null)
const resourceData = ref<any>(null)
const readingTime = ref(0)
const scrollDepth = ref(0)
const hasScrolledToBottom = ref(false)
const minReadingTime = 15
const scrollThreshold = 80

// Agent 生成状态
const isGenerating = ref(false)
const generatedContent = ref('')
const abortGenerate = ref<(() => void) | null>(null)
const contentReady = ref(false) // 内容是否已生成完成
const contentLoadFailed = ref(false) // 内容是否生成失败
const needsGeneration = ref(false) // allocator 缺口：无匹配资源，需用户触发生成

// 计时器
let readingTimer: ReturnType<typeof setInterval> | null = null

// 计算属性
const typeIcon = computed(() => {
  if (!props.resource) return '📄'
  const item = RESOURCE_TYPE_MAP[props.resource.type as keyof typeof RESOURCE_TYPE_MAP]
  return item?.icon || '📄'
})

const readingTimeFormatted = computed(() => {
  if (!contentReady.value) return '等待内容'
  const mins = Math.floor(readingTime.value / 60)
  const secs = readingTime.value % 60
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
})

const canComplete = computed(() => {
  // 必须有内容才能完成
  if (!contentReady.value) return false
  // 视频资源：contentReady 即可完成（视频不需要 generatedContent 文本）
  if (isVideo.value) {
    return readingTime.value >= minReadingTime
  }
  if (!generatedContent.value) return false
  // 阅读时间足够
  if (readingTime.value < minReadingTime) return false
  // 已滚动到底部（内容足够长时）
  const contentLength = generatedContent.value.length
  if (contentLength > 500 && !hasScrolledToBottom.value) return false
  return true
})

const progressTip = computed(() => {
  if (isGenerating.value) {
    return '正在调用 AI 生成学习内容，请稍候...'
  }
  if (!contentReady.value) {
    return '等待内容生成...'
  }
  if (contentLoadFailed.value && !generatedContent.value && !isVideo.value) {
    return '内容生成失败，请点击重新生成'
  }
  if (canComplete.value) {
    return '已完成阅读，可以标记为完成'
  }
  const tips = []
  if (readingTime.value < minReadingTime) {
    tips.push(`还需阅读 ${minReadingTime - readingTime.value} 秒`)
  }
  if (!isVideo.value && generatedContent.value.length > 500 && !hasScrolledToBottom.value) {
    tips.push('请滚动查看完整内容')
  }
  return tips.join('，') || '正在阅读...'
})

const completeButtonText = computed(() => {
  if (!contentReady.value) return '等待内容'
  if (readingTime.value < minReadingTime) {
    return `需阅读 ${minReadingTime - readingTime.value}秒`
  }
  if (!isVideo.value && generatedContent.value.length > 500 && !hasScrolledToBottom.value) {
    return '请滚动到底'
  }
  return '完成学习'
})

// 已存储的资源（从 Agent 工作流生成并写入 resourceStore 的内容）
// 只读 resourceRef，不兜底搜索 —— allocator 负责"哪个资源给哪个小节"，
// Modal 兜底搜索会绕过 allocator 的 exclude 导致多个小节显示同一资源
const storedResource = computed(() => {
  if (!props.resource) return null
  const refId = props.resource.resourceRef
  if (!refId) return null
  return resourceStore.resources.find(r => r.id === refId) || null
})

// 已存储的内容（优先使用 Agent 生成的内容，避免重复生成）
const storedContent = computed(() => {
  return storedResource.value?.content || ''
})

// 类型判断优先用 PathResource.type，其次用已存储 ResourceItem.type
// 原因：workspaceStore 的跨类型模糊匹配可能把 knowledge-graph 资源挂到 document 类 PathResource 上，
// 仅检查 PathResource.type 会导致图谱 JSON 被当作纯文本渲染。
const isKnowledgeGraph = computed(() => {
  if (props.resource?.type === 'knowledge-graph') return true
  return storedResource.value?.type === 'knowledge-graph'
})
const isMindmap = computed(() => {
  if (props.resource?.type === 'mindmap') return true
  return storedResource.value?.type === 'mindmap'
})
const isVideo = computed(() => {
  if (props.resource?.type === 'video') return true
  return storedResource.value?.type === 'video'
})

// 薄弱点（用于知识图谱高亮）
const weakPoints = computed(() => {
  const subject = profileStore.profileData.currentSubject || ''
  const global = profileStore.profileData.weak_points || []
  const overlay = profileStore.profileData.subjectOverlays?.find(o => o.subject === subject)
  const overlayWp = overlay?.weak_points || []
  return [...new Set([...overlayWp, ...global])]
})

// B站搜索链接（视频失败时的降级）
const bilibiliSearchUrl = computed(() => {
  if (!props.resource?.name) return ''
  return `https://search.bilibili.com/all?keyword=${encodeURIComponent(props.resource.name)}`
})

// 方法
function startReadingTimer() {
  if (readingTimer) clearInterval(readingTimer)
  readingTimer = setInterval(() => {
    if (contentReady.value && !isGenerating.value) {
      readingTime.value++
    }
  }, 1000)
}

function stopReadingTimer() {
  if (readingTimer) {
    clearInterval(readingTimer)
    readingTimer = null
  }
}

function handleScroll() {
  if (!contentRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = contentRef.value
  const scrollPercent = (scrollTop + clientHeight) / scrollHeight * 100
  scrollDepth.value = Math.min(100, Math.round(scrollPercent))
  if (scrollPercent >= scrollThreshold) {
    hasScrolledToBottom.value = true
  }
}

async function loadResourceContent() {
  if (!props.resource) return

  // 重置状态
  generatedContent.value = ''
  readingTime.value = 0
  hasScrolledToBottom.value = false
  contentReady.value = false
  contentLoadFailed.value = false
  needsGeneration.value = false
  isGenerating.value = true

  // 加载资源基本信息
  try {
    const data = await getDetail(props.resource.id)
    resourceData.value = data
  } catch {
    resourceData.value = {
      id: props.resource.id,
      title: props.resource.name,
      type: props.resource.type,
      description: `${props.resource.name}的学习内容`
    }
  }

  // 优先使用 Agent 工作流已生成的存储内容（避免重复生成 + 修复图谱JSON显示）
  const stored = storedResource.value
  if (stored) {
    // 视频资源：根据渲染状态展示，不调用AI生成
    if (stored.type === 'video') {
      isGenerating.value = false
      contentReady.value = true
      return
    }
    // 知识图谱/思维导图/文档/练习题：有存储内容则直接使用
    if (stored.content && stored.content.length > 0) {
      generatedContent.value = stored.content
      isGenerating.value = false
      contentReady.value = true
      return
    }
  } else {
    // 无 storedResource（resourceRef 为空）→ allocator 缺口，不自动生成
    isGenerating.value = false
    needsGeneration.value = true
    return
  }

  // 无存储内容，调用 Agent 流式生成
  streamGenerateContent()
}

/** AI 流式生成内容（用于有资源元数据但无 content 的情况，或用户手动触发生成） */
function streamGenerateContent() {
  if (!props.resource) return
  isGenerating.value = true
  contentLoadFailed.value = false
  abortGenerate.value = generateResourceContent(
    props.resource.id,
    {
      title: props.resource.name,
      type: props.resource.type,
      description: `${props.resource.name}的学习内容`,
      difficulty: 'basic',
      duration: '30分钟',
    },
    (content) => {
      generatedContent.value += content
      if (!contentReady.value && generatedContent.value.length > 50) {
        contentReady.value = true
      }
    },
    (error) => {
      console.warn('[Agent] 生成内容失败:', error)
      isGenerating.value = false
      contentLoadFailed.value = true
      if (generatedContent.value.length > 100) {
        contentReady.value = true
        contentLoadFailed.value = false
      }
    },
    () => {
      isGenerating.value = false
      if (generatedContent.value.length > 50) {
        contentReady.value = true
        saveContent({
          resource_id: props.resource.id,
          content: generatedContent.value,
          generated_by: 'deepseek'
        }).catch(err => console.warn('[Learning] 保存内容失败:', err))
      } else {
        contentLoadFailed.value = true
      }
    }
  )
}

/** 为当前小节生成资源（allocator 缺口时用户手动触发） */
function generateForStage() {
  if (!props.resource) return
  needsGeneration.value = false
  generatedContent.value = ''
  contentReady.value = false
  streamGenerateContent()
}

function handleClose() {
  stopReadingTimer()
  if (abortGenerate.value) {
    abortGenerate.value()
    abortGenerate.value = null
  }
  emit('close')
}

function numToChinese(num: number): string {
  const chars = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
  if (num <= 10) return chars[num]
  if (num < 20) return '十' + (num % 10 !== 0 ? chars[num % 10] : '')
  const tens = Math.floor(num / 10)
  const ones = num % 10
  return chars[tens] + '十' + (ones !== 0 ? chars[ones] : '')
}

function formatListNumber(level: string): string {
  const parts = level.split('.')
  if (parts.length === 1) {
    return numToChinese(parseInt(parts[0])) + '、'
  }
  return level + '.'
}

interface MindmapNode {
  name: string
  desc: string
  highlight?: boolean
  children?: MindmapNode[]
}

function renderMindmapSvg(data: MindmapNode): string {
  // 计算每层的节点位置
  const levelNodes: { x: number; y: number; name: string; desc: string; highlight: boolean; width: number; level: number }[][] = []
  const connections: { fromX: number; fromY: number; toX: number; toY: number; fromLevel: number }[] = []
  
  const nodeWidth = 180
  const nodeHeight = 70
  const rootWidth = 240
  const rootHeight = 90
  const levelGap = 160
  const nodeGap = 60
  
  // 递归布局节点
  function layoutNode(node: MindmapNode, level: number, x: number, y: number, parentX?: number, parentY?: number, parentLevel?: number) {
    const width = level === 0 ? rootWidth : nodeWidth
    const height = level === 0 ? rootHeight : nodeHeight
    
    levelNodes[level] = levelNodes[level] || []
    levelNodes[level].push({
      x,
      y,
      name: node.name,
      desc: node.desc,
      highlight: node.highlight || false,
      width,
      level
    })
    
    if (parentX !== undefined && parentY !== undefined) {
      connections.push({ fromX: parentX, fromY: parentY, toX: x, toY: y, fromLevel: parentLevel || 0 })
    }
    
    if (node.children && node.children.length > 0) {
      const totalWidth = (node.children.length - 1) * (nodeWidth + nodeGap)
      const startX = x - totalWidth / 2
      
      node.children.forEach((child, index) => {
        const childX = startX + index * (nodeWidth + nodeGap)
        const childY = y + levelGap
        layoutNode(child, level + 1, childX, childY, x, y, level)
      })
    }
  }
  
  // 从根节点开始布局
  layoutNode(data, 0, 600, 80)
  
  // 计算总尺寸
  let maxX = 600
  let maxY = 80
  levelNodes.forEach(level => {
    level.forEach(node => {
      maxX = Math.max(maxX, node.x + node.width/2)
      maxY = Math.max(maxY, node.y + nodeHeight/2)
    })
  })
  const totalWidth = Math.max(maxX + 80, 1200)
  const totalHeight = maxY + 80
  
  // 生成SVG
  let svg = `<svg width="${totalWidth}" height="${totalHeight}" viewBox="0 0 ${totalWidth} ${totalHeight}" style="overflow: visible; background: linear-gradient(180deg, #FAFBFC 0%, #FFFFFF 100%);">`
  
  // 定义渐变和阴影
  svg += `<defs>`
  svg += `<linearGradient id="mindRootGrad" x1="0%" y1="0%" x2="100%" y2="100%">`
  svg += `<stop offset="0%" style="stop-color:#7C3AED"/>`
  svg += `<stop offset="50%" style="stop-color:#9333EA"/>`
  svg += `<stop offset="100%" style="stop-color:#6366F1"/>`
  svg += `</linearGradient>`
  svg += `<linearGradient id="mindHighlightGrad" x1="0%" y1="0%" x2="100%" y2="100%">`
  svg += `<stop offset="0%" style="stop-color:#FBBF24"/>`
  svg += `<stop offset="100%" style="stop-color:#F59E0B"/>`
  svg += `</linearGradient>`
  svg += `<linearGradient id="mindLevel1Grad" x1="0%" y1="0%" x2="0%" y2="100%">`
  svg += `<stop offset="0%" style="stop-color:#EEF2FF"/>`
  svg += `<stop offset="100%" style="stop-color:#E0E7FF"/>`
  svg += `</linearGradient>`
  svg += `<linearGradient id="mindLevel2Grad" x1="0%" y1="0%" x2="0%" y2="100%">`
  svg += `<stop offset="0%" style="stop-color:#F0FDF4"/>`
  svg += `<stop offset="100%" style="stop-color:#DCFCE7"/>`
  svg += `</linearGradient>`
  svg += `<filter id="mindShadow" x="-30%" y="-30%" width="160%" height="160%">`
  svg += `<feDropShadow dx="0" dy="6" stdDeviation="8" flood-opacity="0.1"/>`
  svg += `</filter>`
  svg += `<filter id="mindShadowSmall" x="-20%" y="-20%" width="140%" height="140%">`
  svg += `<feDropShadow dx="0" dy="3" stdDeviation="4" flood-opacity="0.08"/>`
  svg += `</filter>`
  svg += `</defs>`
  
  // 绘制连接线
  connections.forEach(conn => {
    const fromHeight = conn.fromLevel === 0 ? rootHeight : nodeHeight
    const fromY = conn.fromY + fromHeight / 2 + 5
    const toY = conn.toY - nodeHeight / 2 - 5
    const midY = (fromY + toY) / 2
    
    svg += `<path d="M${conn.fromX},${fromY} C${conn.fromX},${midY} ${conn.toX},${midY} ${conn.toX},${toY}" stroke="#C4B5FD" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.7"/>`
    svg += `<circle cx="${conn.toX}" cy="${toY}" r="5" fill="#8B5CF6" opacity="0.6"/>`
  })
  
  // 绘制节点
  levelNodes.forEach(level => {
    level.forEach(node => {
      const isRoot = node.level === 0
      const isHighlight = node.highlight
      const width = isRoot ? rootWidth : nodeWidth
      const height = isRoot ? rootHeight : nodeHeight
      
      let bgColor: string
      let borderColor: string
      let textColor: string
      let descColor: string
      
      if (isRoot) {
        bgColor = 'url(#mindRootGrad)'
        borderColor = '#6D28D9'
        textColor = 'white'
        descColor = 'rgba(255,255,255,0.9)'
      } else if (isHighlight) {
        bgColor = 'url(#mindHighlightGrad)'
        borderColor = '#D97706'
        textColor = '#92400E'
        descColor = '#B45309'
      } else if (node.level === 1) {
        bgColor = 'url(#mindLevel1Grad)'
        borderColor = '#818CF8'
        textColor = '#4338CA'
        descColor = '#6366F1'
      } else {
        bgColor = 'url(#mindLevel2Grad)'
        borderColor = '#4ADE80'
        textColor = '#166534'
        descColor = '#22C55E'
      }
      
      // 节点背景（带内发光效果）
      svg += `<rect x="${node.x - width/2}" y="${node.y - height/2}" width="${width}" height="${height}" rx="20" ry="20" fill="${bgColor}" stroke="${borderColor}" stroke-width="2.5" filter="${isRoot ? 'url(#mindShadow)' : 'url(#mindShadowSmall)'}" style="stroke-dasharray: none;"/>`
      
      // 内发光效果（仅根节点）
      if (isRoot) {
        svg += `<rect x="${node.x - width/2 + 4}" y="${node.y - height/2 + 4}" width="${width - 8}" height="${height - 8}" rx="18" ry="18" fill="rgba(255,255,255,0.15)" style="pointer-events: none;"/>`
      }
      
      // 节点名称
      svg += `<text x="${node.x}" y="${node.y - 10}" text-anchor="middle" fill="${textColor}" font-size="${isRoot ? 20 : 14}" font-weight="700" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">${node.name}</text>`
      
      // 节点描述
      svg += `<text x="${node.x}" y="${node.y + 15}" text-anchor="middle" fill="${descColor}" font-size="${isRoot ? 13 : 11}" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">${node.desc}</text>`
      
      // 高亮标记（火焰图标）
      if (isHighlight) {
        svg += `<g transform="translate(${node.x + width/2 - 22}, ${node.y - height/2 + 20})">`
        svg += `<polygon points="0,12 6,0 12,12 9,12 9,18 3,18 3,12" fill="#DC2626"/>`
        svg += `<polygon points="2,10 6,2 10,10" fill="#FCA5A5"/>`
        svg += `</g>`
      }
      
      // 层级装饰点
      if (!isRoot && !isHighlight) {
        svg += `<circle cx="${node.x - width/2 + 15}" cy="${node.y}" r="5" fill="${borderColor}" opacity="0.3"/>`
      }
    })
  })
  
  svg += `</svg>`
  
  return `<div class="mindmap-svg-container" style="overflow-x: auto; overflow-y: auto; padding: 20px;">${svg}</div>`
}

/** 渲染 Markdown 内容 - 美观清晰的格式 */
function renderMarkdown(content: string): string {
  if (!content) return ''
  let html = content
  
  // 处理思维导图JSON数据 - 渲染为可视化SVG图形
  html = html.replace(/```mindmap-data\n?([\s\S]*?)```/g, (match, code) => {
    try {
      const trimmedCode = code.trim()
      if (!trimmedCode) {
        return `<div class="mindmap-loading"><div class="loading-spinner"></div><span class="loading-text">🤖 AI 正在生成思维导图...</span></div>`
      }
      const jsonData = JSON.parse(trimmedCode) as MindmapNode
      return renderMindmapSvg(jsonData)
    } catch {
      // JSON 不完整，显示加载状态
      return `<div class="mindmap-loading"><div class="loading-spinner"></div><span class="loading-text">🤖 AI 正在生成思维导图...</span></div>`
    }
  })
  
  // 处理未闭合的 mindmap-data 代码块（流式生成中）
  html = html.replace(/```mindmap-data\n?([\s\S]*?)$/g, () => {
    return `<div class="mindmap-loading"><div class="loading-spinner"></div><span class="loading-text">🤖 AI 正在生成思维导图...</span></div>`
  })
  
  // 处理在线导图链接
  html = html.replace(/\*\*在线导图\*\*:\s*\[([^\]]+)\]\(([^)]+)\)/g, 
    '<a href="$2" target="_blank" class="mindmap-link"><span class="link-icon">🔗</span> $1</a>')
  
  // 处理B站视频链接 - 美化显示
  html = html.replace(/\[([^\]]+视频[^\]]*)\]\((https?:\/\/www\.bilibili\.com\/video\/[^)]+)\)/g,
    '<a href="$2" target="_blank" class="video-link"><span class="video-icon">📺</span> $1</a>')
  
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/search\.bilibili\.com\/[^)]+)\)/g,
    '<a href="$2" target="_blank" class="video-link bilibili-search"><span class="video-icon">🔍</span> 在B站搜索：$1</a>')
  
  // 代码块 - 添加语言标签
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    const langLabel = lang ? `<span class="code-lang">${lang}</span>` : ''
    return `<div class="code-block-wrapper">${langLabel}<pre class="code-block"><code>${code}</code></pre></div>`
  })
  
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  
  // 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="highlight">$1</strong>')
  
  // 斜体
  html = html.replace(/\*(.+?)\*/g, '<em class="emphasis">$1</em>')
  
  // 清理多余空行
  html = html.replace(/\n{3,}/g, '\n\n')
  
  // 分割内容为段落块
  const blocks = html.split(/\n\n/)
  const processedBlocks: string[] = []
  
  for (const block of blocks) {
    if (!block.trim()) continue
    
    // 检查是否为有序列表块
    if (/^\d+(?:\.\d+)*\. /.test(block)) {
      let listContent = block.replace(/^\d+(?:\.\d+)*\. (.+)$/gm, (match, text) => {
        const parts = match.match(/^(\d+(?:\.\d+)*)\. /)
        if (!parts) return match
        const level = parts[1]
        const formattedNum = formatListNumber(level)
        const indentLevel = level.split('.').length
        return `<li class="ordered-item" data-level="${level}" style="padding-left: ${(indentLevel - 1) * 20}px"><span class="num">${formattedNum}</span><span class="text">${text}</span></li>`
      })
      processedBlocks.push(`<ol class="ordered-list">${listContent}</ol>`)
    }
    // 检查是否为无序列表块
    else if (/^- /.test(block)) {
      let listContent = block.replace(/^- (.+)$/gm, '<li class="unordered-item"><span class="dot">•</span><span class="text">$1</span></li>')
      processedBlocks.push(`<ul class="unordered-list">${listContent}</ul>`)
    }
    // 检查是否为标题
    else if (/^(#{1,4}) /.test(block)) {
      let titleBlock = block
      titleBlock = titleBlock.replace(/^#### (.+)$/gm, '<h5 class="title-h5"><span class="title-icon">▸</span>$1</h5>')
      titleBlock = titleBlock.replace(/^### (.+)$/gm, '<h4 class="title-h4"><span class="title-icon">◆</span>$1</h4>')
      titleBlock = titleBlock.replace(/^## (.+)$/gm, '<h3 class="title-h3"><span class="title-icon">●</span>$1</h3>')
      titleBlock = titleBlock.replace(/^# (.+)$/gm, '<h2 class="title-h2"><span class="title-icon">■</span>$1</h2>')
      processedBlocks.push(titleBlock)
    }
    // 检查是否为分隔线
    else if (/^---$/.test(block)) {
      processedBlocks.push('<div class="divider"></div>')
    }
    // 检查是否为引用块
    else if (/^> /.test(block)) {
      let quoteBlock = block.replace(/^> (.+)$/gm, '<div class="quote-block"><span class="quote-icon">💡</span><span class="quote-text">$1</span></div>')
      processedBlocks.push(quoteBlock)
    }
    // 检查是否为导图容器（已处理过的）
    else if (block.includes('class="mindmap-container"')) {
      processedBlocks.push(block)
    }
    // 检查是否为代码块（已处理过的）
    else if (block.includes('<div class="code-block-wrapper">')) {
      processedBlocks.push(block)
    }
    // 普通段落
    else {
      processedBlocks.push(`<p class="paragraph">${block}</p>`)
    }
  }
  
  return processedBlocks.join('\n')
}

async function handleComplete() {
  if (!canComplete.value || !props.resource) return
  stopReadingTimer()
  
  try {
    await completeLearning({
      resource_id: props.resource.id,
      reading_time: readingTime.value,
      scroll_depth: scrollDepth.value
    })
    
    // 添加学习事件，用于统计学习时长
    profileStore.applyLearningEvent({
      type: 'resource_complete',
      sourceId: props.resource.id,
      resourceType: props.resource.type,
      knowledgePoints: [],
      timestamp: new Date().toISOString(),
      description: `完成学习资源: ${props.resource.name}`
    })
    
    if (generatedContent.value) {
      await saveContent({
        resource_id: props.resource.id,
        content: generatedContent.value,
        generated_by: 'deepseek'
      })
    }
  } catch (e) {
    console.error('[Learning] API 调用失败:', e)
  }
  
  emit('complete', props.stageId, props.resource.id)
}

// 监听弹窗打开
watch(() => props.visible, (newVal) => {
  if (newVal) {
    readingTime.value = 0
    hasScrolledToBottom.value = false
    contentReady.value = false
    contentLoadFailed.value = false
    resourceData.value = null
    loadResourceContent()
    startReadingTimer()
  } else {
    stopReadingTimer()
  }
})

onMounted(() => {
  isMounted.value = true
})
onUnmounted(() => {
  stopReadingTimer()
})
</script>

<style lang="less" scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.modal-box {
  width: 720px;
  max-width: 92vw;
  max-height: 85vh;
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #E5E7EB;
  background: linear-gradient(to right, #F8FAFC, #F1F5F9);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.res-type-icon {
  font-size: 18px;
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
  color: #1E293B;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.reading-time {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  background: #DBEAFE;
  color: #3B82F6;

  &.warning {
    background: #FEF3C7;
    color: #D97706;
  }
}

.modal-close {
  font-size: 14px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: #94A3B8;
  cursor: pointer;
  border-radius: 4px;
  &:hover { color: #1E293B; background: #F1F5F9; }
}

.progress-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #FEF3C7;
  border-bottom: 1px solid #FDE68A;

  &.generating {
    background: #DBEAFE;
    border-bottom-color: #BFDBFE;
  }

  &.complete {
    background: #D1FAE5;
    border-bottom-color: #A7F3D0;
  }
}

.tip-icon {
  font-size: 13px;
}

.tip-text {
  font-size: 12px;
  color: #64748B;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  background: #FFFFFF;

  &::-webkit-scrollbar { width: 5px; }
  &::-webkit-scrollbar-track { background: #F1F5F9; }
  &::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
}

.content-wrapper {
  min-height: 100%;
}

.resource-desc {
  font-size: 13px;
  color: #64748B;
  padding: 10px 14px;
  background: #F8FAFC;
  border-radius: 6px;
  margin-bottom: 14px;
  line-height: 1.5;
  border: 1px solid #E5E7EB;
}

.generating-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #EFF6FF;
  border-radius: 6px;
  margin-bottom: 14px;
  border: 1px solid #DBEAFE;
}

.generating-icon {
  font-size: 14px;
}

.generating-text {
  font-size: 13px;
  color: #3B82F6;
  font-weight: 500;
}

.generating-dots {
  display: flex;
  gap: 3px;
  span {
    width: 5px;
    height: 5px;
    background: #3B82F6;
    border-radius: 50%;
    animation: bounce 1.2s infinite ease-in-out both;
    &:nth-child(1) { animation-delay: -0.24s; }
    &:nth-child(2) { animation-delay: -0.12s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); }
  40% { transform: scale(1); }
}

.resource-content {
  font-size: 14px;
  color: #2D3748;
  line-height: 1.8;
  padding: 20px 24px;
  background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFC 100%);
  border-radius: 12px;
  margin: 0;
  border: 1px solid #E2E8F0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.markdown-body {
  .paragraph {
    margin: 12px 0;
    line-height: 1.85;
    color: #4A5568;
    text-align: justify;
    font-size: 14px;
    letter-spacing: 0.3px;
  }
  
  .title-h2 {
    font-size: 18px;
    font-weight: 700;
    color: #1A202C;
    margin: 24px 0 14px;
    padding: 14px 18px;
    background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
    
    .title-icon {
      color: rgba(255, 255, 255, 0.9);
      font-size: 16px;
    }
    
    &::after {
      content: '';
      flex: 1;
      height: 2px;
      background: rgba(255, 255, 255, 0.3);
      border-radius: 1px;
    }
  }
  
  .title-h3 {
    font-size: 16px;
    font-weight: 600;
    color: #2D3748;
    margin: 20px 0 12px;
    padding: 10px 14px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
    border-radius: 8px;
    border-left: 4px solid #667EEA;
    display: flex;
    align-items: center;
    gap: 8px;
    
    .title-icon {
      color: #667EEA;
      font-size: 14px;
    }
  }
  
  .title-h4 {
    font-size: 15px;
    font-weight: 600;
    color: #374151;
    margin: 16px 0 10px;
    padding-left: 12px;
    border-left: 3px solid #48BB78;
    display: flex;
    align-items: center;
    gap: 6px;
    
    .title-icon {
      color: #48BB78;
      font-size: 12px;
    }
  }
  
  .title-h5 {
    font-size: 14px;
    font-weight: 600;
    color: #4A5568;
    margin: 12px 0 8px;
    padding-left: 10px;
    border-left: 2px solid #ED8936;
    display: flex;
    align-items: center;
    gap: 5px;
    
    .title-icon {
      color: #ED8936;
      font-size: 11px;
    }
  }
  
  .unordered-list {
    margin: 14px 0;
    padding: 0;
    list-style: none;
    
    .unordered-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      margin: 8px 0;
      padding: 10px 14px;
      background: linear-gradient(135deg, #F7FAFC 0%, #EDF2F7 100%);
      border-radius: 8px;
      border: 1px solid #E2E8F0;
      transition: all 0.2s ease;
      
      &:hover {
        background: linear-gradient(135deg, #EDF2F7 0%, #E2E8F0 100%);
        transform: translateX(4px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      }
      
      .dot {
        color: #48BB78;
        font-size: 16px;
        font-weight: 700;
        flex-shrink: 0;
        margin-top: 2px;
      }
      
      .text {
        color: #4A5568;
        line-height: 1.7;
        font-size: 14px;
      }
    }
  }
  
  .ordered-list {
    margin: 14px 0;
    padding: 0;
    list-style: none;
    
    .ordered-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin: 10px 0;
      padding: 12px 16px;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
      border-radius: 8px;
      border: 1px solid rgba(102, 126, 234, 0.15);
      transition: all 0.2s ease;
      
      &:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
        transform: translateX(4px);
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
      }
      
      .num {
        color: #667EEA;
        font-size: 14px;
        font-weight: 700;
        flex-shrink: 0;
        min-width: 28px;
        padding: 2px 8px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 4px;
        text-align: center;
      }
      
      .text {
        color: #4A5568;
        line-height: 1.7;
        font-size: 14px;
      }
    }
  }
  
  .code-block-wrapper {
    position: relative;
    margin: 18px 0;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #2D3748;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    
    .code-lang {
      position: absolute;
      top: 0;
      right: 0;
      padding: 6px 12px;
      background: linear-gradient(135deg, #667EEA, #764BA2);
      color: white;
      font-size: 11px;
      font-weight: 600;
      border-radius: 0 8px 0 6px;
    }
  }
  
  .code-block {
    background: linear-gradient(180deg, #2D3748 0%, #1A202C 100%);
    padding: 16px 20px;
    margin: 0;
    overflow-x: auto;
    
    code {
      color: #E2E8F0;
      font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      line-height: 1.7;
      background: transparent;
      padding: 0;
      border: none;
      white-space: pre;
    }
  }
  
  .inline-code {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
    padding: 4px 10px;
    border-radius: 6px;
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 13px;
    color: #667EEA;
    border: 1px solid rgba(102, 126, 234, 0.2);
    font-weight: 500;
  }
  
  .highlight {
    font-weight: 700;
    color: #1A202C;
    background: linear-gradient(135deg, rgba(251, 146, 60, 0.2), rgba(251, 146, 60, 0.1));
    padding: 3px 8px;
    border-radius: 5px;
    border: 1px solid rgba(251, 146, 60, 0.2);
  }
  
  .emphasis {
    color: #718096;
    font-style: italic;
    font-weight: 400;
  }
  
  .divider {
    height: 3px;
    margin: 20px 0;
    background: linear-gradient(90deg, transparent, #E2E8F0, transparent);
    border-radius: 2px;
  }
  
  .quote-block {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 16px 20px;
    margin: 16px 0;
    background: linear-gradient(135deg, rgba(72, 187, 120, 0.06), rgba(72, 187, 120, 0.03));
    border-radius: 10px;
    border-left: 4px solid #48BB78;
    box-shadow: 0 2px 8px rgba(72, 187, 120, 0.08);

    .quote-icon {
      font-size: 20px;
      flex-shrink: 0;
      margin-top: -2px;
    }

    .quote-text {
      color: #4A5568;
      line-height: 1.7;
      font-weight: 500;
      font-size: 14px;
    }
  }

  // 思维导图SVG容器样式
  .mindmap-svg-container {
    margin: 16px 0;
    background: linear-gradient(135deg, #FAFBFC 0%, #F7FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    overflow-x: auto;
    overflow-y: auto;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);

    svg {
      display: block;
      margin: 0 auto;
      max-width: 100%;
      height: auto;
    }
  }

  .mindmap-error {
    text-align: center;
    padding: 40px;
    color: #EF4444;
    font-size: 14px;
  }

  .mindmap-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    margin: 16px 0;
    background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
    border: 2px dashed #A5B4FC;
    border-radius: 12px;

    .loading-spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #C7D2FE;
      border-top-color: #6366F1;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 16px;
    }

    .loading-text {
      font-size: 15px;
      font-weight: 600;
      color: #4F46E5;
      letter-spacing: 0.5px;
    }
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  // 在线导图链接样式
  .mindmap-link {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px;
    margin: 12px 0;
    background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
    color: white;
    text-decoration: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    transition: all 0.2s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    .link-icon {
      font-size: 18px;
    }
  }

  // 视频链接样式
  .video-link {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    margin: 10px 0;
    background: linear-gradient(135deg, #20B2AA 0%, #2E8B8B 100%);
    color: white;
    text-decoration: none;
    border-radius: 10px;
    font-weight: 500;
    font-size: 14px;
    box-shadow: 0 4px 12px rgba(32, 178, 170, 0.3);
    transition: all 0.2s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 18px rgba(32, 178, 170, 0.4);
    }

    &.bilibili-search {
      background: linear-gradient(135deg, #FF6B9D 0%, #FF8E53 100%);
      box-shadow: 0 4px 12px rgba(255, 107, 157, 0.3);

      &:hover {
        box-shadow: 0 6px 18px rgba(255, 107, 157, 0.4);
      }
    }

    .video-icon {
      font-size: 20px;
      flex-shrink: 0;
    }
  }
}

.no-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 50px 20px;
  gap: 10px;
}

.no-content-icon {
  font-size: 36px;
}

.no-content-text {
  font-size: 14px;
  color: #64748B;
}

.retry-btn {
  margin-top: 8px;
  padding: 8px 16px;
  background: #3B82F6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  &:hover { background: #2563EB; }
}

/* 视频渲染状态 */
.video-pending, .video-failed {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  gap: 12px;
  text-align: center;
}

.pending-icon, .failed-icon {
  font-size: 36px;
}

.video-pending span:last-child {
  font-size: 14px;
  color: #64748B;
}

.video-failed span:nth-child(2) {
  font-size: 14px;
  color: #EF4444;
}

.video-player {
  max-width: 100%;
  display: block;
}

/* 知识图谱/思维导图容器 */
.graph-content, .mindmap-content {
  width: 100%;
}

.content-footer {
  height: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 18px;
  border-top: 1px solid #E5E7EB;
  background: #FFFFFF;
}

.btn-cancel, .btn-complete {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #64748B;
  &:hover { background: #F1F5F9; border-color: #CBD5E1; }
}

.btn-complete {
  border: none;
  background: linear-gradient(135deg, #3B82F6, #60A5FA);
  color: #FFFFFF;
  &:hover:not(:disabled) { 
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    transform: translateY(-1px);
  }
  &:disabled {
    background: #CBD5E1;
    color: #94A3B8;
    cursor: not-allowed;
    transform: none;
  }
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>