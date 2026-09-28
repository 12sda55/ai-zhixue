<template>
  <div class="resource-card" @click="onCardClick">
    <div class="card-type-badge" :style="{ background: typeColors[item.type] }">
      {{ typeIcons[item.type] }} {{ typeLabels[item.type] }}
    </div>
    <div class="card-title">{{ item.title }}</div>
    <div class="card-module">{{ item.module }}</div>

    <!-- P1优化7新增：预计剩余时间显示 -->
    <div class="estimated-time" v-if="generating && estimatedTimeRemaining">
      <span class="time-icon">⏱️</span>
      <span class="time-text">预计剩余: {{ estimatedTimeRemaining }}</span>
    </div>

    <!-- P1优化7新增：重试状态显示 -->
    <div class="retry-status" v-if="retryCount > 0 && generating">
      <span class="retry-icon">🔄</span>
      <span class="retry-text">重试 {{ retryCount }}/{{ MAX_RETRIES }}</span>
    </div>

    <!-- 视频类型特殊处理：显示生成状态和操作按钮 -->
    <div class="video-card-actions" v-if="item.type === 'video'" @click.stop>
      <!-- 生成中：优先显示进度条 + 取消按钮 -->
      <template v-if="generating">
        <div class="card-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ progress }}%</span>
          <button class="card-btn cancel" @click="cancelGenerate">取消</button>
        </div>
        <!-- P1优化7新增：显示当前阶段 -->
        <div class="stage-message" v-if="currentStage">{{ currentStage }}</div>
        <div class="progress-message" v-if="statusMessage">{{ statusMessage }}</div>
      </template>
      <!-- 未生成 -->
      <template v-if="!hasVideo && !item.videoStatus">
        <button class="card-btn generate" @click="startGenerate">
          生成视频
        </button>
      </template>
      <!-- 后台渲染中（异步视频） -->
      <template v-else-if="item.videoStatus === 'pending' || item.videoStatus === 'running'">
        <div class="video-status pending">
          <span class="status-icon">⏳</span>
          <span class="status-text">后台渲染中...</span>
          <span class="status-progress">{{ progress > 0 ? `${progress}%` : '启动中' }}</span>
        </div>
      </template>
      <!-- P1优化7新增：降级方案展示 -->
      <template v-else-if="item.videoStatus === 'fallback'">
        <div class="degraded-content">
          <div class="degraded-header">
            <span class="degraded-icon">📄</span>
            <span class="degraded-title">替代学习资源</span>
          </div>
          <div class="degraded-body">
            <div class="degraded-item" v-if="item.degradedContent?.document">
              <span class="item-type">文档</span>
              <span class="item-title">{{ item.degradedContent.document.title }}</span>
            </div>
            <div class="degraded-item" v-if="item.degradedContent?.mindmap">
              <span class="item-type">导图</span>
              <span class="item-title">{{ item.degradedContent.mindmap.title }}</span>
            </div>
          </div>
          <button class="retry-btn" @click="regenerate">
            重新生成视频
          </button>
        </div>
      </template>
      <!-- 视频生成失败 -->
      <template v-else-if="item.videoStatus === 'failed'">
        <div class="video-status failed">
          <span class="status-icon">❌</span>
          <span class="status-text">生成失败</span>
          <span class="status-error">{{ item.description }}</span>
          <button class="card-btn retry" @click="regenerate">重新生成</button>
        </div>
      </template>
      <!-- P1优化7新增：超时状态 -->
      <template v-else-if="item.videoStatus === 'timeout'">
        <div class="video-status timeout">
          <span class="status-icon">⏱️</span>
          <span class="status-text">生成超时</span>
          <span class="status-error">请稍后重试</span>
          <button class="card-btn retry" @click="regenerate">重新生成</button>
        </div>
      </template>
      <!-- 已生成 -->
      <template v-else>
        <div class="video-status">
          <span class="status-icon">✅</span>
          <span class="status-text">视频已生成</span>
          <button class="card-btn regenerate" @click="regenerate">重新生成</button>
        </div>
      </template>
    </div>

    <!-- 非视频类型的普通meta -->
    <div class="card-meta" v-else>
      <span class="card-time">{{ item.createdAt }}</span>
      <span v-if="item.aiGenerated" class="ai-badge">AI 生成</span>
      <button class="card-btn regenerate-small" @click.stop="regenerateOther">重新生成</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import type { ResourceItem } from '../../../shared/types'
import { useAgentStore } from '../../agent/stores/agentStore'
import { useResourceStore } from '../stores/resourceStore'

// P1优化7新增常量
const MAX_RETRIES = 3
const POLL_INTERVAL = 2000
const MAX_POLL_TIME = 300000 // 5分钟最大轮询时间

