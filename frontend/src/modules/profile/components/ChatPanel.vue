<template>
  <div class="chat-panel">
    <!-- 对话头部 -->
    <div class="chat-header">
      <div class="header-left">
        <span class="header-icon">💬</span>
        <span class="header-title">画像对话</span>
      </div>
      <div class="header-right">
        <div v-if="phase === 'initial'" class="round-badge">
          第 {{ dialogueRound }}/4 轮
        </div>
        <div v-else class="phase-badge" :class="phase">
          {{ phase === 'stable' ? '画像生效中' : '补充模式' }}
        </div>
        <button class="reset-btn" @click="handleReset" title="重新构建画像">↻</button>
      </div>
    </div>

    <!-- 进度条 -->
    <div class="progress-bar">
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: completionRate + '%' }" />
      </div>
      <div class="progress-dots">
        <div
          v-for="i in 4"
          :key="i"
          class="progress-dot"
          :class="{
            completed: dialogueRound > i || (dialogueRound >= 4 && phase === 'stable'),
            active: dialogueRound === i && phase === 'initial',
          }"
        >{{ i }}</div>
      </div>
      <span class="progress-text">{{ completionRate }}%</span>
    </div>

    <!-- 消息区域 -->
    <div ref="messageListRef" class="message-list">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-item"
        :class="msg.role"
      >
        <div v-if="msg.role === 'assistant'" class="avatar ai-avatar">🤖</div>

        <div class="message-bubble" :class="msg.role">
          <!-- AI 消息渲染 -->
          <template v-if="msg.role === 'assistant'">
            <div v-if="msg.isStreaming && !msg.content" class="thinking">
              <span class="thinking-dot" /><span class="thinking-dot" /><span class="thinking-dot" />
            </div>
            <div v-else class="message-content">
              <div v-for="(seg, i) in parseContent(msg.content)" :key="i">
                <div v-if="seg.type === 'text'" class="text-seg" v-html="renderMarkdown(seg.content)" />
                <div v-else-if="seg.type === 'profile-update' && seg.items.length" class="profile-update-card">
                  <div class="update-card-header">📊 画像维度更新</div>
                  <div class="update-item" v-for="(item, j) in seg.items" :key="j">
                    <span class="update-dim-name">{{ getDimName(item.key) }}</span>
                    <span class="update-dim-arrow">→</span>
                    <span class="update-dim-value">{{ item.value }}</span>
                  </div>
                </div>
                <div v-else-if="seg.type === 'profile-summary' && seg.items.length" class="profile-summary-card">
                  <div class="summary-card-header">📋 画像总结</div>
                  <div class="summary-item" v-for="(item, j) in seg.items" :key="j">
                    <span class="summary-dim-icon">{{ getDimIcon(item.key) }}</span>
                    <span class="summary-dim-name">{{ getDimName(item.key) }}</span>
                    <span class="summary-dim-value">{{ item.value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 用户消息 -->
          <template v-else>
            <div class="message-content">{{ msg.content }}</div>
          </template>
        </div>

        <div v-if="msg.role === 'user'" class="avatar user-avatar">👤</div>
      </div>

      <!-- 流式输出中的光标 -->
      <div v-if="isStreaming" class="streaming-cursor">
        <span class="cursor-bar" />
      </div>
    </div>

    <!-- 快捷回复 -->
    <div v-if="needsConfirmation && !isStreaming" class="confirmation-section">
      <div class="confirm-prompt">所有维度已收集完毕，请确认画像生效：</div>
      <button class="confirm-btn" @click="confirmProfile">✓ 确认画像生效</button>
      <button class="modify-btn" @click="startModify">修改画像</button>
    </div>
    <div v-else-if="replies && replies.length > 0 && !isStreaming" class="quick-replies">
      <button
        v-for="(reply, i) in replies"
        :key="i"
        class="quick-reply-btn"
        @click="sendQuickReply(reply)"
      >{{ reply }}</button>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <input
        ref="inputRef"
        v-model="inputText"
        class="chat-input"
        :placeholder="inputPlaceholder"
        :disabled="isStreaming"
        @keydown.enter="handleSend"
      />
      <button class="send-btn" :disabled="isStreaming || !inputText.trim()" @click="handleSend">
        <span v-if="isStreaming" class="send-loader" />
        <span v-else>➤</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useProfileStore } from '../stores/profileStore'
import { DIMENSION_META } from '../../../shared/types'
import type { ProfileAllDimensionKey } from '../../../shared/types'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ breaks: true, linkify: true, html: false })

const purifyConfig = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'span', 'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4'],
  ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
  ALLOW_DATA_ATTR: false,
}

const store = useProfileStore()
const messages = computed(() => store.chatMessages)
const isStreaming = computed(() => store.isStreaming)
const completionRate = computed(() => store.completionRate)
const dialogueRound = computed(() => store.profileData.dialogueRound)
const phase = computed(() => store.profileData.phase)
const needsConfirmation = computed(() => store.needsConfirmation)
const replies = computed(() => store.quickReplies ?? [])

