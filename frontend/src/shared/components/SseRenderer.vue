<template>
  <div class="sse-renderer">
    <MarkdownRenderer :content="displayContent" />
    <span v-if="isStreaming" class="blink-cursor">█</span>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import MarkdownRenderer from './MarkdownRenderer.vue'

const props = defineProps<{
  content: string
  isStreaming: boolean
}>()

const displayContent = ref(props.content)

watch(() => props.content, (val) => {
  displayContent.value = val
})
</script>

<style lang="less" scoped>
.sse-renderer {
  width: 100%;
}

.blink-cursor {
  animation: blink 1s infinite;
  color: #00d4ff;
  font-weight: bold;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>