<template>
  <div class="floating-assistant" :class="{ open: isOpen }">
    <!-- 浮动按钮 -->
    <button class="assistant-btn" @click="toggle" :title="isOpen ? '关闭助手' : 'AI 学习助手 (Ctrl+K)'">
      <span v-if="!isOpen" class="btn-icon">💬</span>
      <span v-else class="btn-icon">✕</span>
    </button>

    <!-- 对话面板 -->
    <transition name="panel-slide">
      <div v-if="isOpen" class="assistant-panel">
        <div class="panel-header">
          <span class="panel-title">AI 学习助手</span>
          <span v-if="contextTopic" class="panel-context">当前：{{ contextTopic }}</span>
          <button v-if="isSending" class="panel-stop" @click="stopGenerating">停止</button>
          <button class="panel-close" @click="close">✕</button>
        </div>

        <!-- 消息列表 -->
        <div class="panel-messages" ref="messagesRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="msg-item"
            :class="msg.role"
          >
            <span class="msg-avatar">{{ msg.role === 'user' ? '🧑' : '🤖' }}</span>
            <div class="msg-body">
              <div v-if="msg.isStreaming && !msg.content" class="thinking-dots">
                <span class="dot" /><span class="dot" /><span class="dot" />
              </div>
              <div
                v-else-if="msg.role === 'assistant'"
                class="msg-content"
                v-html="renderMarkdown(msg.content || '')"
              />
              <div v-else class="msg-content">{{ msg.content }}</div>
              <span v-if="msg.isStreaming && msg.content" class="streaming-cursor">▊</span>
            </div>
          </div>
        </div>

        <!-- 快捷提问 -->
        <div v-if="showQuickQuestions && messages.length <= 1" class="quick-questions">
          <button
            v-for="q in quickQuestions"
            :key="q"
            class="quick-btn"
            @click="sendQuick(q)"
          >{{ q }}</button>
        </div>

        <!-- 输入区 -->
        <div class="panel-input">
          <input
            v-model="inputText"
            class="input-field"
            placeholder="输入你的问题..."
            :disabled="isSending"
            @keyup.enter="handleSend"
          />
          <button
            class="send-btn"
            :disabled="!inputText.trim() || isSending"
            @click="handleSend"
          >发送</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { useAssistantStore } from '../stores/assistantStore'
import { useRoute } from 'vue-router'

const assistantStore = useAssistantStore()
const route = useRoute()

const inputText = ref('')
const messagesRef = ref<HTMLElement | null>(null)
const showQuickQuestions = ref(true)

const isOpen = computed(() => assistantStore.isOpen)
const messages = computed(() => assistantStore.messages)
const contextTopic = computed(() => assistantStore.contextTopic)
const quickQuestions = computed(() => assistantStore.quickQuestions)
const isSending = computed(() => assistantStore.isStreaming)

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
const purifyConfig = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'span', 'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
  ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
}

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text), purifyConfig) as string
}

function toggle() {
  assistantStore.toggle()
}

function close() {
  assistantStore.close()
}

function stopGenerating() {
  assistantStore.stopGenerating()
}

function sendQuick(question: string) {
  showQuickQuestions.value = false
  doSend(question)
}

function handleSend() {
  if (!inputText.value.trim() || isSending.value) return
  doSend(inputText.value.trim())
  inputText.value = ''
}

function doSend(text: string) {
  showQuickQuestions.value = false
  assistantStore.sendMessage(text, route.path)
}

// 监听路由变化，更新上下文
watch(() => route.path, (newPath) => {
  assistantStore.deriveContext(newPath)
}, { immediate: true })

// 自动滚动到底部
watch(() => messages.value.length, async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
})

// 快捷键 Ctrl+K 打开/关闭
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault()
    toggle()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.floating-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
}

.assistant-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.35);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.assistant-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(37, 99, 235, 0.5);
}

.assistant-panel {
  position: absolute;
  bottom: 64px;
  right: 0;
  width: 380px;
  max-height: 520px;
  background: #ffffff;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 16px;
  box-shadow: 0 12px 48px rgba(37, 99, 235, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.04), rgba(6, 182, 212, 0.04));
}

.panel-title {
  font-weight: 700;
  color: #0f172a;
  font-size: 15px;
}

.panel-context {
  font-size: 11px;
  color: #64748b;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-stop {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  cursor: pointer;
}

.panel-stop:hover {
  background: rgba(239, 68, 68, 0.15);
}

.panel-close {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 4px;
}

.panel-close:hover {
  color: #0f172a;
  background: rgba(37, 99, 235, 0.06);
}

.panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  max-height: 300px;
  background: #fafbfc;
}

.msg-item {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.msg-item.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  font-size: 20px;
  flex-shrink: 0;
}

.msg-body {
  max-width: 85%;
}

.msg-item.user .msg-body {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  padding: 8px 12px;
  border-radius: 12px 12px 4px 12px;
  font-size: 13px;
  line-height: 1.5;
}

.msg-item.assistant .msg-content {
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}

.msg-item.assistant .msg-content :deep(p) {
  margin: 4px 0;
}

.msg-item.assistant .msg-content :deep(strong) {
  color: #0f172a;
}

.msg-item.assistant .msg-content :deep(code) {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.msg-item.assistant .msg-content :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
  margin: 6px 0;
}

.msg-item.assistant .msg-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.msg-item.assistant .msg-content :deep(blockquote) {
  border-left: 3px solid #2563eb;
  margin: 6px 0;
  padding: 6px 12px;
  background: rgba(37, 99, 235, 0.04);
  color: #475569;
}

.streaming-cursor {
  animation: blink 0.6s infinite;
  color: #2563eb;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.dot {
  width: 6px;
  height: 6px;
  background: #2563eb;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.quick-questions {
  padding: 8px 12px;
  border-top: 1px solid rgba(37, 99, 235, 0.08);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  background: #fff;
}

.quick-btn {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.2);
  background: rgba(37, 99, 235, 0.04);
  color: #2563eb;
  cursor: pointer;
  transition: all 0.15s;
}

.quick-btn:hover {
  background: rgba(37, 99, 235, 0.1);
  border-color: rgba(37, 99, 235, 0.4);
}

.panel-input {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  border-top: 1px solid rgba(37, 99, 235, 0.08);
  background: #fff;
}

.input-field {
  flex: 1;
  background: #f8fafc;
  border: 1px solid rgba(37, 99, 235, 0.15);
  border-radius: 8px;
  padding: 8px 12px;
  color: #0f172a;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.input-field:focus {
  border-color: rgba(37, 99, 235, 0.4);
  background: #fff;
}

.input-field::placeholder {
  color: #94a3b8;
}

.send-btn {
  padding: 8px 14px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  font-weight: 500;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  opacity: 0.9;
}

/* 面板动画 */
.panel-slide-enter-active {
  transition: all 0.25s ease-out;
}

.panel-slide-leave-active {
  transition: all 0.15s ease-in;
}

.panel-slide-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}

.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

/* 滚动条 */
.panel-messages::-webkit-scrollbar {
  width: 4px;
}

.panel-messages::-webkit-scrollbar-thumb {
  background: rgba(37, 99, 235, 0.15);
  border-radius: 2px;
}
</style>
