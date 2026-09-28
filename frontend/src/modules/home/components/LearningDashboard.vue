<template>
  <div class="learning-dashboard">
    <!-- 学习时长趋势 -->
    <div class="card">
      <div class="card-header">
        <div class="card-title-group">
          <span class="card-title">📈 学习时长趋势</span>
          <span class="card-subtitle">近7天每日学习时长</span>
        </div>
      </div>
      <div v-if="hasStudyData" class="chart-body" ref="trendChartRef"></div>
      <div v-else class="chart-empty">
        <span class="empty-icon">📊</span>
        <p class="empty-text">暂无学习记录</p>
        <p class="empty-hint">完成学习资源或测评后，这里会显示时长趋势</p>
      </div>
    </div>

    <!-- 两列布局：知识点掌握 + 学习效率 -->
    <div class="dashboard-row">
      <div class="card">
        <div class="card-header">
          <div class="card-title-group">
            <span class="card-title">🔥 知识点掌握分布</span>
            <span class="card-subtitle">各知识点得分概览</span>
          </div>
        </div>
        <div v-if="hasDimensionData" class="chart-body" ref="knowledgeChartRef"></div>
        <div v-else class="chart-empty">
          <span class="empty-icon">🔥</span>
          <p class="empty-text">暂无掌握数据</p>
          <p class="empty-hint">开始学习后，各维度掌握度将在此展示</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title-group">
            <span class="card-title">⚡ 学习效率曲线</span>
            <span class="card-subtitle">资源完成数趋势</span>
          </div>
        </div>
        <div v-if="hasStudyData" class="chart-body" ref="efficiencyChartRef"></div>
        <div v-else class="chart-empty">
          <span class="empty-icon">⚡</span>
          <p class="empty-text">暂无效率数据</p>
          <p class="empty-hint">完成学习活动后，效率曲线将自动生成</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useProfileStore } from '../../profile/stores/profileStore'

const profileStore = useProfileStore()

const trendChartRef = ref<HTMLElement>()
const knowledgeChartRef = ref<HTMLElement>()
const efficiencyChartRef = ref<HTMLElement>()

let trendChart: echarts.ECharts | null = null
let knowledgeChart: echarts.ECharts | null = null
let efficiencyChart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null

/** 是否有学习事件数据 */
const hasStudyData = computed(() => (profileStore.profileData.learningEvents || []).length > 0)

/** 是否有维度数据（至少一个雷达维度 > 0） */
const hasDimensionData = computed(() => {
  const dims = profileStore.profileData.dimensions || []
  return dims.filter(d => d.showOnRadar !== false).some(d => d.value > 0)
})

/** 最近7天日期标签 */
function getRecent7Days(): string[] {
  const days: string[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    days.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return days
}

/** 从画像事件计算每日学习时长 */
function getDailyStudyMinutes(): number[] {
  const events = profileStore.profileData.learningEvents || []
  const dailyMap: Record<string, number> = {}

  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const key = d.toISOString().split('T')[0]
    dailyMap[key] = 0
  }

  for (const event of events) {
    if (!event.timestamp) continue
    const day = event.timestamp.split('T')[0]
    if (day in dailyMap) {
      if (event.type === 'resource_complete') dailyMap[day] += 20
      else if (event.type === 'assess_complete') dailyMap[day] += 15
      else if (event.type === 'stage_complete') dailyMap[day] += 30
    }
  }

  return Object.values(dailyMap)
}

/** 知识点掌握分布数据（只取雷达图维度） */
function getKnowledgeDistribution(): { names: string[]; scores: number[] } {
  const dims = profileStore.profileData.dimensions || []
  const radarDims = dims.filter(d => d.showOnRadar !== false)
  const names = radarDims.map(d => d.name)
  const scores = radarDims.map(d => d.value)
  return { names, scores }
}

function initTrendChart() {
  if (!trendChartRef.value) return

  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const days = getRecent7Days()
  const minutes = getDailyStudyMinutes()

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>学习时长: {c} 分钟',
      backgroundColor: 'rgba(47,43,61,0.9)',
      borderColor: '#EBE9F1',
      textStyle: { color: '#fff', fontSize: 12 }
    },
    grid: { top: 20, right: 20, bottom: 30, left: 40 },
    xAxis: {
      type: 'category',
      data: days,
      axisLine: { lineStyle: { color: '#D8D6DE' } },
      axisLabel: { color: '#6E6B7B', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F3F2F7' } },
      axisLabel: { color: '#A8AAAE', fontSize: 11 }
    },
    series: [{
      type: 'line',
      data: minutes,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#00CFE8' },
          { offset: 1, color: '#7367F0' }
        ]),
        width: 3
      },
      itemStyle: { color: '#00CFE8', borderWidth: 2, borderColor: '#fff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0,207,232,0.25)' },
          { offset: 1, color: 'rgba(115,103,240,0.05)' }
        ])
      }
    }]
  }, true)

  trendChart.resize()
}

