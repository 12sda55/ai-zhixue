import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, UserRole } from '../../../shared/types'
import { loginApi, registerApi, refreshTokenApi, resetPasswordApi, isAccountLocked } from '../api/authApi'
import { safeGetItem, safeGetJSON, safeSetItem, safeRemoveItem } from '../../../shared/utils/storage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(safeGetItem('token'))
  const user = ref<UserInfo | null>(safeGetJSON<UserInfo | null>('user', null))

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // 重置密码状态
  const resetPasswordStep = ref(1) // 1: 输入邮箱/用户名, 2: 输入验证码, 3: 设置新密码
  const resetPasswordTarget = ref('')
  const resetPasswordCooldown = ref(0)
  const resetPasswordError = ref('')

  async function login(username: string, password: string) {
    const res = await loginApi(username, password)
    token.value = res.token
    user.value = res.user
    safeSetItem('token', res.token)
    safeSetItem('user', JSON.stringify(res.user))
  }

  async function register(data: { username: string; password: string; email?: string; role: UserRole; inviteCode?: string }) {
    const res = await registerApi(data)
    token.value = res.token
    user.value = res.user
    safeSetItem('token', res.token)
    safeSetItem('user', JSON.stringify(res.user))
  }

  function logout() {
    token.value = null
    user.value = null
    safeRemoveItem('token')
    safeRemoveItem('user')
  }

  async function refreshToken() {
    if (!token.value) return
    try {
      const res = await refreshTokenApi(token.value)
      if (res.token && res.user.username) {
        token.value = res.token
        user.value = res.user
        safeSetItem('token', res.token)
        safeSetItem('user', JSON.stringify(res.user))
      }
    } catch {
      // 刷新失败，不处理
    }
  }

  async function resetPassword(newPassword: string) {
    if (!resetPasswordTarget.value) {
      resetPasswordError.value = '请输入用户名'
      return false
    }
    try {
      await resetPasswordApi(resetPasswordTarget.value, newPassword)
      resetPasswordError.value = ''
      return true
    } catch (err: any) {
      resetPasswordError.value = err.message || '重置密码失败'
      return false
    }
  }

  function startResetCooldown() {
    resetPasswordCooldown.value = 60
    const timer = setInterval(() => {
      resetPasswordCooldown.value--
      if (resetPasswordCooldown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  }

  function clearResetState() {
    resetPasswordStep.value = 1
    resetPasswordTarget.value = ''
    resetPasswordCooldown.value = 0
    resetPasswordError.value = ''
  }

  function checkAccountLocked(username: string) {
    return isAccountLocked(username)
  }

  function switchToAdmin() {
    window.location.href = '/admin/dashboard'
  }

  function switchToStudent() {
    window.location.href = '/'
  }

  // 检查并刷新即将过期的Token
  function checkTokenExpiry() {
    if (!token.value) return
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      const expiresAt = payload.exp * 1000
      const now = Date.now()
      // 小于1天时刷新
      if (expiresAt - now < 24 * 60 * 60 * 1000) {
        refreshToken()
      }
    } catch {
      // Token解析失败，不处理
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    resetPasswordStep,
    resetPasswordTarget,
    resetPasswordCooldown,
    resetPasswordError,
    login,
    register,
    logout,
    refreshToken,
    resetPassword,
    startResetCooldown,
    clearResetState,
    checkAccountLocked,
    switchToAdmin,
    switchToStudent,
    checkTokenExpiry,
  }
})