const props = defineProps<{ item: ResourceItem }>()
const emit = defineEmits(['click', 'update:item'])

const agentStore = useAgentStore()
const resourceStore = useResourceStore()

// ===== 使用 store 持久化状态，解决切换卡片进度消失问题 =====
const task = computed(() => resourceStore.getVideoGenerationTask(props.item.id))
const generating = computed(() => task.value?.generating ?? false)
const progress = computed(() => task.value?.progress ?? 0)
const statusMessage = computed(() => task.value?.statusMessage ?? '')
const taskId = computed(() => task.value?.taskId ?? null)
const retryCount = computed(() => task.value?.retryCount ?? 0)
const estimatedTimeRemaining = computed(() => task.value?.estimatedTimeRemaining ?? '')
const currentStage = computed(() => task.value?.currentStage ?? '')
let pollTimer: number | null = null

// 判断是否有视频
const hasVideo = computed(() => props.item.url && props.item.url.startsWith('http'))

// ===== 组件挂载时恢复轮询 =====
onMounted(() => {
  if (task.value && task.value.generating && task.value.taskId) {
    // 有正在进行的任务，恢复轮询
    startPolling()
  }
})

// 组件卸载时停止轮询（但不清除 store 状态）
onUnmounted(() => {
  stopPolling()
})

// 监听视频 Agent 进度（同步到卡片显示）
watch(
  () => props.item.videoStatus,
  (status) => {
    if (status === 'pending' || status === 'running') {
      const videoAgent = agentStore.agents[5]
      if (videoAgent && videoAgent.status === 'running') {
        resourceStore.updateVideoGenerationProgress(
          props.item.id,
          videoAgent.progress,
          videoAgent.log?.[videoAgent.log.length - 1] ?? '',
          ''
        )
      }
    }
  },
  { immediate: true }
)

// 定时同步视频 Agent 进度
watch(
  () => agentStore.agents[5]?.progress,
  (newProgress) => {
    if (props.item.videoStatus === 'pending' || props.item.videoStatus === 'running') {
      resourceStore.updateVideoGenerationProgress(props.item.id, newProgress || 0, '', '')
    }
  }
)

// 点击卡片
function onCardClick() {
  emit('click')
}

// 开始生成视频
async function startGenerate() {
  if (generating.value) return

  try {
    const res = await axios.post('/api/v1/video/generate', {
      knowledge_point: props.item.title,
      style: 'whiteboard'
    })

    if (res.data.status === 'created') {
      // 在 store 中创建任务
      resourceStore.startVideoGeneration(props.item.id, props.item.title, res.data.task_id)
      startPolling()
    } else if (res.data.status === 'fallback') {
      handleFallback(res.data)
    } else {
      await handleRetry()
    }
  } catch (e: any) {
    console.error('生成视频失败', e)
    await handleRetry()
  }
}

// 轮询方法
function startPolling() {
  if (pollTimer) clearInterval(pollTimer)

  const startTime = Date.now()

  pollTimer = setInterval(async () => {
    if (Date.now() - startTime > MAX_POLL_TIME) {
      stopPolling()
      handleTimeout()
      return
    }

    const currentTaskId = taskId.value
    if (!currentTaskId) return

    try {
      const res = await axios.get(`/api/v1/video/status/${currentTaskId}`)
      const data = res.data

      // 更新 store 状态
      resourceStore.updateVideoGenerationProgress(
        props.item.id,
        data.progress || 0,
        data.message || '',
        getStageMessage(data.stage, data.message)
      )

      console.log('[Polling]', data.status, data.progress, data.stage)

      if ((data.status === 'done' || data.status === 'completed') && data.video_url) {
        handleSuccess(data)
      } else if (data.status === 'failed') {
        handleFailure(data)
      } else if (data.status === 'fallback') {
        handleFallback(data)
      }
    } catch (e) {
      console.error('轮询失败', e)
      // P1优化7新增：网络错误不停止轮询，继续尝试
    }
  }, POLL_INTERVAL)
}

// P1优化7新增：获取阶段消息
function getStageMessage(stage: string, message: string): string {
  const stageMessages: Record<string, string> = {
    'initialized': '任务初始化中...',
    'outline': '正在分析知识点结构...',
    'scenes': '正在生成场景代码...',
    'rendering': '正在渲染视频画面...',
    'encoding': '正在编码输出文件...',
    'syncing': '正在进行音画同步...'
  }
  return message || stageMessages[stage] || '正在处理...'
}

// 处理成功
function handleSuccess(data: any) {
  stopPolling()
  resourceStore.completeVideoGeneration(props.item.id)

  console.log('[Emit update:item] video_url:', data.video_url)
  emit('update:item', { ...props.item, url: data.video_url, videoStatus: 'done' })
}

