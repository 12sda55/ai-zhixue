<template>
  <Teleport to="body">
    <Transition name="spotlight-fade">
      <div v-if="mounted && visible" class="spotlight-overlay">
        <!-- 镂空聚光灯 -->
        <div
          class="spotlight-hole"
          :style="holeStyle"
        ></div>

        <!-- 浮动提示卡片 -->
        <Transition name="tooltip-slide" mode="out-in">
          <div
            v-if="stepConfig"
            :key="currentStep"
            class="spotlight-tooltip"
            :style="tooltipStyle"
          >
            <!-- 步骤指示器 -->
            <div class="tooltip-step-indicator">
              <div class="step-dots">
                <div
                  v-for="i in totalSteps"
                  :key="i"
                  class="step-dot"
                  :class="{
                    active: i - 1 === currentStep,
                    done: i - 1 < currentStep,
                  }"
                ></div>
              </div>
              <span class="step-text">{{ currentStep + 1 }} / {{ totalSteps }}</span>
            </div>

            <!-- 步骤内容 -->
            <div class="tooltip-content">
              <div class="tooltip-icon">
                <SvgIcon :name="stepConfig.icon" :size="20" />
              </div>
              <div class="tooltip-text">
                <h4 class="tooltip-title">{{ stepConfig.title }}</h4>
                <p class="tooltip-desc">{{ stepConfig.description }}</p>
              </div>
            </div>

            <!-- 导航按钮 -->
            <div class="tooltip-actions">
              <button
                v-if="!isFirstStep"
                class="btn-prev"
                @click="handlePrev"
              >
                ← 上一步
              </button>
              <div v-else></div>

              <div class="actions-right">
                <button class="btn-skip" @click="handleSkip">跳过导览</button>
                <button
                  v-if="!isLastStep"
                  class="btn-next"
                  @click="handleNext"
                >
                  下一步 →
                </button>
                <button
                  v-else
                  class="btn-finish"
                  @click="handleFinish"
                >
                  🚀 开始使用
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import SvgIcon from './SvgIcon.vue'
import type { TourStep } from '../stores/productGuideStore'

const props = defineProps<{
  visible: boolean
  currentStep: number
  totalSteps: number
  stepConfig: TourStep | undefined
  isFirstStep: boolean
  isLastStep: boolean
}>()

const emit = defineEmits<{
  next: []
  prev: []
  skip: []
  finish: []
}>()

const mounted = ref(false)
onMounted(() => {
  mounted.value = true
  window.addEventListener('resize', updatePosition)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updatePosition)
})

// ===== 聚光灯位置计算 =====
const holeRect = ref({ top: 0, left: 0, width: 0, height: 0 })
const tooltipPos = ref({ top: 0, left: 0 })

function getTargetEl(): HTMLElement | null {
  if (!props.stepConfig) return null
  return document.querySelector(`[data-guide="${props.stepConfig.target}"]`)
}

function updatePosition() {
  const el = getTargetEl()
  if (!el) return

  const rect = el.getBoundingClientRect()
  const padding = 6 // 镂空区域比目标稍大

  holeRect.value = {
    top: rect.top - padding,
    left: rect.left - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  }

  // 提示卡片定位：在目标元素右侧
  const tooltipWidth = 320
  const tooltipGap = 20
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight

  let left = rect.right + tooltipGap
  let top = rect.top

  // 如果右侧放不下，放到左侧
  if (left + tooltipWidth > viewportWidth - 24) {
    left = rect.left - tooltipWidth - tooltipGap
  }
  // 如果左侧也放不下（很窄的屏幕），放到下方
  if (left < 24) {
    left = rect.left
    top = rect.bottom + tooltipGap
  }

  // 确保不超出视口底部
  const estimatedTooltipHeight = 180
  if (top + estimatedTooltipHeight > viewportHeight - 24) {
    top = viewportHeight - estimatedTooltipHeight - 24
  }
  // 确保不超出视口顶部
  if (top < 24) {
    top = 24
  }

  tooltipPos.value = { top, left }
}

// 监听步骤变化更新位置
watch(() => props.currentStep, () => {
  nextTick(() => updatePosition())
})

watch(() => props.visible, (v) => {
  if (v) {
    nextTick(() => updatePosition())
  }
})

// ===== 样式计算 =====
const holeStyle = computed(() => ({
  top: `${holeRect.value.top}px`,
  left: `${holeRect.value.left}px`,
  width: `${holeRect.value.width}px`,
  height: `${holeRect.value.height}px`,
}))

const tooltipStyle = computed(() => ({
  top: `${tooltipPos.value.top}px`,
  left: `${tooltipPos.value.left}px`,
}))

// ===== 事件 =====
function handleNext() { emit('next') }
function handlePrev() { emit('prev') }
function handleSkip() { emit('skip') }
function handleFinish() { emit('finish') }
</script>

<style lang="less" scoped>
.spotlight-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  pointer-events: none;
}

// 镂空聚光灯 — 使用 box-shadow 实现遮罩
.spotlight-hole {
  position: absolute;
  border-radius: 10px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.45);
  transition: top 0.35s cubic-bezier(0.16, 1, 0.3, 1),
              left 0.35s cubic-bezier(0.16, 1, 0.3, 1),
              width 0.35s cubic-bezier(0.16, 1, 0.3, 1),
              height 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: auto;
  z-index: 1;

  // 镂空区域边框高亮
  &::after {
    content: '';
    position: absolute;
    inset: -2px;
    border-radius: 12px;
    border: 2px solid rgba(37, 99, 235, 0.4);
    pointer-events: none;
  }
}

// 浮动提示卡片
.spotlight-tooltip {
  position: absolute;
  width: 320px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 4px 16px rgba(37, 99, 235, 0.06);
  padding: 20px;
  pointer-events: auto;
  z-index: 2;
}

// 步骤指示器
.tooltip-step-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.step-dots {
  display: flex;
  gap: 5px;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.15);
  transition: all 0.2s ease;

  &.active {
    background: #2563eb;
    box-shadow: 0 0 8px rgba(37, 99, 235, 0.4);
    transform: scale(1.2);
  }

  &.done {
    background: rgba(37, 99, 235, 0.4);
  }
}

.step-text {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

// 步骤内容
.tooltip-content {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.tooltip-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  flex-shrink: 0;
}

.tooltip-text {
  flex: 1;
}

.tooltip-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 6px;
}

.tooltip-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  margin: 0;
}

// 导航按钮
.tooltip-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-prev {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.55);
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.8);
    color: #2563eb;
  }
}

.btn-next {
  padding: 7px 16px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);

  &:hover {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    transform: translateY(-1px);
  }
}

.btn-finish {
  padding: 7px 16px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #10b981, #34d399);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);

  &:hover {
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
    transform: translateY(-1px);
  }
}

.btn-skip {
  padding: 7px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    color: #475569;
    background: rgba(0, 0, 0, 0.04);
  }
}

// 过渡动画
.spotlight-fade-enter-active,
.spotlight-fade-leave-active {
  transition: opacity 0.3s ease;
}

.spotlight-fade-enter-from,
.spotlight-fade-leave-to {
  opacity: 0;
}

.tooltip-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.tooltip-slide-leave-active {
  transition: all 0.15s ease;
}

.tooltip-slide-enter-from {
  opacity: 0;
  transform: translateX(12px);
}

.tooltip-slide-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

// 响应式
@media (max-width: 768px) {
  .spotlight-tooltip {
    width: 280px;
    padding: 16px;
  }
}
</style>
