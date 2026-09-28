<template>
  <div class="assess-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { AssessModule } from '../../../shared/types'

const props = defineProps<{ modules: AssessModule[] }>()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})

watch(() => props.modules, () => updateChart(), { deep: true })

function handleResize() {
  chart?.resize()
}

function updateChart() {
  if (!chart) return
  chart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: '#131a2e',
      borderColor: 'rgba(0, 212, 255, 0.15)',
      textStyle: { color: '#e8f4fd', fontSize: 11 },
    },
    legend: {
      data: ['当前水平', '目标水平'],
      bottom: 4,
      textStyle: { color: '#5a7a8a', fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
    },
    radar: {
      indicator: props.modules.map(m => ({ name: m.name, max: 100 })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#7eb8d0', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)' } },
      splitArea: { areaStyle: { color: ['rgba(0, 212, 255, 0.02)', 'rgba(0, 212, 255, 0.04)'] } },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.modules.map(m => m.score),
            name: '当前水平',
            lineStyle: { color: '#00d4ff', width: 2 },
            areaStyle: {
              color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.25)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0.02)' },
              ]),
            },
            itemStyle: { color: '#00d4ff' },
            symbol: 'circle',
            symbolSize: 6,
          },
          {
            value: props.modules.map(() => 80),
            name: '目标水平',
            lineStyle: { color: '#a78bfa', width: 1.5, type: 'dashed' },
            areaStyle: { color: 'rgba(167, 139, 250, 0.06)' },
            itemStyle: { color: '#a78bfa' },
            symbol: 'circle',
            symbolSize: 4,
          },
        ],
        emphasis: {
          lineStyle: { width: 3 },
        },
      },
      {
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: props.modules.map(m => ({
          value: m.score,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 1, 0, 0, [
              { offset: 0, color: m.color + '88' },
              { offset: 1, color: m.color },
            ]),
          },
        })),
        barWidth: 24,
        label: {
          show: true,
          position: 'top',
          color: '#7eb8d0',
          fontSize: 9,
          formatter: '{c}%',
        },
      },
    ],
    grid: [
      { left: '4%', top: '8%', width: '46%', height: '80%' },
      { left: '54%', top: '8%', width: '42%', height: '80%' },
    ],
    xAxis: [
      { gridIndex: 0, show: false },
      {
        gridIndex: 1,
        type: 'category',
        data: props.modules.map(m => m.name),
        axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
        axisLabel: { color: '#5a7a8a', fontSize: 9, interval: 0 },
      },
    ],
    yAxis: [
      { gridIndex: 0, show: false },
      {
        gridIndex: 1,
        type: 'value',
        max: 100,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.06)' } },
        axisLabel: { color: '#5a7a8a', fontSize: 9 },
      },
    ],
  }, true)
}
</script>

<style lang="less" scoped>
.assess-chart {
  background: rgba(0, 212, 255, 0.04);
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0, 212, 255, 0.08);
  min-height: 260px;
}
</style>