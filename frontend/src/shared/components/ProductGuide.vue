<template>
  <div class="product-guide">
    <!-- 欢迎弹窗阶段 -->
    <ProductGuideWelcome
      :visible="guideStore.visible && guideStore.phase === 'welcome'"
      @start="handleStartTour"
      @skip="handleSkip"
    />

    <!-- 聚光灯导览阶段 -->
    <ProductGuideSpotlight
      :visible="guideStore.visible && guideStore.phase === 'tour'"
      :current-step="guideStore.currentStep"
      :total-steps="guideStore.totalSteps"
      :step-config="guideStore.currentStepConfig"
      :is-first-step="guideStore.isFirstStep"
      :is-last-step="guideStore.isLastStep"
      @next="guideStore.nextStep()"
      @prev="guideStore.prevStep()"
      @skip="handleSkip"
      @finish="handleFinish"
    />
  </div>
</template>

<script setup lang="ts">
import { useProductGuideStore } from '../stores/productGuideStore'
import { useAppStore } from '../../stores/appStore'
import ProductGuideWelcome from './ProductGuideWelcome.vue'
import ProductGuideSpotlight from './ProductGuideSpotlight.vue'

const guideStore = useProductGuideStore()
const appStore = useAppStore()

// 记录导览开始前侧边栏状态
let wasSidebarCollapsed = false

function handleStartTour() {
  // 导览需要侧边栏展开以显示目标元素
  wasSidebarCollapsed = appStore.sidebarCollapsed
  if (appStore.sidebarCollapsed) {
    appStore.sidebarCollapsed = false
  }
  guideStore.startTour()
}

function handleSkip() {
  restoreSidebar()
  guideStore.skipGuide()
}

function handleFinish() {
  restoreSidebar()
  guideStore.completeGuide()
}

function restoreSidebar() {
  // 如果导览前侧边栏是折叠的，恢复折叠状态
  // 这里暂不恢复，因为用户刚学完导航，保持展开更好
  // wasSidebarCollapsed 只作为备用
}
</script>

<style lang="less" scoped>
.product-guide {
  // 容器不占空间，子组件使用 Teleport 渲染到 body
}
</style>