function initKnowledgeChart() {
  if (!knowledgeChartRef.value) return

  if (!knowledgeChart) {
    knowledgeChart = echarts.init(knowledgeChartRef.value)
  }

  const { names, scores } = getKnowledgeDistribution()

  knowledgeChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => params[0] ? `${params[0].name}<br/>掌握度: ${params[0].value}%` : '',
      backgroundColor: 'rgba(47,43,61,0.9)',
      textStyle: { color: '#fff', fontSize: 12 }
    },
    grid: { top: 20, right: 20, bottom: 30, left: 80 },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F3F2F7' } },
      axisLabel: { color: '#A8AAAE', fontSize: 11 }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: '#D8D6DE' } },
      axisLabel: { color: '#2F2B3D', fontSize: 11 },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      data: scores.map((v) => ({
        value: v,
        itemStyle: {
          color: v < 40 ? '#EA5455' : v < 70 ? '#FF9F43' : '#28C76F',
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: 14
    }]
  }, true)

  knowledgeChart.resize()
}

function initEfficiencyChart() {
  if (!efficiencyChartRef.value) return

  if (!efficiencyChart) {
    efficiencyChart = echarts.init(efficiencyChartRef.value)
  }

  const events = profileStore.profileData.learningEvents || []
  const dailyMap: Record<string, number> = {}

  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dailyMap[d.toISOString().split('T')[0]] = 0
  }

  for (const event of events) {
    if (!event.timestamp) continue
    const day = event.timestamp.split('T')[0]
    if (day in dailyMap) {
      dailyMap[day]++
    }
  }

  const dates = Object.keys(dailyMap).map(k => {
    const parts = k.split('-')
    return `${parseInt(parts[1])}/${parseInt(parts[2])}`
  })
  const counts = Object.values(dailyMap)

  efficiencyChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>完成学习: {c} 次',
      backgroundColor: 'rgba(47,43,61,0.9)',
      textStyle: { color: '#fff', fontSize: 12 }
    },
    grid: { top: 20, right: 20, bottom: 30, left: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#D8D6DE' } },
      axisLabel: { color: '#6E6B7B', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F3F2F7' } },
      axisLabel: { color: '#A8AAAE', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: counts,
      barWidth: 16,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#7367F0' },
          { offset: 1, color: '#9E94FF' }
        ]),
        borderRadius: [4, 4, 0, 0]
      }
    }]
  }, true)

  efficiencyChart.resize()
}

/** 条件性地初始化图表：只在有数据且 DOM ref 存在时才 init */
function refreshCharts() {
  nextTick(() => {
    // 先销毁旧实例，避免 v-if 切换后 ref 指向新 DOM 但旧实例残留
    if (trendChart) { trendChart.dispose(); trendChart = null }
    if (knowledgeChart) { knowledgeChart.dispose(); knowledgeChart = null }
    if (efficiencyChart) { efficiencyChart.dispose(); efficiencyChart = null }

    if (hasStudyData.value) {
      initTrendChart()
      initEfficiencyChart()
    }
    if (hasDimensionData.value) {
      initKnowledgeChart()
    }
  })
}

onMounted(() => {
  refreshCharts()

  resizeHandler = () => {
    trendChart?.resize()
    knowledgeChart?.resize()
    efficiencyChart?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

// 监听学习事件变化，自动更新图表
watch(
  () => profileStore.profileData.learningEvents?.length,
  () => refreshCharts()
)

// 监听画像维度变化，更新知识点图表
watch(
  () => profileStore.profileData.dimensions?.map(d => d.value).join(','),
  () => refreshCharts()
)

// 监听 profileJustUpdated 信号
watch(
  () => profileStore.profileJustUpdated,
  (updated) => {
    if (updated) {
      refreshCharts()
    }
  }
)

onUnmounted(() => {
  trendChart?.dispose()
  knowledgeChart?.dispose()
  efficiencyChart?.dispose()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style lang="less" scoped>
.learning-dashboard {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.dashboard-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.card {
  background: transparent;
  border: 1px solid #EBE9F1;
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 0;
}

.card-title-group {
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #2F2B3D;
}

.card-subtitle {
  font-size: 12px;
  color: #A8AAAE;
  margin-top: 2px;
}

.chart-body {
  width: 100%;
  height: 260px;
  padding: 8px 12px 12px;
}

.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 260px;
  color: #94a3b8;

  .empty-icon {
    font-size: 36px;
    margin-bottom: 8px;
    opacity: 0.5;
  }

  .empty-text {
    font-size: 14px;
    font-weight: 600;
    color: #475569;
    margin: 0 0 4px;
  }

  .empty-hint {
    font-size: 12px;
    color: #94a3b8;
    margin: 0;
    text-align: center;
    max-width: 240px;
  }
}

@media (max-width: 768px) {
  .dashboard-row {
    grid-template-columns: 1fr;
  }
}
</style>