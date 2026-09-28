<template>
  <div class="dashboard-view">
    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #2563eb, #3b82f6)">
          <UserOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_users }}</div>
          <div class="stat-label">用户总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #10b981, #34d399)">
          <CheckCircleOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.active_users }}</div>
          <div class="stat-label">活跃用户</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b, #fbbf24)">
          <BookOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_resources }}</div>
          <div class="stat-label">资源数量</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #06b6d4, #22d3ee)">
          <RobotOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.assessment_completion_rate }}%</div>
          <div class="stat-label">评估完成率</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="dashboard-grid">
      <!-- 用户增长趋势 -->
      <div class="dash-card">
        <div class="card-header">
          <span class="card-title"><LineChartOutlined /> 用户增长趋势</span>
          <a-select v-model:value="trendDays" size="small" style="width: 100px" @change="fetchUsersTrend">
            <a-select-option :value="7">近7天</a-select-option>
            <a-select-option :value="30">近30天</a-select-option>
          </a-select>
        </div>
        <div class="chart-body" ref="userTrendChartRef"></div>
      </div>

      <!-- 资源分布 -->
      <div class="dash-card">
        <div class="card-header">
          <span class="card-title"><PieChartOutlined /> 资源分布</span>
          <button class="refresh-btn" @click="fetchResourceDist"><ReloadOutlined /></button>
        </div>
        <div class="chart-body" ref="resourceChartRef"></div>
      </div>

      <!-- 最近注册用户 -->
      <div class="dash-card">
        <div class="card-header">
          <span class="card-title"><UserOutlined /> 最近注册用户</span>
          <router-link to="/admin/users" class="card-link">查看全部 →</router-link>
        </div>
        <div class="user-list">
          <div v-for="u in recentUsers" :key="u.id" class="user-row">
            <div class="user-avatar">{{ (u.username || 'U')[0].toUpperCase() }}</div>
            <div class="user-info">
              <span class="user-name">{{ u.username || '未知' }}</span>
              <span class="user-meta">{{ u.role === 'admin' ? '管理员' : '学生' }} · {{ formatDate(u.created_at) }}</span>
            </div>
            <a-tag :color="(u.status || 'active') === 'active' ? 'green' : 'orange'" size="small">
              {{ (u.status || 'active') === 'active' ? '正常' : '禁用' }}
            </a-tag>
          </div>
          <a-empty v-if="recentUsers.length === 0" description="暂无数据" />
        </div>
      </div>

      <!-- Agent 调用统计 -->
      <div class="dash-card">
        <div class="card-header">
          <span class="card-title"><RobotOutlined /> Agent 调用统计</span>
          <router-link to="/admin/agents" class="card-link">查看详情 →</router-link>
        </div>
        <div class="chart-body" ref="agentChartRef"></div>
      </div>

      <!-- 系统通知 -->
      <div class="dash-card notification-card">
        <div class="card-header">
          <span class="card-title">
            <BellOutlined /> 系统通知
            <a-badge v-if="unreadCount > 0" :count="unreadCount" :offset="[8, 0]" />
          </span>
          <a-button type="link" size="small" @click="markAllRead" :disabled="unreadCount === 0">全部已读</a-button>
        </div>
        <div class="notification-list">
          <div v-for="n in notifications" :key="n.id" class="notification-item" :class="{ unread: !n.is_read }" @click="handleNotificationClick(n)">
            <div class="notif-icon" :class="n.type">
              <CheckCircleOutlined v-if="n.type === 'success'" />
              <WarningOutlined v-else-if="n.type === 'warning'" />
              <InfoCircleOutlined v-else-if="n.type === 'info'" />
              <ExclamationCircleOutlined v-else />
            </div>
            <div class="notif-content">
              <div class="notif-title">{{ n.title }}</div>
              <div class="notif-desc">{{ n.content }}</div>
              <div class="notif-time">{{ formatDateTime(n.created_at) }}</div>
            </div>
          </div>
          <a-empty v-if="notifications.length === 0" description="暂无通知" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import {
  UserOutlined, RobotOutlined,
  LineChartOutlined, PieChartOutlined, ReloadOutlined,
  BookOutlined, CheckCircleOutlined, BellOutlined,
  WarningOutlined, InfoCircleOutlined, ExclamationCircleOutlined
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import * as adminApi from '../api/adminApi'
import type { AdminStatsData, UserTrendItem, ResourceDistributionItem, AgentActivityItem, AdminNotificationItem, AdminUserItem } from '../types'

// 统计数据
const stats = reactive<AdminStatsData>({
  total_users: 0,
  active_users: 0,
  total_profiles: 0,
  total_resources: 0,
  total_assessments: 0,
  assessment_completion_rate: 0
})

// 用户增长趋势
const trendDays = ref(7)
const userTrendData = ref<UserTrendItem[]>([])

// 资源分布
const resourceDistData = ref<ResourceDistributionItem[]>([])

// Agent活动
const agentActivityData = ref<AgentActivityItem[]>([])

// 最近用户
const recentUsers = ref<AdminUserItem[]>([])

// 通知
const notifications = ref<AdminNotificationItem[]>([])
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

// 图表引用
const userTrendChartRef = ref<HTMLElement>()
const resourceChartRef = ref<HTMLElement>()
const agentChartRef = ref<HTMLElement>()

let userTrendChart: echarts.ECharts | null = null
let resourceChart: echarts.ECharts | null = null
let agentChart: echarts.ECharts | null = null
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null

// 获取统计数据
const fetchStats = async () => {
  try {
    const res = await adminApi.getAdminStats()
    if (res) {
      Object.assign(stats, res)
    }
  } catch (e) {
    console.error('获取统计数据失败', e)
  }
}

// 获取用户增长趋势
const fetchUsersTrend = async () => {
  try {
    const res = await adminApi.getUsersTrend(trendDays.value)
    userTrendData.value = res || []
    renderUserTrendChart()
  } catch (e) {
    console.error('获取用户趋势失败', e)
  }
}

// 获取资源分布
const fetchResourceDist = async () => {
  try {
    const res = await adminApi.getResourceDistribution()
    resourceDistData.value = res || []
    renderResourceChart()
  } catch (e) {
    console.error('获取资源分布失败', e)
  }
}

// 获取Agent活动
const fetchAgentActivity = async () => {
  try {
    const res = await adminApi.getAgentActivity()
    agentActivityData.value = res || []
    renderAgentChart()
  } catch (e) {
    console.error('获取Agent活动失败', e)
  }
}

// 获取最近用户
const fetchRecentUsers = async () => {
  try {
    const res = await adminApi.getUserList({ page: 1, page_size: 5 })
    recentUsers.value = res?.items || []
  } catch (e) {
    console.error('获取最近用户失败', e)
  }
}

// 获取通知
const fetchNotifications = async () => {
  try {
    const res = await adminApi.getNotifications({ unread_only: false })
    notifications.value = (res || []).slice(0, 5)
  } catch (e) {
    console.error('获取通知失败', e)
  }
}

// 标记通知已读
const handleNotificationClick = async (n: AdminNotificationItem) => {
  if (!n.is_read) {
    try {
      await adminApi.markNotificationRead(n.id)
      n.is_read = true
    } catch (e) {
      console.error('标记已读失败', e)
    }
  }
}

// 全部标记已读
const markAllRead = async () => {
  try {
    const unread = notifications.value.filter(n => !n.is_read)
    await Promise.all(unread.map(n => adminApi.markNotificationRead(n.id)))
    notifications.value.forEach(n => n.is_read = true)
    message.success('已全部标记为已读')
  } catch (e) {
    console.error('批量标记已读失败', e)
    message.error('操作失败')
  }
}

// 渲染用户趋势图
const renderUserTrendChart = () => {
  if (!userTrendChartRef.value) return
  if (!userTrendChart) userTrendChart = echarts.init(userTrendChartRef.value)

  const trendData = userTrendData.value || []
  const dates = trendData.map(d => {
    const parts = (d.date || '').split('-')
    return `${parseInt(parts[1] || '0')}/${parseInt(parts[2] || '0')}`
  })
  const values = trendData.map(d => d.count || 0)

  userTrendChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: '#FFFFFF', textStyle: { color: '#0f172a' } },
    grid: { top: 20, right: 20, bottom: 30, left: 40 },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: 'rgba(37, 99, 235, 0.15)' } }, axisLabel: { color: '#475569', fontSize: 11 } },
    yAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(37, 99, 235, 0.06)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
    series: [{
      type: 'line', data: values, smooth: true, symbol: 'circle', symbolSize: 6,
      lineStyle: { color: '#2563eb', width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(37, 99, 235, 0.2)' }, { offset: 1, color: 'rgba(37, 99, 235, 0.02)' }]) },
      itemStyle: { color: '#2563eb' }
    }]
  })
}

