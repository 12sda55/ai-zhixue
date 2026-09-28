<template>
  <Teleport to="body">
    <Transition name="toast-fade">
      <div v-if="visible" class="perfect-toast-overlay" @click.self="handleClose">
        <div class="perfect-toast">
          <!-- 金色光晕脉冲 -->
          <div class="toast-glow"></div>

          <!-- 装饰粒子 -->
          <div class="toast-particles">
            <span v-for="i in 8" :key="i" class="particle" :style="particleStyle(i)"></span>
          </div>

          <!-- 内容 -->
          <div class="toast-content">
            <div class="toast-emoji">⭐ ✨ 🏆</div>
            <h2 class="toast-title">完美雷达图达成！</h2>
            <p class="toast-desc">8维全部 ≥ 90</p>

            <div class="toast-actions">
              <button class="btn-save" @click="handleSave">
                <span class="btn-icon">💾</span>
                保存画作
              </button>
              <button class="btn-close" @click="handleClose">
                关闭
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  save: []
  close: []
}>()

function handleSave() {
  emit('save')
}

function handleClose() {
  emit('close')
}

/** 粒子动画样式 */
function particleStyle(index: number) {
  const angle = (index - 1) * 45
  const delay = (index - 1) * 0.15
  return {
    '--angle': `${angle}deg`,
    '--delay': `${delay}s`,
  }
}
</script>

<style lang="less" scoped>
.perfect-toast-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(4px);
}

.perfect-toast {
  position: relative;
  width: 380px;
  max-width: 90vw;
  padding: 36px 32px 28px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(245, 158, 11, 0.25);
  box-shadow:
    0 4px 24px rgba(245, 158, 11, 0.12),
    0 1px 3px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  text-align: center;
  overflow: hidden;
}

/* ===== 金色光晕脉冲 ===== */
.toast-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200%;
  height: 200%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(245, 158, 11, 0.12) 0%,
    rgba(245, 158, 11, 0.04) 40%,
    transparent 70%
  );
  animation: glowPulse 2s ease-in-out infinite;
  pointer-events: none;
}

@keyframes glowPulse {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(0.9);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.1);
  }
}

/* ===== 装饰粒子 ===== */
.toast-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;

  .particle {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(245, 158, 11, 0.6);
    animation: particleFly 2s ease-in-out infinite;
    animation-delay: var(--delay);

    &::after {
      content: '✦';
      font-size: 10px;
      color: rgba(245, 158, 11, 0.8);
      position: absolute;
    }
  }
}

@keyframes particleFly {
  0% {
    transform: translate(-50%, -50%) rotate(var(--angle)) translateY(0);
    opacity: 0;
  }
  30% {
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) rotate(var(--angle)) translateY(-120px);
    opacity: 0;
  }
}

/* ===== 内容 ===== */
.toast-content {
  position: relative;
  z-index: 1;
}

.toast-emoji {
  font-size: 36px;
  margin-bottom: 12px;
  letter-spacing: 8px;
}

.toast-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 6px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.toast-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 24px;
}

/* ===== 按钮 ===== */
.toast-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.2s ease;

  .btn-icon {
    font-size: 15px;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }

  &:active {
    transform: translateY(0);
  }
}

.btn-close {
  padding: 10px 20px;
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.4);
  color: #475569;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.6);
    border-color: rgba(37, 99, 235, 0.25);
  }
}

/* ===== 过渡动画 ===== */
.toast-fade-enter-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.toast-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-fade-enter-from {
  opacity: 0;
  transform: scale(0.85);
}

.toast-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
