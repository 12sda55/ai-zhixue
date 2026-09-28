<template>
  <div class="resource-card" @click="onCardClick">
    <div class="card-type-badge" :style="{ background: typeColors[item.type] }">
      {{ typeIcons[item.type] }} {{ typeLabels[item.type] }}
    </div>
    <div class="card-title">{{ item.title }}</div>
    <div class="card-module">{{ item.module }}</div>
    <!-- UX-3: 匹配度标签 -->
    <div v-if="matchLabel.text" class="card-match-badge" :class="matchLabel.class">
      {{ matchLabel.text }} {{ matchScore }}%
    </div>

    <!-- 资源管理：收藏 / 掌握 / 评分 -->
    <div class="card-manage" @click.stop>
      <button
        class="manage-btn"
        :class="{ active: item.favorited }"
        :title="item.favorited ? '取消收藏' : '收藏'"
        @click="toggleFav"
      >{{ item.favorited ? '★' : '☆' }}</button>
      <button
        class="manage-btn mastered-btn"
        :class="{ active: item.mastered }"
        :title="item.mastered ? '取消已掌握' : '标记已掌握'"
        @click="toggleMastered"
      >{{ item.mastered ? '✓ 已掌握' : '○ 未掌握' }}</button>
      <div class="rating-stars">
        <button
          v-for="star in 5"
          :key="star"
          class="star-btn"
          :class="{ filled: star <= (item.rating || 0) }"
          @click="setRating(star)"
          @dblclick="setRating(0)"
          :title="`${star} 星`"
        >★</button>
      </div>
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
      <!-- 视频生成失败 -->
      <template v-else-if="item.videoStatus === 'failed'">
        <div class="video-status failed">
          <span class="status-icon">❌</span>
          <span class="status-text">生成失败</span>
          <span class="status-error">{{ item.description }}</span>
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
      <button class="card-btn regenerate-small" @click.stop="openFeedback">退回重做</button>
    </div>

    <!-- 退回重做反馈对话框（Teleport 到 body，避免卡片 transition 导致闪屏） -->
    <Teleport to="body">
    <div v-if="showFeedback" class="feedback-overlay" @click.stop>
      <div class="feedback-dialog" @click.stop>
        <div class="feedback-header">
          <span class="feedback-title">退回重做</span>
          <button class="feedback-close" @click="cancelFeedback">✕</button>
        </div>
        <div class="feedback-section">
          <div class="feedback-label">请选择不满意的原因 <span class="required">*</span></div>
          <div class="feedback-tags">
            <button
              v-for="reason in feedbackReasons"
              :key="reason"
              class="feedback-tag"
              :class="{ active: selectedReason === reason }"
              @click="selectedReason = reason"
            >{{ reason }}</button>
          </div>
        </div>
        <div class="feedback-section">
          <div class="feedback-label">补充说明（可选）</div>
          <textarea
            v-model="feedbackDetail"
            class="feedback-input"
            placeholder="具体哪里不满意？希望如何改进？"
            rows="3"
          ></textarea>
        </div>
        <div class="feedback-actions">
          <button class="card-btn cancel" @click="cancelFeedback">取消</button>
          <button
            class="card-btn confirm"
            :disabled="!selectedReason || regenerating"
            @click="confirmRegenerate"
          >{{ regenerating ? '重做中...' : '确认重做' }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import type { ResourceItem } from '../../../shared/types'
import { useAgentStore } from '../../agent/stores/agentStore'
import { useResourceStore } from '../stores/resourceStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { calcMatchScore, getMatchLabel } from '../../../shared/utils/matchScorer'

const props = defineProps<{ item: ResourceItem }>()
const emit = defineEmits(['click', 'update:item'])

const agentStore = useAgentStore()
const resourceStore = useResourceStore()
const profileStore = useProfileStore()

// UX-3: 匹配度计算
const matchScore = computed(() => {
  return props.item.match_score ?? calcMatchScore(props.item, profileStore.profileData)
})
const matchLabel = computed(() => getMatchLabel(matchScore.value))

// ===== 使用 store 持久化状态，解决切换页面进度消失问题 =====
const task = computed(() => resourceStore.getVideoGenerationTask(props.item.id))
const generating = computed(() => task.value?.generating ?? false)
const progress = computed(() => task.value?.progress ?? 0)
const statusMessage = computed(() => task.value?.statusMessage ?? '')
let pollTimer: number | null = null

function getCurrentTaskId(): string | null {
  return task.value?.taskId ?? null
}

// 判断是否有视频
const hasVideo = computed(() => props.item.url && props.item.url.startsWith('http'))

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
    if (res.data.task_id) {
      resourceStore.startVideoGeneration(props.item.id, props.item.title, res.data.task_id)
      startPolling()
    }
  } catch (e: any) {
    console.error('生成视频失败', e)
  }
}

// 开始轮询状态
function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    const currentTaskId = getCurrentTaskId()
    if (!currentTaskId) return
    try {
      const res = await axios.get(`/api/v1/video/task/${currentTaskId}`)
      const data = res.data

      resourceStore.updateVideoGenerationProgress(
        props.item.id,
        data.progress || 0,
        data.message || '',
        ''
      )

      console.log('[Polling]', data.status, data.progress, data.video_url)

      if ((data.status === 'done' || data.status === 'completed') && data.video_url) {
        stopPolling()
        resourceStore.completeVideoGeneration(props.item.id)
        console.log('[Emit update:item] video_url:', data.video_url)
        emit('update:item', { ...props.item, url: data.video_url })
      } else if (data.status === 'failed') {
        stopPolling()
        resourceStore.failVideoGeneration(props.item.id, data.message || '视频生成失败')
      }
    } catch (e) {
      console.error('轮询失败', e)
    }
  }, 2000)
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
}

