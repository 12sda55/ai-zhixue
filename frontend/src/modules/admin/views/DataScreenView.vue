<template>
  <div class="data-screen" ref="screenRef">
    <!-- 背景网格 -->
    <div class="screen-grid-bg"></div>

    <!-- HEADER -->
    <div class="screen-header">
      <div class="header-left">
        <span class="header-icon"><SvgIcon name="satellite" size="22" /></span>
        <div class="header-title-group">
          <span class="header-title">系统运行全景</span>
          <span class="header-sub">AI 多智能体个性化学习系统 · 实时数据看板</span>
        </div>
      </div>
      <div class="header-right">
        <span class="header-time">{{ currentTime }}</span>
        <button class="exit-btn" @click="exitScreen"><SvgIcon name="close" size="14" /> 退出大屏</button>
      </div>
    </div>

    <!-- 主网格 -->
    <div class="screen-grid">
      <!-- 左列：核心指标 + 知识点热力图 -->
      <div class="screen-col left-col">
        <!-- 核心指标卡片 -->
        <div class="screen-card metrics-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">核心指标</span>
          </div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ animatedStats.totalUsers }}</div>
              <div class="metric-label">用户总数</div>
              <div class="metric-bar" :style="{ '--bar-color': '#00d4ff', '--bar-pct': barPct(stats.total_users, 100) }"></div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ animatedStats.activeAgents }}<span class="metric-unit">/{{ animatedStats.totalAgents }}</span></div>
              <div class="metric-label">活跃Agent</div>
              <div class="metric-bar" :style="{ '--bar-color': '#10b981', '--bar-pct': barPct(animatedStats.activeAgents, Math.max(animatedStats.totalAgents, 1)) }"></div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ animatedStats.totalResources }}</div>
              <div class="metric-label">资源总量</div>
              <div class="metric-bar" :style="{ '--bar-color': '#2563eb', '--bar-pct': barPct(stats.total_resources, 100) }"></div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ animatedStats.profileCompletionRate }}<span class="metric-unit">%</span></div>
              <div class="metric-label">画像完成率</div>
              <div class="metric-bar" :style="{ '--bar-color': '#f59e0b', '--bar-pct': animatedStats.profileCompletionRate + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- 知识点掌握热力图 -->
        <div class="screen-card heatmap-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">知识点掌握热力图</span>
          </div>
          <div class="chart-body" ref="heatmapRef"></div>
        </div>
      </div>

      <!-- 中列：雷达图 + 资源趋势 -->
      <div class="screen-col center-col">
        <!-- 中央大雷达图 -->
        <div class="screen-card radar-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">8维画像雷达矩阵</span>
          </div>
          <div class="chart-body radar-body" ref="radarRef"></div>
        </div>

        <!-- 资源生成趋势 -->
        <div class="screen-card trend-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">资源生成趋势</span>
          </div>
          <div class="chart-body" ref="trendRef"></div>
        </div>
      </div>

      <!-- 右列：Agent流水线 + 维度分布 -->
      <div class="screen-col right-col">
        <!-- Agent 流水线 -->
        <div class="screen-card agent-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">Agent 流水线</span>
          </div>
          <div class="agent-pipeline">
            <div v-for="agent in (agentList || [])" :key="agent.agent_id || agent.id" class="agent-node" :class="agent?.status">
              <div class="agent-status-dot"></div>
              <div class="agent-name">{{ agent?.agent_name || agent?.name }}</div>
              <div v-if="agent?.status === 'running'" class="agent-flow-track">
                <div class="agent-flow-light"></div>
              </div>
              <div class="agent-progress-bar">
                <div class="agent-progress-fill" :style="{ width: (agent?.progress || 0) + '%', background: agent?.color || '#06b6d4' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 画像维度分布 -->
        <div class="screen-card dimension-card">
          <div class="card-title-bar">
            <span class="card-dot"></span>
            <span class="card-label">画像维度分布</span>
          </div>
          <div class="chart-body" ref="dimensionRef"></div>
        </div>
      </div>
    </div>

    <!-- 底部滚动文字 -->
    <div class="screen-footer">
      <div class="marquee-track">
        <div class="marquee-content" ref="marqueeRef">
          <span v-for="(msg, idx) in footerMessages" :key="idx" class="marquee-item">
            <span class="msg-time">{{ msg.time }}</span>
            <span class="msg-dot">·</span>
            <span class="msg-text">{{ msg.text }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as echarts from 'echarts'
import * as adminApi from '../api/adminApi'

const router = useRouter()
const route = useRoute()

const screenRef = ref<HTMLElement>()
const heatmapRef = ref<HTMLElement>()
const radarRef = ref<HTMLElement>()
const trendRef = ref<HTMLElement>()
const dimensionRef = ref<HTMLElement>()

let heatmapChart: echarts.ECharts | null = null
let radarChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let dimensionChart: echarts.ECharts | null = null
let refreshTimer: number | null = null
let clockTimer: number | null = null

const currentTime = ref('')

// 分享模式
const isShareMode = computed(() => !!route.query.token)
const shareToken = computed(() => route.query.token as string)

function updateClock() {
  const now = new Date()
  currentTime.value = `${now.getFullYear()}/${String(now.getMonth()+1).padStart(2,'0')}/${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`
}

// ===== 核心指标 =====
const stats = reactive({
  total_users: 0,
  active_users: 0,
  total_profiles: 0,
  total_resources: 0,
  total_assessments: 0
})

const animatedStats = reactive({
  totalUsers: 0,
  activeAgents: 0,
  totalAgents: 0,
  totalResources: 0,
  profileCompletionRate: 0,
})

// 雷达矩阵数据
const radarData = reactive({
  current: [] as { name: string; value: number }[],
  target: [] as { name: string; value: number }[]
})

// 知识热力图数据
const heatmapData = ref<any[]>([])

// Agent列表
const agentList = ref<any[]>([])

// 底部滚动文字
const footerMessages = ref<{ time: string; text: string }[]>([])

// 获取数据
const fetchData = async () => {
  try {
    let res: any
    if (isShareMode.value && shareToken.value) {
      res = await adminApi.getDataScreenData(shareToken.value)
    } else {
      const [statsRes, trendRes, heatmapRes, radarRes, agentRes, messagesRes] = await Promise.all([
        adminApi.getAdminStats(),
        adminApi.getResourceTrend(7),
        adminApi.getKnowledgeHeatmap().catch(() => null),
        adminApi.getRadarMatrix().catch(() => null),
        adminApi.getAgentActivity(),
        adminApi.getSystemMessages().catch(() => null)
      ])

      res = {
        stats: statsRes,
        resource_trend: trendRes,
        knowledge_heatmap: heatmapRes,
        radar_matrix: radarRes,
        agent_stats: agentRes,
        system_messages: messagesRes
      }

      if (statsRes) Object.assign(stats, statsRes)
      if (agentRes) agentList.value = agentRes
    }

    if (res) {
      if (res.stats) Object.assign(stats, res.stats)
      if (res.radar_matrix) {
        radarData.current = res.radar_matrix.current || []
        radarData.target = res.radar_matrix.target || []
      }
      if (res.knowledge_heatmap) heatmapData.value = res.knowledge_heatmap
      if (res.agent_stats) agentList.value = res.agent_stats
      if (res.system_messages) footerMessages.value = res.system_messages
      if (res.resource_trend) {
        resourceTrendData.value = res.resource_trend
      }
    }

    // 如果没有系统消息，使用默认数据
    if (footerMessages.value.length === 0) {
      footerMessages.value = generateDefaultMessages()
    }

    animateStats()
  } catch (e) {
    console.error('获取数据失败', e)
    // 使用默认数据
    footerMessages.value = generateDefaultMessages()
  }
}

// 生成默认系统消息
function generateDefaultMessages() {
  const now = new Date()
  return [
    { time: formatTime(now), text: `系统运行正常，当前在线用户 ${stats.active_users} 人` },
    { time: formatTime(new Date(now.getTime() - 300000)), text: `画像Agent已完成 3 个用户的画像更新` },
    { time: formatTime(new Date(now.getTime() - 600000)), text: `资源库新增 5 个AI生成资源` },
    { time: formatTime(new Date(now.getTime() - 900000)), text: `学习路径Agent规划了 2 条新路径` },
    { time: formatTime(new Date(now.getTime() - 1200000)), text: `评估系统完成了 8 次自适应测评` },
  ]
}

function formatTime(date: Date): string {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

// 资源趋势数据
const resourceTrendData = ref<any[]>([])

function animateStats() {
  const targets = {
    totalUsers: stats.total_users,
    activeAgents: agentList.value.filter(a => a.status === 'running').length,
    totalAgents: agentList.value.length,
    totalResources: stats.total_resources,
    profileCompletionRate: stats.assessment_completion_rate || 0
  }
  const duration = 1200
  const start = performance.now()
  const from = { ...animatedStats }

  function step(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedStats.totalUsers = Math.round(from.totalUsers + (targets.totalUsers - from.totalUsers) * eased)
    animatedStats.activeAgents = Math.round(from.activeAgents + (targets.activeAgents - from.activeAgents) * eased)
    animatedStats.totalAgents = Math.round(from.totalAgents + (targets.totalAgents - from.totalAgents) * eased)
    animatedStats.totalResources = Math.round(from.totalResources + (targets.totalResources - from.totalResources) * eased)
    animatedStats.profileCompletionRate = Math.round(from.profileCompletionRate + (targets.profileCompletionRate - from.profileCompletionRate) * eased)
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

// 进度条百分比辅助函数
function barPct(value: number, max: number): string {
  return Math.min(Math.round((value / max) * 100), 100) + '%'
}

// ===== ECharts 渲染 =====
function renderHeatmap() {
  if (!heatmapRef.value) return
  if (!heatmapChart) heatmapChart = echarts.init(heatmapRef.value, 'dark')

  const knowledgeNames = ['数据结构', '算法设计', '操作系统', '计算机网络', '数据库', '编程语言', '软件工程', '人工智能']
  const levels = ['零基础', '入门了解', '基础掌握', '熟练运用', '深入精通']

  const data: number[][] = []
  for (let i = 0; i < knowledgeNames.length; i++) {
    for (let j = 0; j < levels.length; j++) {
      const heatmapItem = heatmapData.value.find(h => h.area === knowledgeNames[i])
      const levelItem = heatmapItem?.levels?.find((l: { level: number; value: number }) => l.level === j + 1)
      data.push([i, j, levelItem?.value ?? 0])
    }
  }

  heatmapChart.setOption({
    tooltip: { position: 'top', backgroundColor: 'rgba(10,14,39,0.9)', textStyle: { color: '#e8f4fd' } },
    grid: { top: 30, right: 10, bottom: 40, left: 80 },
    xAxis: { type: 'category', data: knowledgeNames, axisLabel: { color: '#5a7a8a', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(0,212,255,0.1)' } } },
    yAxis: { type: 'category', data: levels, axisLabel: { color: '#5a7a8a', fontSize: 10 }, axisLine: { lineStyle: { color: 'rgba(0,212,255,0.1)' } } },
    visualMap: { min: 0, max: 100, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#ef4444', '#f59e0b', '#f59e0b', '#10b981', '#0dd4cf'] }, textStyle: { color: '#5a7a8a', fontSize: 10 } },
    series: [{ type: 'heatmap', data, label: { show: true, color: '#e8f4fd', fontSize: 9 }, itemStyle: { borderColor: 'rgba(0,212,255,0.06)', borderWidth: 1 } }],
  })
}

function renderRadar() {
  if (!radarRef.value) return
  if (!radarChart) radarChart = echarts.init(radarRef.value, 'dark')

  const dims = radarData.current.length > 0 ? radarData.current : [
    { name: '编程能力', value: 65 },
    { name: '算法思维', value: 55 },
    { name: '系统设计', value: 50 },
    { name: '问题解决', value: 70 },
    { name: '团队协作', value: 60 },
    { name: '学习能力', value: 75 },
    { name: '创新意识', value: 45 },
    { name: '工程实践', value: 58 }
  ]
  const values = dims.map(d => d.value)
  const targets = radarData.target.length > 0 ? radarData.target.map(d => d.value) : dims.map(() => 80)

  radarChart.setOption({
    tooltip: { backgroundColor: 'rgba(10,14,39,0.9)', textStyle: { color: '#e8f4fd' } },
    legend: { data: ['当前画像', '目标水平'], bottom: 5, textStyle: { color: '#5a7a8a', fontSize: 11 } },
    radar: {
      indicator: dims.map(d => ({ name: d.name, max: 100 })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#7eb8d0', fontSize: 12 },
      splitLine: { lineStyle: { color: 'rgba(0,212,255,0.08)' } },
      splitArea: { areaStyle: { color: ['rgba(0,212,255,0.02)', 'rgba(0,212,255,0.04)', 'rgba(0,212,255,0.06)', 'rgba(0,212,255,0.08)'] } },
      axisLine: { lineStyle: { color: 'rgba(0,212,255,0.1)' } },
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: targets, name: '目标水平',
          lineStyle: { color: '#a78bfa', width: 1, type: 'dashed' },
          areaStyle: { color: 'rgba(167,139,250,0.06)' },
          itemStyle: { color: '#a78bfa' },
          symbol: 'circle', symbolSize: 4,
        },
        {
          value: values, name: '当前画像',
          lineStyle: { color: '#00d4ff', width: 2.5 },
          areaStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
              { offset: 0, color: 'rgba(0,212,255,0.35)' },
              { offset: 1, color: 'rgba(0,212,255,0.02)' },
            ]),
          },
          itemStyle: { color: '#00d4ff', borderWidth: 2, borderColor: '#fff' },
          symbol: 'circle', symbolSize: 7,
        },
      ],
      emphasis: { lineStyle: { width: 3 } },
    }],
    animationDuration: 800,
    animationEasing: 'cubicOut' as const,
  }, true)
}

function renderTrend() {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value, 'dark')

  // 如果有真实数据，使用真实数据
  const trendData = resourceTrendData.value
  const dates = trendData.length > 0
    ? trendData.map((d: any) => {
        const parts = (d.date || '').split('-')
        return `${parseInt(parts[1] || '0')}/${parseInt(parts[2] || '0')}`
      })
    : getLast7Days()

  const types = ['document', 'mindmap', 'exercise', 'code', 'video']
  const typeColors: Record<string, string> = { document: '#00d4ff', mindmap: '#10b981', exercise: '#f59e0b', code: '#2563eb', video: '#ef4444' }
  const typeLabels: Record<string, string> = { document: '文档', mindmap: '导图', exercise: '习题', code: '代码', video: '视频' }

  const series = types.map(t => ({
    name: typeLabels[t],
    type: 'line',
    stack: 'total',
    data: trendData.length > 0
      ? dates.map((_: any, i: number) => {
          const dayData = trendData[i]
          return dayData?.by_type?.[t] || 0
        })
      : dates.map(() => 0),
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    lineStyle: { width: 2 },
    itemStyle: { color: typeColors[t] },
    areaStyle: { color: typeColors[t] + '15' },
  }))

  trendChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(10,14,39,0.9)', textStyle: { color: '#e8f4fd' } },
    legend: { data: types.map(t => typeLabels[t]), bottom: 0, textStyle: { color: '#5a7a8a', fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
    grid: { top: 20, right: 15, bottom: 30, left: 30 },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: 'rgba(0,212,255,0.1)' } }, axisLabel: { color: '#5a7a8a', fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(0,212,255,0.06)' } }, axisLabel: { color: '#5a7a8a', fontSize: 10 } },
    series,
    animationDuration: 800,
    animationEasing: 'cubicOut' as const,
  })
}