// 处理失败（带重试）
async function handleFailure(data: any) {
  const currentRetryCount = retryCount.value
  if (currentRetryCount < MAX_RETRIES) {
    resourceStore.updateVideoRetryCount(props.item.id, currentRetryCount + 1)
    resourceStore.updateVideoGenerationProgress(
      props.item.id, 0, `生成失败，正在重试 (${currentRetryCount + 1}/${MAX_RETRIES})...`, ''
    )

    // 等待一段时间后重试
    await new Promise(resolve => setTimeout(resolve, 2000 * (currentRetryCount + 1)))

    // 重新创建任务
    try {
      const res = await axios.post('/api/v1/video/generate', {
        knowledge_point: props.item.title,
        style: 'whiteboard',
        retry_strategy: getRetryStrategy(currentRetryCount + 1)
      })

      if (res.data.status === 'created') {
        resourceStore.startVideoGeneration(props.item.id, props.item.title, res.data.task_id)
        startPolling()
      } else {
        handleFallback(res.data)
      }
    } catch (e) {
      console.error('重试失败', e)
      handleFallback(data)
    }
  } else {
    // 重试次数用尽，显示降级内容
    handleFallback(data)
  }
}

// 获取重试策略
function getRetryStrategy(retryCount: number): string {
  const strategies = ['default', 'simplified', 'preset_template']
  return strategies[Math.min(retryCount - 1, strategies.length - 1)]
}

// 处理超时
function handleTimeout() {
  resourceStore.failVideoGeneration(props.item.id, '生成超时，请稍后重试')
  emit('update:item', { ...props.item, videoStatus: 'timeout' })
}

// 处理降级方案
function handleFallback(data: any) {
  stopPolling()
  resourceStore.cancelVideoGeneration(props.item.id)

  if (data.alternative_resources) {
    emit('update:item', {
      ...props.item,
      videoStatus: 'fallback',
      degradedContent: data.alternative_resources
    })
  } else {
    emit('update:item', { ...props.item, videoStatus: 'failed' })
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 取消生成
function cancelGenerate() {
  stopPolling()
  resourceStore.cancelVideoGeneration(props.item.id)

  // 调用后端API取消任务
  const currentTaskId = taskId.value
  if (currentTaskId) {
    axios.post(`/api/v1/video/cancel/${currentTaskId}`).catch(() => {})
  }
}

// 重新生成
async function regenerate() {
  // 重置状态
  emit('update:item', { ...props.item, url: null, videoStatus: null })
  resourceStore.cancelVideoGeneration(props.item.id)
  await startGenerate()
}

// 重新生成非视频类型资源
async function regenerateOther() {
  const topic = props.item.module || props.item.title.replace(' 知识讲解', '').replace(' 知识导图', '').replace(' 练习题', '').replace(' 代码示例', '')
  const newResource = await agentStore.regenerateSingleResource(props.item.type, topic)
  if (newResource) {
    emit('update:item', newResource)
  }
}

// 如果资源已经有 task_id 且状态不是 completed，恢复轮询
onMounted(() => {
  const tid = props.item.video_task_id || props.item.taskId
  if (tid && !hasVideo.value && props.item.videoStatus !== 'done' && props.item.videoStatus !== 'failed') {
    taskId.value = tid
    generating.value = true
    startPolling()
  }
})

onUnmounted(() => stopPolling())

const typeColors: Record<string, string> = {
  document: 'rgba(0, 207, 232, 0.12)',
  mindmap: 'rgba(115, 103, 240, 0.12)',
  'knowledge-graph': 'rgba(245, 158, 11, 0.12)',
  code: 'rgba(40, 199, 111, 0.12)',
  video: 'rgba(255, 159, 67, 0.12)',
  quiz: 'rgba(234, 84, 85, 0.12)',
}

const typeIcons: Record<string, string> = {
  document: '📄', mindmap: '🗺️', 'knowledge-graph': '🔗', code: '💻', video: '🎬', quiz: '📝',
}

const typeLabels: Record<string, string> = {
  document: '文档', mindmap: '导图', 'knowledge-graph': '图谱', code: '代码', video: '视频', quiz: '题库',
}
</script>

<style lang="less" scoped>
.resource-card {
  background: transparent;
  border: 1px solid #EBE9F1;
  border-radius: 12px;
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  min-height: 140px;

  &:hover {
    border-color: rgba(0, 207, 232, 0.3);
    box-shadow: 0 4px 12px rgba(76, 78, 100, 0.08);
    transform: translateY(-2px);
  }
}

.card-type-badge {
  display: inline-flex;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #00CFE8;
  margin-bottom: 10px;
  font-weight: 500;
}

.card-title {
  color: #2F2B3D;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  margin-bottom: 6px;
  min-height: 21px;
}

.card-module {
  color: #A8AAAE;
  font-size: 12px;
  margin-bottom: 12px;
  flex: 1;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}

.card-time {
  color: #A8AAAE;
  font-size: 12px;
}

.ai-badge {
  background: rgba(0, 207, 232, 0.08);
  border-radius: 4px;
  padding: 3px 8px;
  color: #00CFE8;
  font-size: 11px;
  font-weight: 500;
}

.card-btn.regenerate-small {
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.2);
  color: #2563eb;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: auto;
  font-weight: 500;

  &:hover {
    background: rgba(37, 99, 235, 0.15);
    border-color: rgba(37, 99, 235, 0.3);
    transform: translateY(-1px);
  }
}

// 视频卡片操作区域
.video-card-actions {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 207, 232, 0.08);
}