// 渲染资源分布图
const renderResourceChart = () => {
  if (!resourceChartRef.value) return
  if (!resourceChart) resourceChart = echarts.init(resourceChartRef.value)

  const typeLabels: Record<string, string> = {
    document: '文档', mindmap: '导图', exercise: '习题', code: '代码', video: '视频'
  }
  const typeColors: Record<string, string> = {
    document: '#2563eb', mindmap: '#10b981', exercise: '#f59e0b', code: '#06b6d4', video: '#ef4444'
  }

  const data = (resourceDistData.value || []).filter(Boolean).map(d => ({
    name: typeLabels[d.type] || d.type,
    value: d.count || 0,
    itemStyle: { color: typeColors[d.type] || '#94a3b8' }
  }))

  resourceChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: '#FFFFFF', textStyle: { color: '#0f172a' } },
    series: [{
      type: 'pie', radius: ['30%', '65%'], center: ['50%', '50%'],
      data,
      label: { color: '#475569', fontSize: 11 },
      itemStyle: { borderColor: '#FFFFFF', borderWidth: 2 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(76,78,100,0.15)' } }
    }]
  })
}

// 渲染Agent图
const renderAgentChart = () => {
  if (!agentChartRef.value) return
  if (!agentChart) agentChart = echarts.init(agentChartRef.value)

  const names = (agentActivityData.value || []).filter(Boolean).map(a => a.agent_name || 'Unknown')
  const calls = (agentActivityData.value || []).filter(Boolean).map(a => a.call_count || 0)

  agentChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: '#FFFFFF', textStyle: { color: '#0f172a' } },
    grid: { top: 20, right: 20, bottom: 30, left: 80 },
    xAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(37, 99, 235, 0.06)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
    yAxis: { type: 'category', data: names, axisLine: { lineStyle: { color: 'rgba(37, 99, 235, 0.15)' } }, axisLabel: { color: '#0f172a', fontSize: 11 } },
    series: [{
      type: 'bar', data: calls.map(v => ({
        value: v,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#06b6d488' },
            { offset: 1, color: '#06b6d4' }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: 16
    }]
  })
}