function getLast7Days(): string[] {
  const days: string[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    days.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return days
}

function renderDimension() {
  if (!dimensionRef.value) return
  if (!dimensionChart) dimensionChart = echarts.init(dimensionRef.value, 'dark')

  const dims = radarData.current.length > 0 ? radarData.current : [
    { name: '编程能力', value: 65 },
    { name: '算法思维', value: 55 },
    { name: '系统设计', value: 50 },
    { name: '问题解决', value: 70 },
    { name: '团队协作', value: 60 },
    { name: '学习能力', value: 75 },
    { name: '创新意识', value: 45 },
    { name: '工程实践', value: 58 }
  ]
  const data = dims.map(d => ({
    name: d.name,
    value: d.value,
    itemStyle: { color: d.value >= 70 ? '#10b981' : d.value >= 40 ? '#00d4ff' : '#ef4444' },
  }))

  const completed = dims.filter(d => d.value > 0).length
  const incomplete = dims.length - completed

  dimensionChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(10,14,39,0.9)', textStyle: { color: '#e8f4fd' } },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        data,
        label: { color: '#7eb8d0', fontSize: 10, formatter: '{b}: {d}%' },
        labelLine: { lineStyle: { color: 'rgba(0,212,255,0.2)' } },
        itemStyle: { borderColor: 'rgba(0,212,255,0.06)', borderWidth: 1 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,212,255,0.3)' } },
      },
      {
        type: 'pie',
        radius: ['0%', '35%'],
        center: ['50%', '45%'],
        data: [
          { name: '已完成', value: completed, itemStyle: { color: '#00d4ff' } },
          { name: '待完善', value: incomplete, itemStyle: { color: 'rgba(0,212,255,0.15)' } },
        ],
        label: { show: true, position: 'center', formatter: `{d}%`, color: '#e8f4fd', fontSize: 18, fontWeight: 700 },
        emphasis: { disabled: true },
        silent: true,
      },
    ],
    animationDuration: 800,
    animationEasing: 'cubicOut' as const,
  })
}

