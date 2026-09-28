<template>
  <div class="profile-view">
    <!-- 左侧：对话区域 -->
    <div class="chat-area">
      <!-- 对话头部 -->
      <div class="chat-header">
        <div class="header-avatar">🤖</div>
        <div class="header-info">
          <span class="header-name">AI 画像助手</span>
          <span class="header-status">
            <span class="status-dot" :class="profileData.phase"></span>
            {{ phaseLabel }}
          </span>
        </div>
        <div class="header-progress">
          <div class="progress-ring">
            <svg width="36" height="36" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(37, 99, 235, 0.15)" stroke-width="3"/>
              <circle cx="18" cy="18" r="14" fill="none" stroke="#06b6d4" stroke-width="3"
                stroke-linecap="round" :stroke-dasharray="`${(completionRate / 100) * 88} 88`"
                transform="rotate(-90 18 18)"/>
            </svg>
            <span class="progress-num">{{ completionRate }}%</span>
          </div>
        </div>
      </div>

      <!-- 对话消息区域 -->
      <div ref="messageAreaRef" class="message-area">
        <div v-for="msg in messages" :key="msg.id" class="message" :class="msg.role">
          <div v-if="msg.role === 'assistant'" class="msg-avatar">🤖</div>
          <div class="msg-content" :class="msg.role">
            <div class="msg-text" v-html="renderMarkdown(msg.content)"></div>
            <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">👤</div>
        </div>

        <!-- AI 正在输入提示 -->
        <div v-if="isStreaming" class="message assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content assistant typing">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 快捷回复 -->
      <div class="quick-reply-area">
        <button v-for="reply in quickReplies" :key="reply" class="quick-reply-btn" @click="sendQuickReply(reply)">
          {{ reply }}
        </button>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <input
          v-model="inputText"
          type="text"
          class="input-box"
          placeholder="告诉我你的情况，比如专业、年级、学习目标..."
          @keyup.enter="sendMessage"
          :disabled="isStreaming"
        />
        <button class="send-btn" :disabled="!inputText.trim() || isStreaming" @click="sendMessage">
          发送
        </button>
      </div>
    </div>

    <!-- 右侧：画像卡片 -->
    <div class="profile-area">
      <!-- 画像状态卡片 -->
      <div class="status-card" :class="profileData.phase">
        <div class="status-icon">
          <span v-if="completionRate < 100">🎯</span>
          <span v-else>✅</span>
        </div>
        <div class="status-text">
          <span class="status-title">{{ completionRate < 100 ? '画像构建中' : '画像已完成' }}</span>
          <span class="status-desc">{{ completionRate < 100 ? `已收集 ${completedDims}/${totalDims} 个维度` : '可以开始学习之旅了' }}</span>
        </div>
      </div>

      <!-- 科目选择器 -->
      <div v-if="profileData.subjectOverlays && profileData.subjectOverlays.length > 0" class="subject-card">
        <div class="subject-label">📖 当前科目</div>
        <div class="subject-tabs">
          <button
            v-for="overlay in profileData.subjectOverlays"
            :key="overlay.subject"
            class="subject-tab"
            :class="{ active: overlay.subject === profileData.currentSubject }"
            @click="switchSubject(overlay.subject)"
          >
            {{ overlay.subject }}
            <span class="tab-weak-count">{{ (overlay.weak_points || []).length }}项薄弱</span>
          </button>
        </div>
      </div>

      <!-- 雷达图 -->
      <div class="radar-card">
        <RadarChart :data="store.effectiveProfile" :isPerfect="store.isPerfectRadar" iconOnly />
      </div>

      <!-- 展馆入口：快照卡片横滑 -->
      <div v-if="profileData.snapshots && profileData.snapshots.length > 0" class="gallery-entry-card">
        <div class="gallery-entry-header">
          <span class="gallery-entry-title">🏛️ 展馆</span>
          <router-link to="/gallery" class="gallery-entry-link">查看全部 →</router-link>
        </div>
        <div class="snapshot-scroll">
          <div v-for="snap in profileData.snapshots.slice(0, 5)" :key="snap.id" class="snapshot-mini-card" :class="{ perfect: snap.isPerfect }">
            <div class="snap-tag">{{ snap.isPerfect ? '⭐ 完美' : '📸 手动' }}</div>
            <div class="snap-score">{{ snap.totalScore }}</div>
            <div class="snap-name">{{ snap.title }}</div>
            <div class="snap-growth">📈 +{{ snap.growthFromInitial }}</div>
          </div>
        </div>
      </div>

      <!-- 手动保存到展馆按钮 -->
      <div v-if="completionRate >= 100" class="action-card">
        <button class="save-gallery-btn" @click="handleSaveToGallery">
          📸 保存到展馆
        </button>
      </div>

      <!-- 已收集的维度 -->
      <div class="dims-card">
        <div class="dims-header">
          <span class="dims-title">已收集维度</span>
          <span class="dims-count">{{ completedDims }}/{{ totalDims }}</span>
        </div>
        <div class="dims-list">
          <div v-for="dim in profileData.dimensions" :key="dim.key" class="dim-item" :class="getDimItemClass(dim)">
            <span class="dim-icon">{{ dimIcon(dim.key) }}</span>
            <div class="dim-info">
              <span class="dim-name">{{ dim.name }}</span>
              <span v-if="dim.value > 0" class="dim-value">{{ getDimDisplayValue(dim.key as any) }}</span>
              <span v-else-if="isDynamicDim(dim.key)" class="dim-empty">自动计算</span>
              <span v-else class="dim-empty">待收集</span>
            </div>
            <div v-if="dim.showOnRadar !== false && !isDynamicDim(dim.key)" class="dim-score">
              <div class="score-bar" :style="{ width: dim.value + '%' }"></div>
            </div>
            <div v-else-if="dim.showOnRadar !== false && isDynamicDim(dim.key)" class="dim-score">
              <div class="score-bar dynamic-bar" :style="{ width: dim.value + '%' }"></div>
            </div>
            <span v-else-if="dim.value > 0" class="dim-radar-badge">已采集</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-card">
        <button v-if="completionRate >= 100 && profileData.phase !== 'stable'" class="confirm-btn" @click="confirmProfile">
          ✅ 确认画像生效
        </button>
        <button class="history-btn" @click="openHistorySelector">
          📚 选择历史画像
        </button>
        <button class="reset-btn" @click="resetProfile">
          🔄 重新构建
        </button>
      </div>
    </div>

    <!-- 画像历史选择弹窗 -->
    <div v-if="showHistorySelector" class="history-modal-overlay" @click.self="closeHistorySelector">
      <div class="history-modal">
        <div class="modal-header">
          <span class="modal-title">📚 选择历史画像</span>
          <button class="modal-close" @click="closeHistorySelector">×</button>
        </div>
        <div class="modal-body">
          <div v-if="isLoadingHistories" class="loading-state">
            <div class="loading-spinner"></div>
            <span>正在加载历史画像...</span>
          </div>
          <div v-else-if="profileHistories.length === 0" class="empty-state">
            <span class="empty-icon">📭</span>
            <span class="empty-text">暂无历史画像，请先构建并确认画像</span>
          </div>
          <div v-else class="history-list">
            <div v-for="history in profileHistories" :key="history.id" 
                 class="history-item" :class="{ active: history.is_active === 1 }">
              <div class="history-info">
                <span class="history-name">{{ history.name }}</span>
                <span class="history-meta">
                  {{ history.major }} · {{ history.grade }} · {{ history.base_level }}
                </span>
                <span v-if="history.weak_points_summary" class="history-weak">
                  薄弱点：{{ history.weak_points_summary }}
                </span>
                <span class="history-time">{{ formatHistoryTime(history.created_at) }}</span>
              </div>
              <div class="history-actions">
                <button v-if="history.is_active !== 1" class="use-btn" @click="useHistory(history.id)">
                  使用
                </button>
                <span v-else class="current-tag">当前</span>
                <button v-if="history.is_active !== 1" class="delete-btn" @click="deleteHistory(history.id)">
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, nextTick, watch } from 'vue'
import { useProfileStore } from '../stores/profileStore'
import { DIMENSION_META } from '../../../shared/types'
import type { ProfileAllDimensionKey } from '../../../shared/types'
import RadarChart from '../components/RadarChart.vue'

