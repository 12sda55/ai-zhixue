import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { safeGetItem, safeSetItem } from '../shared/utils/storage'

export type ThemeMode = 'light' | 'dark'
const VALID_THEMES: ThemeMode[] = ['light', 'dark']

export const useAppStore = defineStore('app', () => {
  const courseName = ref('数据结构')
  const userName = ref('同学')

  const storedTheme = safeGetItem('theme')
  const theme = ref<ThemeMode>(VALID_THEMES.includes(storedTheme as ThemeMode) ? (storedTheme as ThemeMode) : 'light')

  const sidebarCollapsed = ref(false)

  // 粒子系统开关（默认开启）
  const particleEnabled = ref(safeGetItem('particleEnabled') !== 'false')

  let transitionTimer: ReturnType<typeof setTimeout> | null = null

  function setTheme(newTheme: ThemeMode) {
    theme.value = newTheme
    safeSetItem('theme', newTheme)
    applyTheme(newTheme)
  }

  function toggleTheme() {
    const newTheme = theme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }

  function applyTheme(mode: ThemeMode) {
    document.documentElement.setAttribute('data-theme', mode)
    document.body.classList.add('theme-transition')
    if (transitionTimer) clearTimeout(transitionTimer)
    transitionTimer = setTimeout(() => {
      document.body.classList.remove('theme-transition')
      transitionTimer = null
    }, 300)
  }

  watch(theme, (newTheme) => {
    applyTheme(newTheme)
  }, { immediate: true })

  // 粒子系统切换
  function toggleParticle() {
    particleEnabled.value = !particleEnabled.value
    safeSetItem('particleEnabled', String(particleEnabled.value))
  }

  return {
    courseName,
    userName,
    theme,
    sidebarCollapsed,
    particleEnabled,
    setTheme,
    toggleTheme,
    toggleParticle,
    applyTheme
  }
})