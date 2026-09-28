<template>
  <div ref="chartRef" class="radar-chart" :class="{ 'perfect-glow': isPerfect }">
    <div class="live-tag">
      <span class="live-dot" />
      <span>实时</span>
    </div>
    <!-- 画像更新闪烁遮罩 -->
    <Transition name="flash-fade">
      <div v-if="hasChanges && isMounted" class="update-flash">
        <span class="flash-icon">✨</span>
        <span>画像已更新</span>
      </div>
    </Transition>
    <!-- 完美达成金色光晕 -->
    <Transition name="perfect-fade">
      <div v-if="isPerfect" class="perfect-overlay">
        <div class="perfect-halo" />
        <span class="perfect-star">⭐</span>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart as RadarChartSeries } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProfileData, ProfileAllDimensionKey } from '../../../shared/types'
import { DIMENSION_META } from '../../../shared/types'

echarts.use([RadarChartSeries, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  data: ProfileData
  isPerfect?: boolean
  iconOnly?: boolean
}>()

const chartRef = ref<HTMLDivElement>()
const hasChanges = ref(false)
const isMounted = ref(false)
let chartInstance: echarts.ECharts | null = null
let prevValues: number[] = []
let flashTimer: ReturnType<typeof setTimeout> | null = null

// ★ 关键：用 computed 建立响应式依赖，确保维度值变化时能被追踪到
// 只取雷达图上显示的维度（showOnRadar !== false）
const radarDimensions = computed(() => {
  const dims = props.data?.dimensions || []
  return dims.filter(d => d.showOnRadar !== false)
})

const dimensionValues = computed(() => {
  return radarDimensions.value.map(d => d.value)
})

// 维度摘要字符串，作为 watch 的稳定源
const dimensionSummary = computed(() => JSON.stringify(dimensionValues.value))

function buildOption(data: ProfileData, changedIndices: number[]) {
  const dims = radarDimensions.value
  const indicator = dims.map(d => {
    const meta = DIMENSION_META[d.key as ProfileAllDimensionKey]
    const icon = meta?.icon || ''
    const name = d.name
    if (props.iconOnly) {
      return { name: icon, max: 100 }
    }
    return { name: icon ? `${icon} ${name}` : name, max: 100 }
  })

  const values = dims.map(d => d.value)
  const targetValues = dims.map(d =>
    d.key === 'weak_points' ? 85 : 80
  )

  const hasAnyChange = changedIndices.length > 0

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(10, 14, 39, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.2)',
      borderWidth: 1,
      textStyle: { color: '#c8dce8', fontSize: 12 },
      padding: [8, 12],
      extraCssText: 'backdrop-filter: blur(10px); border-radius: 8px;',
      formatter: (params: any) => {
        if (params.value && dims) {
          const items = dims.map((d, i) => {
            const meta = DIMENSION_META[d.key as ProfileAllDimensionKey]
            const isChanged = changedIndices.includes(i)
            return `<div style="display:flex;gap:6px;margin:2px 0;">
              <span style="color:${meta?.color || '#7eb8d0'}">${meta?.icon || ''} ${d.name}</span>
              <span style="color:#00d4ff;font-weight:700">${params.value[i]}</span>
              <span style="color:#5a7a8a">${d.label}</span>
              ${isChanged ? '<span style="color:#28C76F;font-weight:700"> ↑updated</span>' : ''}
            </div>`
          })
          return `<div style="padding:4px 0">${items.join('')}</div>`
        }
        return ''
      },
    },
    legend: {
      right: 4,
      top: 4,
      orient: 'vertical',
      textStyle: { color: '#5a7a8a', fontSize: 10 },
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 8,
    },
    radar: {
      indicator,
      shape: 'polygon',
      radius: '65%',
      center: ['50%', '48%'],
      axisName: {
        color: '#7eb8d0',
        fontSize: 10,
        fontWeight: 500,
      },
      splitNumber: 4,
      splitArea: {
        areaStyle: {
          color: [
            'rgba(0, 212, 255, 0.02)',
            'rgba(0, 212, 255, 0.04)',
            'rgba(0, 212, 255, 0.06)',
            'rgba(0, 212, 255, 0.08)',
          ],
        },
      },
      splitLine: {
        lineStyle: { color: 'rgba(0, 212, 255, 0.1)' },
      },
      axisLine: {
        lineStyle: { color: 'rgba(0, 212, 255, 0.12)' },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: targetValues,
            name: '理想',
            symbol: 'circle',
            symbolSize: 3,
            lineStyle: {
              color: 'rgba(167, 139, 250, 0.3)',
              width: 1,
              type: 'dashed',
            },
            areaStyle: { color: 'rgba(167, 139, 250, 0.04)' },
            itemStyle: { color: '#a78bfa', opacity: 0.4 },
          },
          {
            value: values,
            name: '当前',
            symbol: 'circle',
            symbolSize: hasAnyChange ? 7 : 5,
            lineStyle: {
              color: hasAnyChange ? '#28C76F' : '#00d4ff',
              width: hasAnyChange ? 2.5 : 2,
            },
            areaStyle: {
              color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                {
                  offset: 0,
                  color: hasAnyChange
                    ? 'rgba(40, 199, 111, 0.35)'
                    : 'rgba(0, 212, 255, 0.3)',
                },
                {
                  offset: 1,
                  color: hasAnyChange
                    ? 'rgba(40, 199, 111, 0.04)'
                    : 'rgba(0, 212, 255, 0.04)',
                },
              ]),
            },
            itemStyle: {
              color: hasAnyChange ? '#28C76F' : '#00d4ff',
              shadowColor: hasAnyChange
                ? 'rgba(40, 199, 111, 0.6)'
                : 'rgba(0, 212, 255, 0.5)',
              shadowBlur: hasAnyChange ? 10 : 6,
            },
          },
        ],
        emphasis: {
          lineStyle: { width: 3 },
        },
      },
    ],
    animationDuration: hasAnyChange ? 1200 : 600,
    animationEasing: 'cubicOut' as const,
    animationDurationUpdate: 800,
    animationEasingUpdate: 'cubicInOut' as const,
  }
}