// ===== 全屏 =====
function requestFullscreen() {
  if (screenRef.value) {
    screenRef.value.requestFullscreen?.() ||
    (screenRef.value as any).webkitRequestFullscreen?.() ||
    (screenRef.value as any).msRequestFullscreen?.()
  }
}

function exitScreen() {
  document.exitFullscreen?.() || (document as any).webkitExitFullscreen?.()
  router.push('/admin/dashboard')
}

// ===== 初始化 =====
function renderAll() {
  fetchData()
  renderHeatmap()
  renderRadar()
  renderTrend()
  renderDimension()
}

onMounted(async () => {
  updateClock()
  clockTimer = window.setInterval(updateClock, 1000)
  await fetchData()
  await nextTick()
  renderAll()
  requestFullscreen()
  refreshTimer = window.setInterval(renderAll, 30000)
  window.addEventListener('resize', () => {
    heatmapChart?.resize()
    radarChart?.resize()
    trendChart?.resize()
    dimensionChart?.resize()
  })
})

onUnmounted(() => {
  heatmapChart?.dispose()
  radarChart?.dispose()
  trendChart?.dispose()
  dimensionChart?.dispose()
  if (refreshTimer) clearInterval(refreshTimer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style lang="less" scoped>
.data-screen {
  position: fixed;
  inset: 0;
  background: #0a0e27;
  color: #e8f4fd;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.screen-grid-bg {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(0deg, rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

// ===== HEADER =====
.screen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: rgba(0,212,255,0.04);
  border-bottom: 1px solid rgba(0,212,255,0.08);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon { display: flex; align-items: center; justify-content: center; }

.header-title-group {
  display: flex;
  flex-direction: column;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: #00d4ff;
  letter-spacing: 2px;
}

.header-sub {
  font-size: 12px;
  color: #5a7a8a;
  margin-top: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-time {
  font-size: 13px;
  color: #7eb8d0;
  font-variant-numeric: tabular-nums;
}

.exit-btn {
  padding: 6px 14px;
  border-radius: 6px;
  background: rgba(234,84,85,0.1);
  border: 1px solid rgba(234,84,85,0.3);
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;

  &:hover { background: rgba(234,84,85,0.2); }
}

// ===== 主网格 =====
.screen-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1.5fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 14px;
  padding: 14px 24px;
  min-height: 0;
}

.screen-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

// ===== 卡片通用 =====
.screen-card {
  background: rgba(0,212,255,0.04);
  border: 1px solid rgba(0,212,255,0.08);
  border-radius: 10px;
  box-shadow: 0 0 15px rgba(0,212,255,0.06);
  backdrop-filter: blur(10px);
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.card-title-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(0,212,255,0.06);
}

.card-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00d4ff;
  box-shadow: 0 0 6px rgba(0,212,255,0.6);
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  color: #7eb8d0;
}

// ===== 核心指标 =====
.metrics-card {
  flex: 0.8;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 12px 14px;
}

.metric-item {
  padding: 10px 12px;
  background: rgba(0,212,255,0.03);
  border-radius: 8px;
  border: 1px solid rgba(0,212,255,0.06);
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #00d4ff;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.metric-unit {
  font-size: 14px;
  color: #5a7a8a;
  font-weight: 400;
}

.metric-label {
  font-size: 11px;
  color: #5a7a8a;
  margin-top: 4px;
}

.metric-bar {
  height: 3px;
  background: rgba(0,212,255,0.06);
  border-radius: 2px;
  margin-top: 6px;
  overflow: hidden;

  &::after {
    content: '';
    display: block;
    width: var(--bar-pct);
    height: 100%;
    background: var(--bar-color);
    border-radius: 2px;
    transition: width 1s ease;
  }
}

// ===== 图表区 =====
.chart-body {
  flex: 1;
  min-height: 0;
  padding: 0 6px;
}

.radar-body {
  flex: 1;
  min-height: 0;
}

// ===== Agent 流水线 =====
.agent-pipeline {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 14px;
  overflow-y: auto;
}

.agent-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(0,212,255,0.03);
  border-radius: 6px;
  border: 1px solid rgba(0,212,255,0.06);
  position: relative;

  &.completed { border-color: rgba(40,199,111,0.2); }
  &.running { border-color: rgba(0,212,255,0.2); }
}

.agent-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  flex-shrink: 0;

  .agent-node.completed & {
    background: #10b981;
    box-shadow: 0 0 6px rgba(40,199,111,0.6);
  }

  .agent-node.running & {
    background: #00d4ff;
    box-shadow: 0 0 6px rgba(0,212,255,0.6);
    animation: pulse-glow 1.5s ease-in-out infinite;
  }
}

.agent-icon { flex-shrink: 0; display: flex; align-items: center; justify-content: center; }

.agent-name {
  font-size: 12px;
  font-weight: 600;
  color: #e8f4fd;
  flex: 1;
  white-space: nowrap;
}

.agent-flow-track {
  position: absolute;
  left: 24px;
  right: 10px;
  top: 50%;
  height: 2px;
  background: rgba(0,212,255,0.06);
  border-radius: 1px;
  overflow: hidden;
  transform: translateY(-50%);
  z-index: 0;
}

.agent-flow-light {
  width: 30px;
  height: 100%;
  background: linear-gradient(90deg, transparent, #00d4ff, transparent);
  border-radius: 1px;
  animation: flow-light 2s linear infinite;
}

.agent-progress-bar {
  width: 40px;
  height: 3px;
  background: rgba(0,212,255,0.06);
  border-radius: 2px;
  overflow: hidden;
  flex-shrink: 0;
}

.agent-progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

// ===== 底部滚动 =====
.screen-footer {
  flex-shrink: 0;
  padding: 10px 24px;
  background: rgba(0,212,255,0.04);
  border-top: 1px solid rgba(0,212,255,0.08);
  overflow: hidden;
}

.marquee-track {
  overflow: hidden;
  white-space: nowrap;
}

.marquee-content {
  display: inline-flex;
  gap: 40px;
  animation: marquee 30s linear infinite;
}

.marquee-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #7eb8d0;
}

.msg-time { color: #5a7a8a; }
.msg-dot { color: rgba(0,212,255,0.3); }
.msg-text { color: #7eb8d0; }

// ===== 动画 =====
@keyframes pulse-glow {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(0,212,255,0.6); }
  50% { opacity: 0.4; box-shadow: 0 0 2px rgba(0,212,255,0.3); }
}

@keyframes flow-light {
  0% { transform: translateX(-30px); }
  100% { transform: translateX(calc(100% + 30px)); }
}

@keyframes marquee {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
</style>