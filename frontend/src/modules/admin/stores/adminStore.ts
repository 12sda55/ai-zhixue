import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as adminApi from '../api/adminApi'
import type { AdminStatsData, AdminNotificationItem } from '../types'

export const useAdminStore = defineStore('admin', () => {
  // 统计数据
  const stats = ref<AdminStatsData>({
    total_users: 0,
    active_users: 0,
    total_profiles: 0,
    total_resources: 0,
    total_assessments: 0,
    assessment_completion_rate: 0,
  })
  const loading = ref(false)

  // 通知
  const notifications = ref<AdminNotificationItem[]>([])
  const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

  // 加载统计
  async function loadStats() {
    loading.value = true
    try {
      const res = await adminApi.getAdminStats()
      if (res) Object.assign(stats.value, res)
    } catch (e) {
      console.error('[AdminStore] 加载统计数据失败', e)
    } finally {
      loading.value = false
    }
  }

  // 加载通知
  async function loadNotifications(limit = 20) {
    try {
      const res = await adminApi.getNotifications({ unread_only: false, limit })
      notifications.value = res || []
    } catch (e) {
      console.error('[AdminStore] 加载通知失败', e)
    }
  }

  // 标记单条通知已读
  async function markNotificationRead(id: number) {
    try {
      await adminApi.markNotificationRead(id)
      const n = notifications.value.find(item => item.id === id)
      if (n) n.is_read = true
    } catch (e) {
      console.error('[AdminStore] 标记通知已读失败', e)
    }
  }

  // 标记全部已读
  async function markAllNotificationsRead() {
    const unread = notifications.value.filter(n => !n.is_read)
    await Promise.all(unread.map(n => adminApi.markNotificationRead(n.id)))
    notifications.value.forEach(n => { n.is_read = true })
  }

  return {
    stats,
    loading,
    notifications,
    unreadCount,
    loadStats,
    loadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
  }
})
