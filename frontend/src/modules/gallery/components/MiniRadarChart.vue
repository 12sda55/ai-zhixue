<template>
  <div ref="chartRef" class="mini-radar-chart" :style="{ width: `${size}px`, height: `${size}px` }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart as RadarChartSeries } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { DIMENSION_META } from '../../../shared/types'
import type { ProfileAllDimensionKey } from '../../../shared/types'

echarts.use([RadarChartSeries, CanvasRenderer])

/** 维度 key → 图标+名称 的硬编码兜底表（确保即使 DIMENSION_META 查找失败也有显示） */
const FALLBACK_DIM_INFO: Record<string, { icon: string; name: string }> = {
  base_level: { icon: '💡', name: '基础水平' },
  weak_points: { icon: '⚡', name: '薄弱知识点' },
  study_goal: { icon: '🎯', name: '学习目标' },
  learning_engagement: { icon: '🔥', name: '学习投入度' },
  study_rhythm: { icon: '⏱️', name: '学习节奏' },
  interest_preference: { icon: '🎨', name: '内容偏好' },
  knowledge_mastery: { icon: '📚', name: '知识掌握度' },
  exercise_completion: { icon: '✅', name: '练习完成度' },
  major: { icon: '🎓', name: '专业方向' },
  grade: { icon: '📊', name: '年级水平' },
  cognitive_style: { icon: '🧠', name: '认知风格' },
}

const props = withDefaults(defineProps<{
  dimensions: { key: string; name?: string; value: number; label?: string }[]
  size?: number
  showAxisName?: boolean
}>(), {
  size: 160,
  showAxisName: true,
})

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

function buildOption() {
  const dims = props.dimensions || []
  if (dims.length === 0) return {}

  const indicator = dims.map((d) => {
    const meta = DIMENSION_META[d.key as ProfileAllDimensionKey]
    const fallback = FALLBACK_DIM_INFO[d.key]
    const icon = meta?.icon || fallback?.icon || ''
    // 优先用 DIMENSION_META 的 name，然后 fallback 表，然后 dim 自身的 name/label/key
    const name = meta?.name || fallback?.name || d.label || d.name || d.key
    const displayName = props.showAxisName && icon ? `${icon} ${name}` : (props.showAxisName ? name : '')
    return {
      name: displayName,
      max: 100,
    }
  })

  const values = dims.map(d => d.value)
  const fontSize = props.size >= 220 ? 11 : 9
  const radius = props.showAxisName ? '58%' : '68%'

  return {
    radar: {
      indicator,
      shape: 'polygon',
      radius,
      center: ['50%', '50%'],
      axisName: {
        show: props.showAxisName,
        color: '#7eb8d0',
        fontSize,
        fontWeight: 500,
        lineHeight: 14,
      },
      nameGap: props.showAxisName ? 8 : 5,
      splitNumber: 3,
      splitArea: {
        areaStyle: {
          color: [
            'rgba(37, 99, 235, 0.02)',
            'rgba(37, 99, 235, 0.04)',
            'rgba(37, 99, 235, 0.06)',
          ],
        },
      },
      splitLine: {
        lineStyle: { color: 'rgba(37, 99, 235, 0.08)' },
      },
      axisLine: {
        lineStyle: { color: 'rgba(37, 99, 235, 0.1)' },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        symbol: 'circle',
        symbolSize: 3,
        lineStyle: {
          color: '#06b6d4',
          width: 1.5,
        },
        areaStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
            { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
            { offset: 1, color: 'rgba(6, 182, 212, 0.03)' },
          ]),
        },
        itemStyle: {
          color: '#06b6d4',
          shadowColor: 'rgba(6, 182, 212, 0.4)',
          shadowBlur: 4,
        },
      }],
      emphasis: {
        lineStyle: { width: 2 },
      },
    }],
    animation: true,
    animationDuration: 600,
    animationEasing: 'cubicOut',
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, undefined, {
    renderer: 'canvas',
    width: props.size,
    height: props.size,
  })
  chartInstance.setOption(buildOption())
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), { notMerge: true })
}

watch(() => [props.dimensions, props.showAxisName], () => {
  nextTick(() => updateChart())
}, { deep: true })

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style lang="less" scoped>
.mini-radar-chart {
  flex-shrink: 0;
}
</style>
