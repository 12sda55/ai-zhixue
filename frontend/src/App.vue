<template>
  <router-view />
  <!-- UX-2: 全局悬浮AI助手 -->
  <FloatingAssistant />
</template>

<script setup lang="ts">
import { watch, onUnmounted, onMounted, onErrorCaptured } from 'vue'
import { useProfileStore } from './modules/profile/stores/profileStore'
import { usePathStore } from './modules/path/stores/pathStore'
import FloatingAssistant from './shared/components/FloatingAssistant.vue'

// 捕获子组件渲染错误，防止页面完全空白
onErrorCaptured((err, _instance, info) => {
  console.error('[App Error Captured]', err, '\nInfo:', info)
})

// 全局画像监听：确保在任何页面，画像变化都能触发路径生成/重新生成
const profileStore = useProfileStore()
const pathStore = usePathStore()

let oldProfileSnapshot: string = ''
let initTimer: ReturnType<typeof setTimeout> | null = null
let stopStatusWatch: (() => void) | null = null

// 路径生成完成时间（用于冷却机制）
let lastGenerationDoneTime = 0
const GENERATION_COOLDOWN_MS = 2000  // 生成完成后 2 秒内不再次触发

// 初始化快照
const initSnapshot = () => {
  try {
    oldProfileSnapshot = JSON.stringify(profileStore.profileData)

    // 如果画像有数据但没有路径，且当前不在生成中，且用户未主动清空，自动生成路径
    if (profileStore.hasProfile && !pathStore.hasPath && pathStore.generationStatus !== 'generating' && !pathStore.isPathCleared()) {
      pathStore.generatePath()
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  // 立即初始化快照
  try {
    oldProfileSnapshot = JSON.stringify(profileStore.profileData)
  } catch { /* ignore */ }

  // 监听路径生成状态，记录完成时间
  stopStatusWatch = watch(
    () => pathStore.generationStatus,
    (status) => {
      if (status === 'done') {
        lastGenerationDoneTime = Date.now()
        // 更新快照，避免后续触发
        try {
          oldProfileSnapshot = JSON.stringify(profileStore.profileData)
        } catch { /* ignore */ }
      }
    },
  )
  
  // 延迟检查是否需要生成路径（确保 profileStore 完成初始化）
  initTimer = setTimeout(() => {
    if (profileStore.hasProfile && !pathStore.hasPath && pathStore.generationStatus !== 'generating' && !pathStore.isPathCleared()) {
      pathStore.generatePath()
    }
  }, 100)
})

onUnmounted(() => {
  // 清理定时器
  if (initTimer) {
    clearTimeout(initTimer)
    initTimer = null
  }
  // 清理 watch
  if (stopStatusWatch) {
    stopStatusWatch()
    stopStatusWatch = null
  }
})
</script>