function getDimName(key: string): string {
  return DIMENSION_META[key as ProfileAllDimensionKey]?.name || key
}

function getDimIcon(key: string): string {
  return DIMENSION_META[key as ProfileAllDimensionKey]?.icon || '•'
}

const inputText = ref('')
const messageListRef = ref<HTMLElement>()

const inputPlaceholder = computed(() => {
  if (isStreaming.value) return 'AI 正在回复...'
  if (phase.value === 'initial') return `第 ${dialogueRound.value}/4 轮对话，请描述你的学习情况...`
  return '输入修改请求或补充信息...'
})

/* ===== 内容解析 ===== */

interface ContentSegment {
  type: 'text' | 'profile-update' | 'profile-summary'
  content: string
  items: { key: string; value: string }[]
}

function parseContent(raw: string): ContentSegment[] {
  const segments: ContentSegment[] = []
  if (!raw) return segments

  const profileUpdateRegex = /```profile-update\n([\s\S]*?)```/g
  const profileSummaryRegex = /```profile-summary\n([\s\S]*?)```/g

  let lastIdx = 0
  const codeBlocks: { start: number; end: number; type: string; content: string; items: { key: string; value: string }[] }[] = []

  // 收集 profile-update 代码块
  let match: RegExpExecArray | null
  while ((match = profileUpdateRegex.exec(raw)) !== null) {
    const items = parseKeyValuePairs(match[1])
    codeBlocks.push({ start: match.index, end: match.index + match[0].length, type: 'profile-update', content: match[0], items })
  }
  while ((match = profileSummaryRegex.exec(raw)) !== null) {
    const items = parseKeyValuePairs(match[1])
    codeBlocks.push({ start: match.index, end: match.index + match[0].length, type: 'profile-summary', content: match[0], items })
  }

  codeBlocks.sort((a, b) => a.start - b.start)

  for (const block of codeBlocks) {
    if (block.start > lastIdx) {
      segments.push({ type: 'text', content: raw.slice(lastIdx, block.start), items: [] })
    }
    segments.push({ type: block.type as any, content: block.content, items: block.items })
    lastIdx = block.end
  }

  if (lastIdx < raw.length) {
    segments.push({ type: 'text', content: raw.slice(lastIdx), items: [] })
  }

  return segments.length > 0 ? segments : [{ type: 'text', content: raw, items: [] }]
}

function parseKeyValuePairs(block: string): { key: string; value: string }[] {
  const result: { key: string; value: string }[] = []
  block.split('|').forEach(pair => {
    const [key, val] = pair.split(':')
    if (key?.trim() && val?.trim()) {
      result.push({ key: key.trim(), value: val.trim() })
    }
  })
  return result
}

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text), purifyConfig) as string
}

/* ===== 操作 ===== */

function handleSend() {
  if (!inputText.value.trim() || isStreaming.value) return
  store.sendMessage(inputText.value.trim())
  inputText.value = ''
}

function sendQuickReply(text: string) {
  if (isStreaming.value) return
  store.sendMessage(text)
}

function confirmProfile() {
  store.confirmProfile()
}

function startModify() {
  store.sendMessage('我想修改我的画像信息')
}

function handleReset() {
  if (isStreaming.value) return
  store.resetProfile()
}

/* ===== 自动滚动 ===== */

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

watch(messages, () => scrollToBottom(), { deep: true })
watch(isStreaming, () => scrollToBottom())

onMounted(() => {
  store.initDialogue()
  scrollToBottom()
})
</script>

<style lang="less" scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
  border-radius: 12px;
  overflow: hidden;
}

/* ===== 头部 ===== */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #F3F2F7;
  background: transparent;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon { font-size: 18px; }

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: #2F2B3D;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.round-badge {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(115, 103, 240, 0.12);
  color: #7367F0;
}

.phase-badge {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  &.stable { background: rgba(40, 199, 111, 0.12); color: #28C76F; }
  &.supplement { background: rgba(255, 159, 67, 0.12); color: #FF9F43; }
}

.reset-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid #EBE9F1;
  background: #F8F7FA;
  color: #6E6B7B;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #7367F0; color: #7367F0; background: rgba(115, 103, 240, 0.08); }
}

/* ===== 进度条 ===== */
.progress-bar {
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #F3F2F7;
  background: transparent;
}

.progress-track {
  flex: 1;
  height: 6px;
  background: #EBE9F1;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7367F0, #9E94FF);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-dots {
  display: flex;
  gap: 6px;
}

.progress-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid #EBE9F1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #A8AAAE;
  font-weight: 500;
  transition: all 0.3s;

  &.active {
    border-color: #7367F0;
    color: #7367F0;
    background: rgba(115, 103, 240, 0.1);
  }

  &.completed {
    border-color: #28C76F;
    background: rgba(40, 199, 111, 0.12);
    color: #28C76F;
  }
}