// 日期格式化
const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

const formatDateTime = (date?: string) => {
  if (!date) return '-'
  const d = new Date(date)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  return d.toLocaleDateString('zh-CN')
}

// 窗口大小变化
let resizeHandler: () => void

onMounted(() => {
  fetchStats()
  fetchUsersTrend()
  fetchResourceDist()
  fetchAgentActivity()
  fetchRecentUsers()
  fetchNotifications()

  resizeHandler = () => {
    userTrendChart?.resize()
    resourceChart?.resize()
    agentChart?.resize()
  }
  window.addEventListener('resize', resizeHandler)

  // 30秒自动刷新
  autoRefreshTimer = setInterval(() => {
    fetchStats()
    fetchNotifications()
  }, 30000)
})

onUnmounted(() => {
  userTrendChart?.dispose()
  resourceChart?.dispose()
  agentChart?.dispose()
  window.removeEventListener('resize', resizeHandler)
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
})
</script>

<style lang="less" scoped>
.dashboard-view {
  padding: 0;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(37, 99, 235, 0.2);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
}

.stat-value {
  color: #0f172a;
  font-size: 24px;
  font-weight: 700;
}

.stat-label {
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  margin-top: 4px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.dash-card {
  padding: 20px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(37, 99, 235, 0.15);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.card-link {
  color: #2563eb;
  font-size: 12px;
  text-decoration: none;
  font-weight: 500;

  &:hover { text-decoration: underline; }
}

.refresh-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;

  &:hover { color: #2563eb; }
}

.chart-body {
  width: 100%;
  height: 220px;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: transparent;
  transition: background 0.2s;

  &:hover { background: rgba(37, 99, 235, 0.06); }
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-info { flex: 1; }
.user-name { color: #0f172a; font-size: 13px; font-weight: 600; }
.user-meta { color: #94a3b8; font-size: 11px; display: block; margin-top: 2px; }

@media (max-width: 1200px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
  .dashboard-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .stat-cards { grid-template-columns: 1fr; }
}

// 通知卡片
.notification-card {
  grid-column: span 2;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
  }

  &.unread {
    background: rgba(37, 99, 235, 0.04);
    border-left: 3px solid #2563eb;
  }
}

.notif-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;

  &.success { background: rgba(16, 185, 129, 0.12); color: #10b981; }
  &.warning { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
  &.info { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
  &.error { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
}

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 2px;
}

.notif-desc {
  font-size: 12px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

@media (max-width: 1200px) {
  .notification-card {
    grid-column: span 1;
  }
}
</style>
