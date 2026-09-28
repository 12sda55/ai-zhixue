<template>
  <Teleport to="body">
    <Transition name="guide-fade">
      <div v-if="mounted && visible" class="welcome-overlay" @click.self="handleSkip">
        <Transition name="guide-scale" appear>
          <div v-if="visible" class="welcome-card">
            <!-- 顶部装饰 -->
            <div class="welcome-decoration">
              <div class="deco-circle deco-circle-1"></div>
              <div class="deco-circle deco-circle-2"></div>
              <div class="deco-circle deco-circle-3"></div>
            </div>

            <!-- 标题区域 -->
            <div class="welcome-header">
              <div class="welcome-icon">
                <svg width="48" height="48" viewBox="0 0 48 48">
                  <defs>
                    <linearGradient id="guideGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
                      <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:1" />
                    </linearGradient>
                  </defs>
                  <circle cx="24" cy="24" r="22" fill="url(#guideGrad)" />
                  <text x="24" y="30" text-anchor="middle" fill="#fff" font-size="16" font-weight="700">AI</text>
                </svg>
              </div>
              <h2 class="welcome-title">欢迎使用 AI 学习系统</h2>
              <p class="welcome-subtitle">7 个 AI 驱动的功能，加速你的学习之旅 ✨</p>
            </div>

            <!-- 功能卡片网格 -->
            <div class="features-grid">
              <div
                v-for="feature in features"
                :key="feature.key"
                class="feature-card"
                :style="{ '--accent': feature.color, '--accent-glow': feature.glow }"
              >
                <div class="feature-accent-bar"></div>
                <div class="feature-icon">
                  <SvgIcon :name="feature.icon" :size="22" />
                </div>
                <div class="feature-info">
                  <div class="feature-name">{{ feature.name }}</div>
                  <div class="feature-desc">{{ feature.desc }}</div>
                </div>
              </div>
            </div>

            <!-- 底部按钮 -->
            <div class="welcome-footer">
              <button class="btn-start" @click="handleStartTour">
                <span>🚀</span>
                <span>开始互动导览</span>
              </button>
              <button class="btn-skip" @click="handleSkip">
                我自己探索
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SvgIcon from './SvgIcon.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  start: []
  skip: []
}>()

const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})

const features = [
  { key: 'home', icon: 'home', name: '首页', desc: '仪表盘总览，学习进度一目了然', color: '#2563eb', glow: 'rgba(37, 99, 235, 0.15)' },
  { key: 'profile', icon: 'profile', name: '画像', desc: 'AI 对话构建你的 8 维学习画像', color: '#6366f1', glow: 'rgba(99, 102, 241, 0.15)' },
  { key: 'agent', icon: 'robot', name: '智能体', desc: '7 个 AI 智能体协同为你工作', color: '#06b6d4', glow: 'rgba(6, 182, 212, 0.15)' },
  { key: 'resource', icon: 'book', name: '资源', desc: '个性化推荐视频/文档/代码/思维导图', color: '#10b981', glow: 'rgba(16, 185, 129, 0.15)' },
  { key: 'path', icon: 'path', name: '路径', desc: 'AI 生成专属学习路径，按阶段推进', color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.15)' },
  { key: 'qa', icon: 'chat', name: '答疑', desc: '随时向 AI 提问，即时解答疑惑', color: '#ec4899', glow: 'rgba(236, 72, 153, 0.15)' },
  { key: 'assess', icon: 'assess', name: '评估', desc: '自适应测评，精准定位薄弱点', color: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.15)' },
]

function handleStartTour() {
  emit('start')
}

function handleSkip() {
  emit('skip')
}
</script>

<style lang="less" scoped>
.welcome-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.welcome-card {
  position: relative;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 20px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), 0 4px 16px rgba(37, 99, 235, 0.06);
  padding: 40px;
  max-width: 720px;
  width: 100%;
  overflow: hidden;
}

// 顶部装饰圆
.welcome-decoration {
  position: absolute;
  top: 0;
  right: 0;
  width: 200px;
  height: 200px;
  pointer-events: none;

  .deco-circle {
    position: absolute;
    border-radius: 50%;
  }

  .deco-circle-1 {
    width: 180px;
    height: 180px;
    top: -60px;
    right: -40px;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.06));
  }

  .deco-circle-2 {
    width: 100px;
    height: 100px;
    top: -20px;
    right: 20px;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.05), rgba(6, 182, 212, 0.04));
  }

  .deco-circle-3 {
    width: 60px;
    height: 60px;
    top: 30px;
    right: 80px;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.04), rgba(6, 182, 212, 0.03));
  }
}

// 标题
.welcome-header {
  text-align: center;
  margin-bottom: 32px;
  position: relative;
}

.welcome-icon {
  margin-bottom: 16px;
  display: inline-block;
}

.welcome-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.welcome-subtitle {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

// 功能卡片网格
.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 32px;
  position: relative;
}

.feature-card {
  position: relative;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 12px;
  padding: 16px 14px;
  text-align: center;
  transition: all 0.2s ease;
  overflow: hidden;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px var(--accent-glow);
    border-color: var(--accent);
  }
}

.feature-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent);
  border-radius: 3px 3px 0 0;
}

.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--accent-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
  color: var(--accent);
  transition: all 0.2s ease;

  .feature-card:hover & {
    transform: scale(1.1);
  }
}

.feature-info {
  position: relative;
}

.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 4px;
}

.feature-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

// 底部按钮
.welcome-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  position: relative;
}

.btn-start {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.3);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
  }

  &:active {
    transform: translateY(0);
  }
}

.btn-skip {
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.55);
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.8);
    border-color: rgba(37, 99, 235, 0.25);
    color: #2563eb;
  }
}

// 过渡动画
.guide-fade-enter-active,
.guide-fade-leave-active {
  transition: opacity 0.3s ease;
}

.guide-fade-enter-from,
.guide-fade-leave-to {
  opacity: 0;
}

.guide-scale-enter-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.guide-scale-leave-active {
  transition: all 0.2s ease;
}

.guide-scale-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(12px);
}

.guide-scale-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
}

// 响应式
@media (max-width: 768px) {
  .welcome-card {
    padding: 28px 20px;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .welcome-title {
    font-size: 20px;
  }
}

@media (max-width: 576px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .feature-card {
    padding: 12px 10px;
  }

  .welcome-footer {
    flex-direction: column;
  }

  .btn-start,
  .btn-skip {
    width: 100%;
    justify-content: center;
  }
}
</style>