function detectChanges(newValues: number[]): number[] {
  const changed: number[] = []
  if (prevValues.length === newValues.length) {
    newValues.forEach((v, i) => {
      if (v !== prevValues[i]) changed.push(i)
    })
  }
  return changed
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  prevValues = [...dimensionValues.value]
  chartInstance.setOption(buildOption(props.data, []))
}

function updateChart() {
  // 安全检查：组件未挂载或图表实例不存在时跳过
  if (!isMounted.value || !chartInstance) return

  const newValues = dimensionValues.value
  const changedIndices = detectChanges(newValues)

  // 有变化时显示闪烁提示
  if (changedIndices.length > 0) {
    hasChanges.value = true
    if (flashTimer) clearTimeout(flashTimer)
    flashTimer = setTimeout(() => { hasChanges.value = false }, 3000)
  }

  // 更新 prevValues
  prevValues = [...newValues]

  // 关键：用 notMerge: true 完全替换整个配置，确保数据准确更新
  chartInstance.setOption(buildOption(props.data, changedIndices), {
    notMerge: true,
    lazyUpdate: false,
  })
}

// ★ 关键：watch computed 摘要值，维度值任何变化都会触发
watch(dimensionSummary, () => {
  nextTick(() => updateChart())
})

onMounted(() => {
  isMounted.value = true
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  isMounted.value = false
  // 先清除状态，避免 transition 组件在卸载时操作 DOM
  hasChanges.value = false
  if (flashTimer) {
    clearTimeout(flashTimer)
    flashTimer = null
  }
  window.removeEventListener('resize', handleResize)
  // 等待 DOM 更新后再销毁图表
  nextTick(() => {
    chartInstance?.dispose()
    chartInstance = null
  })
})

function handleResize() {
  chartInstance?.resize()
}
</script>

<style lang="less" scoped>
.radar-chart {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 220px;
}

.live-tag {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid rgba(52, 211, 153, 0.2);
  z-index: 1;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; box-shadow: 0 0 4px rgba(52, 211, 153, 0.6); }
  50% { opacity: 0.4; box-shadow: none; }
}

/* 画像更新闪烁提示 */
.update-flash {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(40, 199, 111, 0.9), rgba(111, 209, 148, 0.9));
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 4px 20px rgba(40, 199, 111, 0.4);
  z-index: 10;
  pointer-events: none;
  backdrop-filter: blur(4px);
}

/* ===== 完美达成金色光晕 ===== */
.radar-chart.perfect-glow {
  box-shadow: 0 0 30px rgba(245, 158, 11, 0.15), 0 0 60px rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.3) !important;
}

.perfect-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
  pointer-events: none;
}

.perfect-halo {
  position: absolute;
  width: 70%;
  height: 70%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.02), transparent);
  animation: halo-pulse 2s ease-in-out infinite;
}

.perfect-star {
  font-size: 20px;
  position: absolute;
  top: 12%;
  right: 15%;
  animation: star-sparkle 1.5s ease-in-out infinite;
}

@keyframes halo-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
}

@keyframes star-sparkle {
  0%, 100% { transform: scale(1) rotate(0deg); opacity: 1; }
  50% { transform: scale(1.3) rotate(15deg); opacity: 0.7; }
}

.perfect-fade-enter-active { animation: perfect-in 0.6s ease-out; }
.perfect-fade-leave-active { animation: perfect-out 0.4s ease-in; }

@keyframes perfect-in {
  0% { opacity: 0; transform: scale(0.5); }
  100% { opacity: 1; transform: scale(1); }
}

@keyframes perfect-out {
  0% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(0.8); }
}

.flash-icon {
  font-size: 16px;
  animation: sparkle 0.6s ease-in-out infinite alternate;
}

@keyframes sparkle {
  0% { transform: scale(1) rotate(0deg); }
  100% { transform: scale(1.3) rotate(15deg); }
}

/* 过渡动画 */
.flash-fade-enter-active {
  animation: flash-in 0.4s ease-out;
}
.flash-fade-leave-active {
  animation: flash-out 0.3s ease-in;
}

@keyframes flash-in {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.7); }
  100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}

@keyframes flash-out {
  0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
}
</style>
