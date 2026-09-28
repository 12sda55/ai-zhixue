<template>
  <div class="qa-chat">
    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <span class="empty-icon">💬</span>
        <div class="empty-title">智能答疑</div>
        <div class="empty-desc">输入你的数据结构问题，AI 将根据你的画像提供个性化解答</div>
      </div>

      <div v-for="msg in messages" :key="msg.id" class="chat-msg" :class="msg.role">
        <div class="msg-avatar">{{ msg.role === 'user' ? '🧑' : '🤖' }}</div>
        <div class="msg-body">
          <div v-if="msg.role === 'assistant' && msg.isStreaming && !msg.content" class="thinking-dots">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </div>
          <div v-else-if="msg.role === 'assistant'" class="msg-content markdown-body" v-html="renderMarkdown(msg.content || '')" />
          <div v-else class="msg-content">{{ msg.content }}</div>
          <div v-if="msg.isStreaming && msg.content" class="streaming-cursor">▊</div>
          <div v-if="msg.source && !msg.isStreaming" class="msg-source" :class="msg.source?.includes('AI') ? 'ai' : 'kb'">
            {{ msg.source }}
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input">
      <input
        v-model="inputText"
        class="input-field"
        placeholder="输入你的数据结构问题..."
        :disabled="isGenerating"
        @keyup.enter="handleSend"
      />
      <button class="send-btn" :disabled="!inputText.trim() || isGenerating" @click="handleSend">
        {{ isGenerating ? '思考中...' : '发送' }}
      </button>
      <button v-if="isGenerating" class="stop-btn" @click="store.stopGenerating()">停止</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { useQaStore } from '../stores/qaStore'

const store = useQaStore()
const inputText = ref('')
const messagesRef = ref<HTMLElement | null>(null)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

const purifyConfig = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'span', 'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4'],
  ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
  ALLOW_DATA_ATTR: false,
}

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text), purifyConfig) as string
}

const messages = computed(() => store.messages)
const isGenerating = computed(() => store.isGenerating)

function handleSend() {
  if (!inputText.value.trim() || isGenerating.value) return
  store.sendMessage(inputText.value.trim())
  inputText.value = ''
}

watch(() => messages.value.length, async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
})

watch(isGenerating, async (val) => {
  if (val) {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  }
})
</script>

<style lang="less" scoped>
.qa-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
  border-radius: 12px;
  border: 1px solid #EBE9F1;
  box-shadow: 0 2px 12px rgba(76, 78, 100, 0.06);
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: transparent;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: #D8D6DE; border-radius: 2px; }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8px;
}

.empty-icon { font-size: 36px; }
.empty-title { font-size: 16px; font-weight: 600; color: #2F2B3D; }
.empty-desc { font-size: 13px; color: #6E6B7B; text-align: center; max-width: 280px; }

.chat-msg {
  display: flex;
  gap: 10px;
  max-width: 85%;

  &.user { align-self: flex-end; flex-direction: row-reverse; }
  &.assistant { align-self: flex-start; }
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.assistant .msg-avatar {
  background: linear-gradient(135deg, #00CFE8, #6FE4F0);
}

.user .msg-avatar {
  background: linear-gradient(135deg, #7367F0, #9E94FF);
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;

  .user & {
    background: linear-gradient(135deg, #7367F0, #9E94FF);
    color: #FFFFFF;
    border-bottom-right-radius: 4px;
    font-weight: 500;
  }

  .assistant & {
    background: transparent;
    color: #5E5873;
    border-bottom-left-radius: 4px;
    border: 1px solid #EBE9F1;
  }
}

.markdown-body {
  :deep(p) { margin: 4px 0; }
  :deep(pre) {
    background: transparent;
    border-radius: 8px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: 8px 0;
  }
  :deep(code) {
    font-family: 'Fira Code', monospace;
    font-size: 12px;
  }
  :deep(strong) { color: #7367F0; font-weight: 600; }
  :deep(blockquote) {
    border-left: 3px solid rgba(0, 207, 232, 0.3);
    padding-left: 10px;
    margin: 6px 0;
    color: #6E6B7B;
  }
  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 6px 0;
    th, td {
      border: 1px solid #EBE9F1;
      padding: 4px 8px;
      font-size: 12px;
    }
    th { background: rgba(0, 207, 232, 0.06); color: #00CFE8; }
  }
}

.streaming-cursor {
  display: inline-block;
  animation: blink 0.8s infinite;
  color: #00CFE8;
  font-size: 14px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.msg-source {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 4px;
  align-self: flex-end;

  &.ai { background: rgba(0, 207, 232, 0.08); color: #00CFE8; }
  &.kb { background: rgba(255, 159, 67, 0.08); color: #FF9F43; }
}

.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: transparent;
  border: 1px solid #EBE9F1;
  border-radius: 12px;
  border-bottom-left-radius: 4px;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #00CFE8;
    animation: dot-pulse 1.2s ease-in-out infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dot-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* ===== 输入区 ===== */
.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #EBE9F1;
  background: transparent;
}

.input-field {
  flex: 1;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #EBE9F1;
  background: transparent;
  color: #2F2B3D;
  font-size: 13px;
  outline: none;

  &::placeholder { color: #A8AAAE; }
  &:focus { border-color: #00CFE8; background: transparent; }
  &:disabled { opacity: 0.5; }
}

.send-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #00CFE8, #6FE4F0);
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(0, 207, 232, 0.3); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.stop-btn {
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid rgba(234, 84, 85, 0.3);
  background: rgba(234, 84, 85, 0.08);
  color: #EA5455;
  font-size: 13px;
  cursor: pointer;
  &:hover { background: rgba(234, 84, 85, 0.15); }
}
</style>