const store = useProfileStore()
const profileData = computed(() => store.profileData)
const messages = computed(() => store.chatMessages)
const isStreaming = computed(() => store.isStreaming)
const quickReplies = computed(() => store.quickReplies)

// 画像历史相关
const showHistorySelector = computed(() => store.showHistorySelector)
const profileHistories = computed(() => store.profileHistories)
const isLoadingHistories = computed(() => store.isLoadingHistories)

const inputText = ref('')
const messageAreaRef = ref<HTMLElement | null>(null)

const totalDims = computed(() => store.totalDims)
const completedDims = computed(() => store.completedDims)
const completionRate = computed(() => store.completionRate)
const phaseLabel = computed(() => {
  const p = profileData.value.phase
  return p === 'initial' ? '构建中' : p === 'supplement' ? '补充中' : '已生效'
})

function dimIcon(k: string) { return DIMENSION_META[k as ProfileAllDimensionKey]?.icon || '•' }

/** 判断是否为自动计算的动态维度 */
function isDynamicDim(key: string): boolean {
  return key === 'knowledge_mastery' || key === 'exercise_completion' || key === 'learning_engagement'
}

/** 维度项的 CSS class */
function getDimItemClass(dim: { key: string; value: number; showOnRadar?: boolean }): Record<string, boolean> {
  return {
    filled: dim.value > 0,
    'non-radar': dim.showOnRadar === false,
    'dynamic-dim': isDynamicDim(dim.key),
  }
}