.card-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s;

  &.generate {
    background: linear-gradient(135deg, #F59E0B, #EA580C);
    color: #fff;

    &:hover:not(:disabled) {
      transform: scale(1.02);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &.cancel {
    background: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    padding: 4px 8px;
    font-size: 10px;
    margin-left: 8px;

    &:hover {
      background: #fee2e2;
      color: #ef4444;
      border-color: #fecaca;
    }
  }

  &.regenerate {
    background: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    padding: 4px 8px;
    font-size: 10px;

    &:hover {
      background: #e2e8f0;
    }
  }
}

.progress-message {
  font-size: 10px;
  color: #64748b;
  margin-top: 4px;
  text-align: center;
}

// P1优化7新增样式：预计剩余时间
.estimated-time {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 6px;

  .time-icon {
    font-size: 12px;
  }

  .time-text {
    font-size: 11px;
    color: #3b82f6;
  }
}

// P1优化7新增样式：重试状态
.retry-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;

  .retry-icon {
    font-size: 12px;
    animation: spin 1s linear infinite;
  }

  .retry-text {
    font-size: 11px;
    color: #f59e0b;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// P1优化7新增样式：阶段消息
.stage-message {
  font-size: 10px;
  color: #3b82f6;
  margin-top: 4px;
  padding: 4px 8px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 4px;
  text-align: center;
}

.card-progress {
  display: flex;
  align-items: center;
  gap: 8px;

  .progress-bar {
    flex: 1;
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(135deg, #F59E0B, #EA580C);
    border-radius: 3px;
    transition: width 0.3s;
  }

  .progress-text {
    font-size: 11px;
    color: #64748b;
    min-width: 32px;
  }
}

.video-status {
  display: flex;
  align-items: center;
  gap: 6px;

  .status-icon {
    font-size: 12px;
  }

  .status-text {
    font-size: 11px;
    color: #22c55e;
  }

  &.pending {
    .status-text {
      color: #f59e0b;
    }
    .status-progress {
      font-size: 10px;
      color: #64748b;
      margin-left: 4px;
    }
  }

  &.failed {
    flex-wrap: wrap;
    gap: 4px;

    .status-text {
      color: #ef4444;
      font-weight: 500;
    }

    .status-error {
      font-size: 10px;
      color: #64748b;
      width: 100%;
      margin-top: 4px;
      padding: 4px 8px;
      background: rgba(239, 68, 68, 0.08);
      border-radius: 4px;
    }
  }

  // P1优化7新增：超时状态
  &.timeout {
    flex-wrap: wrap;
    gap: 4px;

    .status-text {
      color: #f59e0b;
      font-weight: 500;
    }

    .status-error {
      font-size: 10px;
      color: #64748b;
      width: 100%;
      margin-top: 4px;
      padding: 4px 8px;
      background: rgba(245, 158, 11, 0.08);
      border-radius: 4px;
    }
  }
}

.card-btn.retry {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
  font-size: 10px;
  padding: 4px 8px;
  margin-left: 8px;

  &:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: rgba(239, 68, 68, 0.3);
  }
}

// P1优化7新增：降级内容展示
.degraded-content {
  margin-top: 12px;
  padding: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 8px;

  .degraded-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;

    .degraded-title {
      font-size: 12px;
      font-weight: 600;
      color: #22c55e;
    }
  }

  .degraded-body {
    .degraded-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(34, 197, 94, 0.1);

      &:last-child {
        border-bottom: none;
      }

      .item-type {
        font-size: 10px;
        padding: 2px 6px;
        background: rgba(34, 197, 94, 0.15);
        border-radius: 4px;
        color: #22c55e;
      }

      .item-title {
        font-size: 11px;
        color: #374151;
      }
    }
  }

  .retry-btn {
    margin-top: 10px;
    width: 100%;
    padding: 8px;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      transform: scale(1.02);
    }
  }
}
</style>