// 重新生成
async function regenerate() {
  emit('update:item', { ...props.item, url: null })
  resourceStore.cancelVideoGeneration(props.item.id)

  try {
    const res = await axios.post('/api/v1/video/generate', {
      knowledge_point: props.item.title,
      style: 'whiteboard'
    })
    if (res.data.task_id) {
      resourceStore.startVideoGeneration(props.item.id, props.item.title, res.data.task_id)
      startPolling()
    }
  } catch (e: any) {
    console.error('重新生成视频失败', e)
    resourceStore.cancelVideoGeneration(props.item.id)
  }
}

// ===== 资源管理：收藏 / 掌握 / 评分 =====
// 只更新 store，不 emit update:item —— store 变更会自动触发 reactive 更新，
// 双重更新（store + emit）会导致父组件 onCardItemUpdate 再次赋值，引发闪屏
function toggleFav() {
  resourceStore.toggleFavorite(props.item.id)
}

function toggleMastered() {
  const next = !props.item.mastered
  resourceStore.markMastered(props.item.id, next)
}

function setRating(star: number) {
  const next = props.item.rating === star ? 0 : star
  resourceStore.rateResource(props.item.id, next)
}

// ===== 退回重做反馈闭环 =====
const feedbackReasons = ['内容不相关', '太难', '太简单', '有错误', '其他']
const showFeedback = ref(false)
const selectedReason = ref('')
const feedbackDetail = ref('')
const regenerating = ref(false)

function openFeedback() {
  showFeedback.value = true
  selectedReason.value = ''
  feedbackDetail.value = ''
}

function cancelFeedback() {
  showFeedback.value = false
  selectedReason.value = ''
  feedbackDetail.value = ''
}

async function confirmRegenerate() {
  if (!selectedReason.value || regenerating.value) return
  regenerating.value = true
  const topic = props.item.module || props.item.title.replace(' 知识讲解', '').replace(' 知识导图', '').replace(' 练习题', '').replace(' 代码示例', '')
  const feedback = {
    reason: selectedReason.value,
    detail: feedbackDetail.value.trim() || undefined,
  }
  await agentStore.regenerateSingleResource(props.item.type, topic, feedback)
  regenerating.value = false
  showFeedback.value = false
  // 不需要 emit update:item —— regenerateSingleResource 已在 store 中原地替换内容，
  // Vue 响应式会自动传播更新到卡片和详情面板
}

// ===== 组件挂载：恢复已有任务 =====
onMounted(() => {
  const existingTask = resourceStore.getVideoGenerationTask(props.item.id)
  if (existingTask && existingTask.generating && existingTask.taskId) {
    startPolling()
  }
})

// 组件卸载：停止轮询但保留 store 状态
onUnmounted(() => {
  stopPolling()
})

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
  margin-bottom: 8px;
  flex: 1;
}

/* UX-3: 匹配度标签 */
.card-match-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 8px;
  display: inline-block;
  margin-bottom: 10px;
}

.card-match-badge.match-high {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.card-match-badge.match-medium {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.card-match-badge.match-normal {
  background: rgba(168, 170, 174, 0.1);
  color: #8a8a9a;
  border: 1px solid rgba(168, 170, 174, 0.15);
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

/* 资源管理工具栏 */
.card-manage {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 4px 0;
}

.manage-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #A8AAAE;
  padding: 2px 4px;
  transition: all 0.2s;
  line-height: 1;

  &:hover {
    color: #6366f1;
    transform: scale(1.1);
  }

  &.active {
    color: #f59e0b;
  }

  &.mastered-btn {
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    background: #f8fafc;

    &:hover {
      border-color: rgba(34, 197, 94, 0.4);
      color: #22c55e;
    }

    &.active {
      background: rgba(34, 197, 94, 0.1);
      border-color: rgba(34, 197, 94, 0.3);
      color: #22c55e;
      font-weight: 500;
    }
  }
}

.rating-stars {
  display: flex;
  gap: 1px;
  margin-left: auto;
}

.star-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #e2e8f0;
  padding: 0 1px;
  transition: all 0.15s;
  line-height: 1;

  &:hover {
    color: #fbbf24;
    transform: scale(1.15);
  }

  &.filled {
    color: #f59e0b;
  }
}

/* 退回重做反馈对话框 */
.feedback-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.feedback-dialog {
  background: #fff;
  border-radius: 14px;
  padding: 22px 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feedback-title {
  font-size: 16px;
  font-weight: 600;
  color: #2F2B3D;
}

.feedback-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #A8AAAE;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;

  &:hover {
    background: #f1f5f9;
    color: #64748b;
  }
}

.feedback-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedback-label {
  font-size: 13px;
  color: #4B465C;
  font-weight: 500;

  .required {
    color: #ef4444;
  }
}

.feedback-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-tag {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #64748b;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(37, 99, 235, 0.4);
    color: #2563eb;
  }

  &.active {
    background: rgba(37, 99, 235, 0.12);
    border-color: #2563eb;
    color: #2563eb;
    font-weight: 500;
  }
}

.feedback-input {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: #2F2B3D;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }
}

.feedback-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.card-btn.confirm {
  background: #2563eb;
  color: #fff;
  padding: 7px 18px;
  font-size: 12px;
  font-weight: 500;

  &:hover:not(:disabled) {
    background: #1d4ed8;
  }

  &:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
}
</style>