.progress-text {
  font-size: 12px;
  color: #6E6B7B;
  font-weight: 600;
  min-width: 30px;
  text-align: right;
}

/* ===== 消息区域 ===== */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #F8F7FA;

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: #D8D6DE; border-radius: 3px; }
}

.message-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;

  &.user { flex-direction: row-reverse; }
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.ai-avatar {
  background: linear-gradient(135deg, #7367F0, #9E94FF);
}

.user-avatar {
  background: linear-gradient(135deg, #00CFE8, #6FE4F0);
}

.message-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;

  &.assistant {
    background: transparent;
    border: 1px solid #EBE9F1;
    color: #5E5873;
    border-top-left-radius: 4px;
  }

  &.user {
    background: linear-gradient(135deg, #7367F0, #9E94FF);
    color: #FFFFFF;
    border-top-right-radius: 4px;
    font-weight: 500;
  }
}

.message-content {
  word-break: break-word;
}

.text-seg {
  :deep(p) { margin: 0 0 6px; }
  :deep(p:last-child) { margin: 0; }
  :deep(strong) { color: #7367F0; font-weight: 600; }
  :deep(code) { background: #F3F2F7; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #5E5873; }
}

/* ===== 画像更新卡片 ===== */
.profile-update-card {
  margin: 8px 0;
  padding: 10px 12px;
  background: rgba(0, 207, 232, 0.06);
  border: 1px solid rgba(0, 207, 232, 0.15);
  border-radius: 10px;
}

.update-card-header {
  font-size: 12px;
  font-weight: 600;
  color: #00CFE8;
  margin-bottom: 8px;
}

.update-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.update-dim-name { color: #6E6B7B; min-width: 60px; font-weight: 500; }
.update-dim-arrow { color: #A8AAAE; }
.update-dim-value { color: #2F2B3D; font-weight: 600; }

/* ===== 画像总结卡片 ===== */
.profile-summary-card {
  margin: 10px 0;
  padding: 12px;
  background: rgba(115, 103, 240, 0.06);
  border: 1px solid rgba(115, 103, 240, 0.15);
  border-radius: 10px;
}

.summary-card-header {
  font-size: 12px;
  font-weight: 600;
  color: #7367F0;
  margin-bottom: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.summary-dim-icon { font-size: 14px; }
.summary-dim-name { color: #6E6B7B; min-width: 60px; font-weight: 500; }
.summary-dim-value { color: #2F2B3D; font-weight: 600; }

/* ===== 思考动画 ===== */
.thinking {
  display: flex;
  gap: 6px;
  padding: 4px 0;
  align-items: center;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #7367F0;
  animation: thinking-pulse 1.2s infinite;

  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}

/* ===== 流式光标 ===== */
.streaming-cursor {
  padding: 4px 16px;
  display: flex;
  align-items: center;
}

.cursor-bar {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: #7367F0;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ===== 确认区域 ===== */
.confirmation-section {
  padding: 12px 16px;
  border-top: 1px solid #F3F2F7;
  background: transparent;
}

.confirm-prompt {
  font-size: 12px;
  color: #5E5873;
  margin-bottom: 8px;
  font-weight: 500;
}

.confirm-btn {
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid rgba(40, 199, 111, 0.3);
  background: rgba(40, 199, 111, 0.12);
  color: #28C76F;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  margin-right: 8px;
  transition: all 0.2s;

  &:hover { background: rgba(40, 199, 111, 0.2); }
}

.modify-btn {
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid #EBE9F1;
  background: #F8F7FA;
  color: #5E5873;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { background: #F3F2F7; color: #2F2B3D; }
}

/* ===== 快捷回复 ===== */
.quick-replies {
  padding: 10px 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  border-top: 1px solid #F3F2F7;
  background: transparent;
}

.quick-reply-btn {
  padding: 6px 12px;
  border-radius: 14px;
  border: 1px solid #EBE9F1;
  background: #F8F7FA;
  color: #5E5873;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    border-color: #7367F0;
    background: rgba(115, 103, 240, 0.08);
    color: #7367F0;
  }
}

/* ===== 输入区域 ===== */
.input-area {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #F3F2F7;
  background: transparent;
}

.chat-input {
  flex: 1;
  height: 40px;
  padding: 0 14px;
  border: 1px solid #EBE9F1;
  border-radius: 10px;
  background: #F8F7FA;
  color: #2F2B3D;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s, background 0.2s;

  &::placeholder { color: #A8AAAE; }
  &:focus { border-color: #7367F0; background: transparent; }
  &:disabled { opacity: 0.6; }
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #7367F0, #9E94FF);
  color: #FFFFFF;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(115, 103, 240, 0.3); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.send-loader {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
