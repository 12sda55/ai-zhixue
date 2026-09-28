<template>
  <div class="agent-log">
    <div class="log-header">
      <span class="log-title">运行日志</span>
      <button class="clear-btn" @click="$emit('clear')">清除</button>
    </div>
    <div class="log-content" ref="logRef">
      <div v-for="(log, i) in displayLogs" :key="i" class="log-line" :style="{ color: log.color }">
        {{ log.text }}
      </div>
      <div v-if="isRunning" class="log-line pulse-line">
        <span class="blink-cursor">█</span>
        <span class="wait-text">等待下一个事件...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { AGENT_LIST } from '../../../shared/utils/constants'

const props = defineProps<{
  logs: string[]
  isRunning?: boolean
}>()

defineEmits(['clear'])

const logRef = ref<HTMLElement>()

const displayLogs = computed(() => {
  return props.logs.map(text => {
    let color = '#6E6B7B'
    for (const agent of AGENT_LIST) {
      if (text.includes(agent.name)) {
        color = agent.color
        break
      }
    }
    if (text.includes('完成') || text.includes('✓')) color = '#28C76F'
    if (text.includes('启动') || text.includes('开始')) color = '#00CFE8'
    if (text.includes('错误') || text.includes('失败')) color = '#EA5455'
    return { text, color }
  })
})

watch(() => props.logs.length, () => {
  nextTick(() => {
    if (logRef.value) {
      logRef.value.scrollTop = logRef.value.scrollHeight
    }
  })
})
</script>

<style lang="less" scoped>
.agent-log {
  flex: 1;
  padding: 14px;
  overflow: auto;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.log-title {
  color: #2F2B3D;
  font-size: 13px;
  font-weight: 600;
}

.clear-btn {
  background: none;
  border: none;
  color: #A8AAAE;
  font-size: 11px;
  cursor: pointer;
  &:hover { color: #EA5455; }
}

.log-content {
  background: transparent;
  border-radius: 8px;
  padding: 10px;
  font-size: 11px;
  font-family: 'Cascadia Code', Consolas, monospace;
  border: 1px solid #EBE9F1;
  line-height: 1.8;
  overflow-y: auto;
  max-height: 100%;
}

.log-line {
  white-space: pre-wrap;
}

.pulse-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.blink-cursor {
  animation: blink 1s infinite;
  color: #00CFE8;
  font-weight: bold;
}

.wait-text {
  color: #A8AAAE;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