function getDimDisplayValue(key: ProfileAllDimensionKey): string {
  if (key === 'weak_points') {
    return profileData.value.weak_points?.join('、') || '无明显薄弱'
  }
  if (key === 'knowledge_mastery') {
    return profileData.value.knowledge_mastery > 0 ? `${profileData.value.knowledge_mastery}%` : '待学习'
  }
  if (key === 'exercise_completion') {
    return profileData.value.exercise_completion > 0 ? `${profileData.value.exercise_completion}%` : '待练习'
  }
  if (key === 'learning_engagement') {
    return profileData.value.learning_engagement > 0 ? `${profileData.value.learning_engagement}%` : '待评估'
  }
  const data = profileData.value as any
  return data[key] || ''
}

function sendMessage() {
  if (!inputText.value.trim() || isStreaming.value) return
  store.sendMessage(inputText.value.trim())
  inputText.value = ''
  scrollToBottom()
}

function sendQuickReply(reply: string) {
  if (isStreaming.value) return
  store.sendMessage(reply)
  scrollToBottom()
}

// 画像历史相关方法
function openHistorySelector() {
  store.loadProfileHistories()
  store.showHistorySelector = true
}

function closeHistorySelector() {
  store.showHistorySelector = false
}

function switchSubject(subject: string) {
  store.switchSubject(subject)
}

async function useHistory(historyId: string) {
  await store.switchToHistory(historyId)
  // 强制刷新视图
  store.showHistorySelector = false
}

async function deleteHistory(historyId: string) {
  await store.deleteHistory(historyId)
}

