<template>
  <div class="path-generator">
    <!-- 空状态：启动卡片 -->
    <div v-if="status === 'idle'" class="gen-idle">
      <div class="gen-icon-wrap">
        <span class="gen-icon">🗺️</span>
        <div class="gen-icon-ring" />
      </div>
      <div class="gen-title">生成你的专属学习路径</div>
      <div class="gen-desc">
        基于你的 8 维学习画像，AI 将为你规划一条循序渐进的数据结构学习路径
      </div>
      <button class="gen-start-btn" @click="$emit('generate')">
        <span class="btn-pulse" />
        开始生成
      </button>
    </div>

    <!-- 生成中：流式进度 -->
    <div v-else-if="status === 'generating'" class="gen-progress">
      <div class="gen-spinner">
        <svg width="64" height="64" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" fill="none" stroke="rgba(0,207,232,0.1)" stroke-width="3" />
          <circle
            cx="32" cy="32" r="28"
            fill="none"
            stroke="url(#gen-grad)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-dasharray="44 132"
            class="spin-ring"
          />
          <defs>
            <linearGradient id="gen-grad" x1="0" y1="0" x2="64" y2="64">
              <stop stop-color="#00CFE8" />
              <stop offset="1" stop-color="#7367F0" />
            </linearGradient>
          </defs>
        </svg>
        <span class="spin-icon">🤖</span>
      </div>

      <div class="gen-steps">
        <div
          v-for="(step, i) in genSteps"
          :key="i"
          class="gen-step"
          :class="{ active: currentStep === i, done: currentStep > i }"
        >
          <span class="step-dot">{{ currentStep > i ? '✓' : currentStep === i ? '●' : '○' }}</span>
          <span class="step-text">{{ step }}</span>
        </div>
      </div>

      <div class="gen-status">{{ progress }}</div>
      <button class="gen-cancel-btn" @click="$emit('cancel')">取消生成</button>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="status === 'error'" class="gen-error">
      <span class="err-icon">⚠️</span>
      <div class="err-title">生成失败</div>
      <div class="err-msg">{{ error }}</div>
      <button class="gen-start-btn" @click="$emit('generate')">重新生成</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PathGenerationStatus } from '../../../shared/types'

const props = defineProps<{
  status: PathGenerationStatus
  progress: string
  error?: string
}>()

defineEmits<{
  generate: []
  cancel: []
}>()

const genSteps = [
  '分析学习画像',
  '规划学习阶段',
  '匹配学习资源',
  '生成学习建议',
]

const currentStep = computed(() => {
  const p = props.progress
  if (p.includes('阶段')) return 1
  if (p.includes('资源')) return 2
  if (p.includes('建议')) return 3
  if (p.includes('输出') || p.includes('完成')) return 3
  return 0
})
</script>

<style lang="less" scoped>
.path-generator {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 32px;
}

/* ===== 空状态 ===== */
.gen-idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.gen-icon-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gen-icon {
  font-size: 32px;
  z-index: 1;
}

.gen-icon-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(0, 207, 232, 0.3);
  animation: ring-pulse 2s ease-in-out infinite;
}

@keyframes ring-pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.15); opacity: 0.6; }
}

.gen-title {
  font-size: 18px;
  font-weight: 700;
  color: #2F2B3D;
}

.gen-desc {
  font-size: 14px;
  color: #6E6B7B;
  text-align: center;
  max-width: 320px;
  line-height: 1.6;
}

.gen-start-btn {
  position: relative;
  padding: 10px 32px;
  border-radius: 10px;
  border: 1px solid rgba(0, 207, 232, 0.3);
  background: rgba(0, 207, 232, 0.08);
  color: #00CFE8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    background: rgba(0, 207, 232, 0.15);
    box-shadow: 0 0 20px rgba(0, 207, 232, 0.15);
  }
}

.btn-pulse {
  position: absolute;
  inset: -1px;
  border-radius: 10px;
  border: 1px solid rgba(0, 207, 232, 0.3);
  animation: btn-pulse 2s ease-in-out infinite;
}

@keyframes btn-pulse {
  0%, 100% { opacity: 0; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.04); }
}

/* ===== 生成中 ===== */
.gen-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.gen-spinner {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spin-ring {
  animation: spin 1.2s linear infinite;
  transform-origin: center;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spin-icon {
  position: absolute;
  font-size: 20px;
}

.gen-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 220px;
}

.gen-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #A8AAAE;
  transition: all 0.3s;

  &.active { color: #00CFE8; }
  &.done { color: #28C76F; }
}

.step-dot {
  width: 16px;
  text-align: center;
  font-size: 11px;
}

.gen-status {
  font-size: 13px;
  color: #6E6B7B;
  animation: fade-pulse 1.5s ease-in-out infinite;
}

@keyframes fade-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.gen-cancel-btn {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid #EBE9F1;
  background: transparent;
  color: #6E6B7B;
  font-size: 12px;
  cursor: pointer;

  &:hover { color: #2F2B3D; border-color: #D8D6DE; background: rgba(37, 99, 235, 0.08); }
}

/* ===== 错误 ===== */
.gen-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.err-icon { font-size: 32px; }
.err-title { font-size: 16px; font-weight: 600; color: #EA5455; }
.err-msg { font-size: 13px; color: #6E6B7B; max-width: 280px; text-align: center; }
</style>
