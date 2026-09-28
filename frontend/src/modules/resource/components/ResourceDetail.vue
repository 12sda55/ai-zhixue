<template>
  <div class="resource-detail" v-if="resource">
    <!-- 头部区域 -->
    <div class="detail-header">
      <div class="header-badge" :style="{ background: typeColor }">
        <span class="badge-icon">{{ typeIcon }}</span>
        <span class="badge-text">{{ typeLabel }}</span>
      </div>
      <div class="header-info">
        <h3 class="detail-title">{{ resource.title }}</h3>
        <div class="detail-meta">
          <span v-if="resource.difficulty" class="meta-tag difficulty">
            <span class="tag-dot"></span>
            {{ difficultyLabel }}
          </span>
          <span v-if="resource.module" class="meta-tag module">
            <span class="tag-dot"></span>
            {{ resource.module }}
          </span>
          <span class="meta-tag source">
            <span class="tag-dot"></span>
            {{ resource.aiGenerated ? 'AI生成' : '系统资源' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="detail-body">
      <!-- 视频：内嵌播放器 + 生成功能 -->
      <template v-if="resource.type === 'video'">
        <div class="video-section">
          <div class="section-title">
            <span class="title-icon">🎬</span>
            <span>视频资源</span>
          </div>

          <!-- 已有视频URL：内嵌播放器 -->
          <div class="video-player-wrapper" v-if="videoUrl">
            <div class="video-controls-bar">
              <button class="subtitle-toggle" @click="toggleSubtitle" :class="{ active: showSubtitle }">
                {{ showSubtitle ? '📝 字幕开' : '📝 字幕关' }}
              </button>
            </div>
            <video
              ref="videoPlayer"
              :src="videoUrl"
              controls
              class="video-player"
              @error="onVideoError"
              crossorigin="anonymous"
            >
              <track v-if="subtitleUrl" :src="subtitleUrl" kind="subtitles" srclang="zh" label="中文字幕" :default="showSubtitle">
              您的浏览器不支持视频播放
            </video>
            <div class="video-meta">
              <span class="meta-item">⏱ {{ resource.duration || '约2分钟' }}</span>
              <span class="meta-item">📡 AI生成</span>
            </div>
            <!-- 删除并重新生成按钮 -->
            <div class="video-actions">
              <button class="regenerate-btn" @click="deleteAndRegenerate" :disabled="generating">
                {{ generating ? '生成中...' : '🔄 删除并重新生成' }}
              </button>
            </div>
          </div>

          <!-- 正在生成：显示进度 -->
          <div class="video-generating" v-else-if="videoTaskId && videoStatus !== 'done' && videoStatus !== 'failed'">
            <div class="generating-icon">
              <div class="spinner"></div>
            </div>
            <div class="generating-info">
              <p class="generating-title">正在生成教学视频...</p>
              <div class="generating-progress">
                <div class="progress-track">
                  <div class="progress-bar-fill" :style="{ width: videoProgress + '%' }"></div>
                </div>
                <span class="progress-text">{{ videoProgress }}%</span>
              </div>
              <p class="generating-message">{{ videoMessage }}</p>
              <button class="cancel-gen-btn" @click="cancelVideoGeneration">✕ 取消生成</button>
            </div>
          </div>

          <!-- 生成失败 -->
          <div class="video-card empty" v-else-if="videoStatus === 'failed'">
            <div class="empty-icon">⚠️</div>
            <div class="empty-text">视频生成失败</div>
            <div class="empty-sub">{{ videoMessage || '请稍后重试' }}</div>
            <button class="generate-btn" @click="startGenerateVideo">重新生成</button>
          </div>

          <!-- 未生成：显示生成按钮 -->
          <div class="video-card empty" v-else>
            <div class="empty-icon">🎬</div>
            <div class="empty-text">暂无视频内容</div>
            <div class="empty-sub">点击下方按钮，AI将为你生成教学动画视频</div>
            <button class="generate-btn" @click="startGenerateVideo" :disabled="generating">
              {{ generating ? '创建中...' : '🎬 生成教学视频' }}
            </button>
          </div>
        </div>
      </template>

      <!-- 代码：代码块 -->
      <template v-else-if="resource.type === 'code'">
        <div class="code-section">
          <div class="section-title">
            <span class="title-icon">💻</span>
            <span>代码示例</span>
          </div>
          <div class="code-container">
            <div class="code-header">
              <span class="code-lang">{{ codeLanguage }}</span>
              <button class="copy-btn" @click="copyCode">复制代码</button>
            </div>
            <pre class="code-block"><code>{{ resource.content }}</code></pre>
          </div>
        </div>
      </template>

      <!-- 习题：题目列表 -->
      <template v-else-if="resource.type === 'exercise'">
        <div class="exercise-section">
          <div class="section-title">
            <span class="title-icon">📝</span>
            <span>练习题</span>
          </div>
          <div class="exercise-content markdown-body" v-html="renderMarkdown(resource.content || '')" />
        </div>
      </template>

      <!-- 导图 -->
      <template v-else-if="resource.type === 'mindmap'">
        <div class="mindmap-section">
          <div class="section-title">
            <span class="title-icon">🗺️</span>
            <span>知识导图</span>
          </div>
          <MindMapViewer :content="resource.content || ''" />
        </div>
      </template>

      <!-- 知识图谱 -->
      <template v-else-if="resource.type === 'knowledge-graph'">
        <div class="graph-section">
          <div class="section-title">
            <span class="title-icon">📊</span>
            <span>知识图谱</span>
          </div>
          <KnowledgeGraph :content="resource.content || ''" :weak-points="weakPoints" />
        </div>
      </template>

      <!-- 文档：Markdown 渲染 -->
      <template v-else>
        <div class="document-section">
          <div class="section-title">
            <span class="title-icon">📄</span>
            <span>学习文档</span>
          </div>
          <div class="doc-content markdown-body" v-html="renderMarkdown(resource.content || '')" />
        </div>
      </template>
    </div>

    <!-- 标签区域 -->
    <div v-if="resource.tags?.length" class="detail-tags">
      <span v-for="tag in resource.tags" :key="tag" class="tag-item">{{ tag }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import type { ResourceItem } from '../../../shared/types'
import MindMapViewer from './MindMapViewer.vue'
import KnowledgeGraph from './KnowledgeGraph.vue'
import { useProfileStore } from '../../profile/stores/profileStore'
import request from '../../../shared/utils/request'

const props = defineProps<{ resource: ResourceItem | null }>()
const emit = defineEmits<{
  (e: 'update:resource', resource: ResourceItem): void
}>()

const profileStore = useProfileStore()
const weakPoints = computed(() => profileStore.profileData.weak_points || [])

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
function renderMarkdown(text: string): string { return md.render(text) }

// ===== 视频生成状态 =====
const videoUrl = ref<string | null>(null)
const subtitleUrl = ref<string | null>(null)  // 字幕文件URL
const videoTaskId = ref<string | null>(null)
const videoStatus = ref<string>('idle')
const videoProgress = ref(0)
const videoMessage = ref('')
const generating = ref(false)
const showSubtitle = ref(true)  // 字幕开关状态
const videoPlayer = ref<HTMLVideoElement | null>(null)  // 视频播放器引用
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollFailureCount = 0
const MAX_POLL_FAILURES = 10  // 最大轮询失败次数（每次2秒，约20秒后放弃）

// 切换字幕显示
function toggleSubtitle() {
  showSubtitle.value = !showSubtitle.value
  if (videoPlayer.value && videoPlayer.value.textTracks.length > 0) {
    videoPlayer.value.textTracks[0].mode = showSubtitle.value ? 'showing' : 'hidden'
  }
}

// 从 resource 初始化视频状态
watch(() => props.resource, (res) => {
  // 停止旧的轮询
  stopPolling()
  if (res?.type === 'video') {
    // 只有真实视频URL（非B站链接）才显示播放器
    const url = res.url || null
    const isRealVideo = url && (url.endsWith('.mp4') || url.endsWith('.webm') || url.includes('/static/videos/'))
    videoUrl.value = isRealVideo ? url : null
    // 兼容两种字段命名：video_task_id 和 taskId
    const tid = res.video_task_id || res.taskId || null
    videoTaskId.value = tid
    // 兼容两种状态：videoStatus 字段 或 从 video_task_id 推断
    const vs = res.videoStatus
    videoStatus.value = isRealVideo ? 'done' : (vs === 'done' ? 'done' : vs === 'failed' ? 'failed' : (tid ? 'rendering' : 'idle'))
    videoProgress.value = 0
    videoMessage.value = ''
    generating.value = false
    // 如果有 task_id 但没有真实视频，开始轮询
    if (tid && !isRealVideo && vs !== 'done' && vs !== 'failed') {
      startPolling(tid)
    }
  }
}, { immediate: true, deep: true })

async function startGenerateVideo() {
  if (!props.resource || generating.value) return
  generating.value = true
  videoStatus.value = 'creating'
  videoMessage.value = '正在创建视频生成任务...'

  try {
    const knowledgePoint = props.resource.title || props.resource.module || '综合学习'
    const res = await request<{ status: string; task_id?: string; message?: string }>({
      url: '/video/generate',
      method: 'POST',
      data: { knowledge_point: knowledgePoint, style: 'rigorous' }
    })

    if (res.task_id) {
      videoTaskId.value = res.task_id
      videoStatus.value = 'rendering'
      videoMessage.value = '视频生成任务已创建...'
      startPolling(res.task_id)
    } else {
      videoStatus.value = 'failed'
      videoMessage.value = res.message || '创建任务失败'
    }
  } catch (e: any) {
    videoStatus.value = 'failed'
    videoMessage.value = e?.message || '网络错误'
  } finally {
    generating.value = false
  }
}

function startPolling(taskId: string) {
  stopPolling()
  pollFailureCount = 0
  pollTimer = setInterval(async () => {
    try {
      const data = await request<{
        status: string
        progress?: number
        message?: string
        video_url?: string
        subtitle_url?: string  // 字幕文件URL
      }>({
        url: `/video/task/${taskId}`,
        method: 'GET'
      })

      pollFailureCount = 0  // 成功时重置失败计数
      videoStatus.value = data.status
      if (data.progress !== undefined) videoProgress.value = data.progress
      if (data.message) videoMessage.value = data.message

      if ((data.status === 'done' || data.status === 'completed') && data.video_url) {
        videoUrl.value = data.video_url
        subtitleUrl.value = data.subtitle_url || null  // 保存字幕URL
        videoProgress.value = 100
        videoMessage.value = '视频生成完成'
        stopPolling()
        // 保存视频 URL 到资源对象，避免下次重新生成
        if (props.resource) {
          emit('update:resource', {
            ...props.resource,
            url: data.video_url,
            video_task_id: videoTaskId.value
          })
        }
      } else if (data.status === 'failed') {
        stopPolling()
      }
    } catch {
      // 网络错误累计失败次数，超过上限后放弃轮询
      pollFailureCount++
      if (pollFailureCount >= MAX_POLL_FAILURES) {
        stopPolling()
        videoStatus.value = 'failed'
        videoMessage.value = '视频服务连接失败，请检查 AI Tutor 服务是否正常运行后重试'
      }
    }
  }, 2000)
}

// 取消视频生成
function cancelVideoGeneration() {
  stopPolling()
  videoStatus.value = 'failed'
  videoMessage.value = '已取消视频生成'
  videoProgress.value = 0
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 删除视频并重新生成
function deleteAndRegenerate() {
  if (!props.resource || generating.value) return
  
  // 清除当前视频状态
  videoUrl.value = null
  videoTaskId.value = null
  videoStatus.value = 'idle'
  videoProgress.value = 0
  videoMessage.value = ''
  
  // 通知父组件清除资源中的视频 URL
  emit('update:resource', {
    ...props.resource,
    url: null,
    video_task_id: null
  })
  
  // 开始重新生成
  startGenerateVideo()
}

function onVideoError(e: Event) {
  console.error('[Video Error]', e)
  videoMessage.value = '视频加载失败，请刷新重试'
}

onUnmounted(() => stopPolling())

const typeLabel = computed(() => {
  const map: Record<string, string> = {
    document: '文档', video: '视频', code: '代码',
    exercise: '习题', mindmap: '导图', 'knowledge-graph': '图谱'
  }
  return map[props.resource?.type || ''] || '资源'
})

const typeIcon = computed(() => {
  const map: Record<string, string> = {
    document: '📄', video: '🎬', code: '💻',
    exercise: '📝', mindmap: '🗺️', 'knowledge-graph': '📊'
  }
  return map[props.resource?.type || ''] || '📦'
})

const typeColor = computed(() => {
  const map: Record<string, string> = {
    document: '#00CFE8', video: '#EA5455', code: '#28C76F',
    exercise: '#FF9F43', mindmap: '#7367F0', 'knowledge-graph': '#f59e0b'
  }
  return map[props.resource?.type || ''] || '#6E6B7B'
})

const difficultyLabel = computed(() => {
  const map: Record<string, string> = {
    basic: '基础', intermediate: '进阶', advanced: '高级'
  }
  return map[props.resource?.difficulty || ''] || props.resource?.difficulty || '基础'
})

const codeLanguage = computed(() => {
  const content = props.resource?.content || ''
  if (content.includes('def ') || content.includes('import ')) return 'Python'
  if (content.includes('function ') || content.includes('const ')) return 'JavaScript'
  if (content.includes('class ') || content.includes('public ')) return 'Java'
  return 'Code'
})

function copyCode() {
  const content = props.resource?.content || ''
  navigator.clipboard.writeText(content)
}
</script>

<style lang="less" scoped>
.resource-detail {
  padding: 20px;
  background: #FFFFFF;
  border-radius: 12px;
  max-height: 75vh;  // 限制高度，内容内部滚动
  overflow-y: auto;  // 内容滚动在组件内处理
  
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 2px; }
}

/* ===== 头部区域 ===== */
.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #E5E7EB;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.badge-icon {
  font-size: 16px;
}

.badge-text {
  font-size: 13px;
}

.header-info {
  flex: 1;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 10px 0;
  line-height: 1.4;
}

.detail-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  background: #F1F5F9;
  color: #64748B;

  .tag-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  &.difficulty {
    background: #DBEAFE;
    color: #3B82F6;
  }

  &.module {
    background: #F3E8FF;
    color: #7C3AED;
  }

  &.source {
    background: #D1FAE5;
    color: #10B981;
  }
}

/* ===== 内容区域 ===== */
.detail-body {
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #F8FAFC, #F1F5F9);
  border-radius: 8px;
  border: 1px solid #E5E7EB;

  .title-icon {
    font-size: 16px;
  }

  span:last-child {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
  }
}

/* ===== 视频区域 ===== */
.video-section {
  .video-player-wrapper {
    border-radius: 12px;
    overflow: hidden;
    background: #000;
    border: 1px solid #334155;

    .video-controls-bar {
      display: flex;
      justify-content: flex-end;
      padding: 8px 12px;
      background: #1E293B;
      
      .subtitle-toggle {
        padding: 4px 12px;
        border-radius: 6px;
        border: 1px solid #475569;
        background: #334155;
        color: #94A3B8;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
        
        &:hover {
          background: #475569;
        }
        
        &.active {
          background: #2563eb;
          color: #fff;
          border-color: #2563eb;
        }
      }
    }

    .video-player {
      width: 100%;
      max-height: 480px;
      display: block;
    }

    .video-meta {
      display: flex;
      gap: 16px;
      padding: 10px 16px;
      background: #1E293B;
      color: #94A3B8;
      font-size: 12px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .video-generating {
    display: flex;
    gap: 16px;
    padding: 24px;
    border-radius: 12px;
    background: linear-gradient(135deg, #FEF3C7, #FED7AA);
    border: 1px solid #FCD34D;

    .generating-icon {
      flex-shrink: 0;

      .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid #F59E0B;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
    }

    .generating-info {
      flex: 1;

      .generating-title {
        font-size: 14px;
        font-weight: 600;
        color: #92400E;
        margin: 0 0 10px 0;
      }

      .generating-progress {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;

        .progress-track {
          flex: 1;
          height: 8px;
          background: rgba(255, 255, 255, 0.5);
          border-radius: 4px;
          overflow: hidden;

          .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #F59E0B, #EA580C);
            border-radius: 4px;
            transition: width 0.5s ease;
          }
        }

        .progress-text {
          font-size: 12px;
          font-weight: 600;
          color: #92400E;
          min-width: 36px;
          text-align: right;
        }
      }

      .generating-message {
        font-size: 12px;
        color: #78350F;
        margin: 0;
      }

      .cancel-gen-btn {
        margin-top: 10px;
        padding: 6px 16px;
        border-radius: 6px;
        background: rgba(239, 68, 68, 0.1);
        color: #DC2626;
        font-size: 12px;
        font-weight: 500;
        border: 1px solid rgba(239, 68, 68, 0.3);
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background: rgba(239, 68, 68, 0.2);
        }
      }
    }
  }

  .video-card {
    padding: 20px;
    border-radius: 12px;
    background: linear-gradient(135deg, #FEF2F2, #FFF7ED);
    border: 1px solid #FECACA;

    &.empty {
      background: #F8FAFC;
      border-color: #E5E7EB;
      text-align: center;
      padding: 40px 20px;

      .empty-icon {
        font-size: 40px;
        margin-bottom: 10px;
      }

      .empty-text {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 6px;
      }

      .empty-sub {
        font-size: 12px;
        color: #94A3B8;
        margin-bottom: 16px;
      }

      .generate-btn {
        padding: 10px 24px;
        border-radius: 8px;
        background: linear-gradient(135deg, #F59E0B, #EA580C);
        color: #fff;
        font-size: 13px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.2s;

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(245, 158, 11, 0.3);
        }

        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }

      .video-actions {
        display: flex;
        justify-content: center;
        margin-top: 12px;
      }

      .regenerate-btn {
        padding: 8px 20px;
        border-radius: 6px;
        background: #f1f5f9;
        color: #64748b;
        font-size: 12px;
        font-weight: 500;
        border: 1px solid #e2e8f0;
        cursor: pointer;
        transition: all 0.2s;

        &:hover:not(:disabled) {
          background: #e2e8f0;
          color: #475569;
        }

        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 代码区域 ===== */
.code-section {
  .code-container {
    border-radius: 12px;
    background: #1E293B;
    overflow: hidden;
    border: 1px solid #334155;
  }

  .code-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: #334155;
    border-bottom: 1px solid #475569;
  }

  .code-lang {
    font-size: 12px;
    color: #94A3B8;
    font-weight: 500;
  }

  .copy-btn {
    padding: 4px 12px;
    border-radius: 4px;
    background: #475569;
    color: #E2E8F0;
    font-size: 11px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #64748B;
    }
  }

  .code-block {
    padding: 16px;
    margin: 0;
    overflow-x: auto;
    font-family: 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
    color: #E2E8F0;
    background: transparent;

    code {
      background: transparent;
      padding: 0;
    }
  }
}

/* ===== Markdown 内容 ===== */
.markdown-body {
  padding: 16px;
  background: #F8FAFC;
  border-radius: 10px;
  border: 1px solid #E5E7EB;

  :deep(h1), :deep(h2), :deep(h3) {
    color: #1E293B;
    margin: 16px 0 10px;
    font-weight: 700;
  }

  :deep(h1) {
    font-size: 18px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E5E7EB;
  }

  :deep(h2) {
    font-size: 16px;
  }

  :deep(h3) {
    font-size: 14px;
    color: #334155;
  }

  :deep(p) {
    margin: 10px 0;
    font-size: 14px;
    line-height: 1.8;
    color: #475569;
  }

  :deep(ul), :deep(ol) {
    margin: 10px 0;
    padding-left: 24px;
  }

  :deep(li) {
    margin: 6px 0;
    font-size: 14px;
    color: #475569;
    line-height: 1.6;
  }

  :deep(pre) {
    background: #1E293B;
    border-radius: 8px;
    padding: 14px 16px;
    overflow-x: auto;
    margin: 12px 0;
    border: 1px solid #334155;

    code {
      color: #E2E8F0;
      font-family: 'Fira Code', monospace;
      font-size: 13px;
      background: transparent;
      padding: 0;
    }
  }

  :deep(code) {
    background: #F1F5F9;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
    font-size: 13px;
    color: #7C3AED;
  }

  :deep(strong) {
    color: #1E293B;
    font-weight: 600;
  }

  :deep(blockquote) {
    border-left: 4px solid #3B82F6;
    padding: 10px 16px;
    margin: 12px 0;
    background: #EFF6FF;
    border-radius: 0 8px 8px 0;
    color: #64748B;
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    border-radius: 8px;
    overflow: hidden;

    th, td {
      border: 1px solid #E5E7EB;
      padding: 10px 14px;
      font-size: 13px;
    }

    th {
      background: #F1F5F9;
      color: #334155;
      font-weight: 600;
    }

    td {
      color: #475569;
    }
  }
}

/* ===== 标签区域 ===== */
.detail-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 16px;
  border-top: 1px solid #E5E7EB;
}

.tag-item {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 6px;
  background: linear-gradient(135deg, #EFF6FF, #DBEAFE);
  color: #3B82F6;
  font-weight: 500;
  border: 1px solid #BFDBFE;
}
</style>