function formatHistoryTime(time: string) {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function confirmProfile() {
  store.confirmProfile()
}

function handleSaveToGallery() {
  const title = `画像快照 · ${new Date().toLocaleDateString('zh-CN')}`
  store.saveSnapshot(title)
}

function resetProfile() {
  store.resetProfile()
}

function scrollToBottom() {
  nextTick(() => {
    if (messageAreaRef.value) {
      messageAreaRef.value.scrollTop = messageAreaRef.value.scrollHeight
    }
  })
}

function renderMarkdown(content: string): string {
  if (!content) return ''
  let html = content
  
  // 隐藏 profile-update 和 profile-summary 代码块（用于后端解析，不显示给用户）
  html = html.replace(/```profile-update\n[\s\S]*?```/g, '')
  html = html.replace(/```profile-summary\n[\s\S]*?```/g, '')
  
  // 其他代码块正常显示
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')
  // 列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
  // 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 清理多余空行
  html = html.replace(/\n{3,}/g, '\n\n')
  // 段落
  html = html.replace(/\n\n/g, '</p><p>')
  html = `<p>${html}</p>`
  return html
}

function formatTime(iso: string) {
  const d = new Date(iso), now = new Date()
  const dm = Math.floor((now.getTime() - d.getTime()) / 60000)
  if (dm < 1) return '刚刚'
  if (dm < 60) return `${dm}分钟前`
  const dh = Math.floor(dm / 60)
  if (dh < 24) return `${dh}小时前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// 监听消息变化，自动滚动到底部
watch(messages, () => scrollToBottom(), { deep: true })

// 监听画像加载状态，加载完成后再初始化对话
// 避免竞态条件：reloadProfileForUser 是异步的，如果 initDialogue 在加载完成前
// 调用，会看到 phase='initial' 的空画像，导致每次刷新都重新开始对话
watch(() => store.isLoadingProfile, (loading) => {
  if (!loading && messages.value.length === 0) {
    store.initDialogue()
    scrollToBottom()
  }
}, { immediate: true })

onMounted(() => {
  // 如果画像已加载完成且没有消息，初始化对话
  if (!store.isLoadingProfile && messages.value.length === 0) {
    store.initDialogue()
  }
  scrollToBottom()
})
</script>

<style lang="less" scoped>
.profile-view {
  height: 100%;
  display: flex;
  background: transparent;
  overflow: hidden;
}

/* ===== 左侧对话区域 ===== */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-right: 1px solid rgba(37, 99, 235, 0.1);
  min-width: 0;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  gap: 12px;
}

.header-avatar {
  width: 44px;
  height: 44px;
  background: transparent;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.header-info {
  flex: 1;
}

.header-name {
  font-size: 16px;
  font-weight: 700;
  color: #FFFFFF;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  margin-top: 2px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: transparent;
  animation: pulse 1.5s infinite;

  &.stable { background: #22c55e; }
  &.supplement { background: #f59e0b; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-progress {
  display: flex;
  align-items: center;
}

.progress-ring {
  position: relative;
  width: 36px;
  height: 36px;
}

.progress-num {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 9px;
  font-weight: 700;
  color: #FFFFFF;
}

/* ===== 消息区域 ===== */
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 3px; }
}

.message {
  display: flex;
  gap: 10px;
  max-width: 85%;

  &.user {
    flex-direction: row-reverse;
    align-self: flex-end;
  }

  &.assistant {
    align-self: flex-start;
  }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: transparent;
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;

  &.user-avatar {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
  }
}

.msg-content {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: 100%;

  &.assistant {
    background: transparent;
    backdrop-filter: blur(8px);
    border-bottom-left-radius: 4px;
    border: 1px solid rgba(37, 99, 235, 0.1);
  }

  &.user {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #FFFFFF;
    border-bottom-right-radius: 4px;
  }

  &.typing {
    padding: 16px;
  }
}

.msg-text {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  color: #1e293b;

  :deep(h2) { font-size: 16px; font-weight: 700; margin: 8px 0; color: #1e293b; }
  :deep(h3) { font-size: 14px; font-weight: 600; margin: 6px 0; color: #1e293b; }
  :deep(h4) { font-size: 13px; font-weight: 600; margin: 4px 0; color: #1e293b; }
  :deep(li) { margin: 4px 0 4px 16px; }
  :deep(.code-block) {
    background: #1e293b;
    padding: 12px;
    border-radius: 8px;
    margin: 8px 0;
    overflow-x: auto;
    code { color: #e2e8f0; font-family: monospace; font-size: 12px; }
  }
  :deep(.inline-code) {
    background: rgba(37, 99, 235, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    color: #2563eb;
  }
  :deep(strong) { font-weight: 600; }
}

.msg-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
  display: block;
}

.typing-indicator {
  display: flex;
  gap: 4px;

  span {
    width: 8px;
    height: 8px;
    background: #2563eb;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* ===== 快捷回复 ===== */
.quick-reply-area {
  display: flex;
  gap: 8px;
  padding: 8px 20px;
  overflow-x: auto;
  flex-shrink: 0;

  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 2px; }
}

.quick-reply-btn {
  padding: 8px 14px;
  background: transparent;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 20px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
    border-color: #2563eb;
    color: #2563eb;
  }
}

/* ===== 输入区域 ===== */
.input-area {
  display: flex;
  gap: 12px;
  padding: 12px 20px 16px;
  background: transparent;
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  flex-shrink: 0;
}

.input-box {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 24px;
  font-size: 14px;
  color: #1e293b;
  background: transparent;
  outline: none;
  transition: border-color 0.2s;

  &:focus {
    border-color: #2563eb;
  }

  &:disabled {
    background: transparent;
    color: #94a3b8;
  }

  &::placeholder {
    color: #94a3b8;
  }
}

.send-btn {
  padding: 12px 20px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border: none;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }

  &:disabled {
    background: #94a3b8;
    color: #FFFFFF;
    cursor: not-allowed;
  }
}

/* ===== 右侧画像区域 ===== */
.profile-area {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow-y: auto;

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 3px; }
}

/* ===== 状态卡片 ===== */
.status-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.1);

  &.initial {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.04));
    border: 1px solid rgba(37, 99, 235, 0.2);
  }

  &.stable {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(6, 182, 212, 0.04));
    border: 1px solid rgba(34, 197, 94, 0.2);
  }
}

.status-icon {
  width: 48px;
  height: 48px;
  background: transparent;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 2px 6px rgba(76, 78, 100, 0.06);
}

.status-text {
  flex: 1;
}

.status-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.status-desc {
  font-size: 12px;
  color: #475569;
  margin-top: 2px;
}

/* ===== 雷达图 ===== */
.subject-card {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 12px 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.subject-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}

.subject-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.subject-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    border-color: rgba(37, 99, 235, 0.3);
    background: rgba(37, 99, 235, 0.05);
  }

  &.active {
    background: rgba(37, 99, 235, 0.1);
    border-color: #2563eb;
    color: #2563eb;
    font-weight: 600;
  }
}

.tab-weak-count {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 400;
}

.subject-tab.active .tab-weak-count {
  color: rgba(37, 99, 235, 0.6);
}

.radar-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.1);
  min-height: 220px;
}

/* ===== 维度卡片 ===== */
.dims-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.dims-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.dims-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.dims-count {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
  padding: 2px 8px;
  border-radius: 6px;
}

.dims-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dim-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: transparent;
  border-radius: 8px;
  transition: all 0.2s;
  border: 1px solid rgba(37, 99, 235, 0.05);

  &.filled {
    background: rgba(34, 197, 94, 0.06);
    border-color: rgba(34, 197, 94, 0.15);
  }
}

.dim-icon {
  width: 28px;
  height: 28px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.dim-item.filled .dim-icon {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
}

.dim-info {
  flex: 1;
  min-width: 0;
}

.dim-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.dim-value {
  font-size: 11px;
  color: #22c55e;
  font-weight: 500;
  margin-top: 2px;
  display: block;
}

.dim-empty {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.dim-score {
  width: 60px;
  height: 6px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.score-bar {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border-radius: 3px;
  transition: width 0.4s;
}

.dim-radar-badge {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  font-weight: 500;
}

.dim-item.non-radar {
  background: rgba(148, 163, 184, 0.04);
  border-color: rgba(148, 163, 184, 0.1);

  &.filled {
    background: rgba(148, 163, 184, 0.06);
    border-color: rgba(148, 163, 184, 0.15);
  }

  .dim-icon {
    background: rgba(148, 163, 184, 0.15);
  }

  &.filled .dim-icon {
    background: linear-gradient(135deg, #94a3b8, #64748b);
  }
}

.dim-item.dynamic-dim {
  .dim-empty {
    color: #8b5cf6;
    font-style: italic;
  }

  .dynamic-bar {
    background: linear-gradient(90deg, #8b5cf6, #a78bfa) !important;
  }
}

/* ===== 操作按钮 ===== */
.action-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: transparent;
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.08);
}

/* ===== 展馆入口卡片 ===== */
.gallery-entry-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.gallery-entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.gallery-entry-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.gallery-entry-link {
  font-size: 12px;
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
}

.snapshot-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.snapshot-mini-card {
  min-width: 110px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.25);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(37,99,235,0.1);
  position: relative;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(37,99,235,0.1);
    border-color: #2563eb;
  }

  &.perfect {
    background: linear-gradient(135deg, rgba(245,158,11,0.06), rgba(255,255,255,0.15));
    border-color: rgba(245,158,11,0.2);
  }
}

.snap-tag {
  font-size: 9px;
  font-weight: 600;
  color: #2563eb;
  background: rgba(37,99,235,0.1);
  padding: 1px 5px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 4px;
  .perfect & {
    background: rgba(245,158,11,0.1);
    color: #f59e0b;
  }
}

.snap-score {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.snap-name {
  font-size: 10px;
  color: #475569;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.snap-growth {
  font-size: 9px;
  color: #10b981;
  margin-top: 2px;
  font-weight: 500;
}

/* ===== 保存到展馆按钮 ===== */
.save-gallery-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #FFFFFF;
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3);

  &:hover {
    box-shadow: 0 8px 24px rgba(245, 158, 11, 0.4);
    transform: translateY(-2px);
  }

  &:active {
    transform: scale(0.98);
  }
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;

  &:active {
    transform: scale(0.98);
  }
}

.confirm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;
  
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #FFFFFF;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.3);

  &:hover {
    box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
    transform: translateY(-2px);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }

  &:active {
    transform: scale(0.98);
  }
}

.reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;
  
  background: transparent;
  border: 1.5px solid rgba(37, 99, 235, 0.2);
  color: #475569;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
    border-color: #2563eb;
    color: #2563eb;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12);
  }

  &:active {
    transform: scale(0.98);
  }
}

.history-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  outline: none;
  
  background: transparent;
  border: 1.5px solid rgba(16, 185, 129, 0.2);
  color: #475569;

  &:hover {
    background: rgba(16, 185, 129, 0.06);
    border-color: #10b981;
    color: #10b981;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.12);
  }

  &:active {
    transform: scale(0.98);
  }
}

/* ===== 画像历史选择弹窗 ===== */
.history-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.history-modal {
  width: 480px;
  max-width: 90vw;
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 8px 32px rgba(76, 78, 100, 0.16);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #FFFFFF;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #FFFFFF;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
  }
}

.modal-body {
  padding: 20px;
  max-height: 400px;
  overflow-y: auto;

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 3px; }
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: #64748b;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
}

.empty-icon { font-size: 36px; opacity: 0.5; }
.empty-text { color: #94a3b8; font-size: 14px; }

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: #2563eb;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
  }

  &.active {
    background: rgba(37, 99, 235, 0.08);
    border-color: #2563eb;
  }
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.history-meta {
  font-size: 12px;
  color: #64748b;
}

.history-weak {
  font-size: 12px;
  color: #f59e0b;
}

.history-time {
  font-size: 11px;
  color: #94a3b8;
}

.history-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.use-btn {
  padding: 6px 12px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #FFFFFF;
  cursor: pointer;

  &:hover {
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
  }
}

.current-tag {
  padding: 6px 12px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #22c55e;
}

.delete-btn {
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #ef4444;
  cursor: pointer;

  &:hover {
    background: rgba(239, 68, 68, 0.2);
  }
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .profile-view {
    flex-direction: column;
  }

  .chat-area {
    flex: 1;
    border-right: none;
    border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  }

  .profile-area {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 12px;
    gap: 8px;

    .status-card, .radar-card, .dims-card, .action-card {
      flex: 1;
      min-width: 200px;
    }
  }
}
</style>