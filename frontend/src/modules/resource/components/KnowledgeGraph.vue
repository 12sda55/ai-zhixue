<template>
  <div class="knowledge-graph-container" ref="chartRef">
    <div v-if="parseError" class="graph-empty">
      <div class="empty-icon">🕸️</div>
      <div class="empty-text">图谱数据解析失败，请刷新资源重试</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

interface GraphNode {
  id: string
  name: string
  category: 'core' | 'advanced' | 'algorithm' | 'application'
  importance: number
  desc: string
}

interface GraphEdge {
  source: string
  target: string
  label: string
}

const props = defineProps<{
  content: string
  weakPoints?: string[]
}>()

const chartRef = ref<HTMLElement>()
const parseError = ref(false)
let chart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null

const categoryColors: Record<string, string> = {
  core: '#3b82f6',
  advanced: '#8b5cf6',
  algorithm: '#10b981',
  application: '#f59e0b',
}

const categoryLabels: Record<string, string> = {
  core: '核心概念',
  advanced: '进阶知识',
  algorithm: '算法方法',
  application: '应用实践',
}

function parseGraph() {
  try {
    return JSON.parse(props.content)
  } catch {
    return { nodes: [], edges: [] }
  }
}

function renderGraph() {
  if (!chartRef.value) return

  parseError.value = false
  const graph = parseGraph()
  if (!graph.nodes || graph.nodes.length === 0) {
    parseError.value = true
    // 如果有旧图表，清空它
    if (chart) {
      chart.clear()
    }
    return
  }

  const weakPointSet = new Set(props.weakPoints || [])

  const nodes = graph.nodes.map((node: GraphNode) => {
    const isWeak = weakPointSet.has(node.name)
    return {
      id: node.id,
      name: node.name,
      symbolSize: 20 + node.importance * 8,
      category: node.category,
      itemStyle: {
        color: categoryColors[node.category] || '#6b7280',
        borderColor: isWeak ? '#EA5455' : 'transparent',
        borderWidth: isWeak ? 3 : 0,
        shadowColor: isWeak ? '#EA5455' : 'transparent',
        shadowBlur: isWeak ? 10 : 0,
      },
      label: { show: true, fontSize: 12, color: '#2F2B3D' },
    }
  })

  const edges = graph.edges.map((edge: GraphEdge) => ({
    source: edge.source,
    target: edge.target,
    label: { show: true, formatter: edge.label, fontSize: 10, color: '#6E6B7B' },
    lineStyle: { curveness: 0.2, opacity: 0.6, color: '#A8AAAE' },
    emphasis: { lineStyle: { width: 3 } }
  }))

  const categories = [
    { name: 'core', itemStyle: { color: categoryColors.core } },
    { name: 'advanced', itemStyle: { color: categoryColors.advanced } },
    { name: 'algorithm', itemStyle: { color: categoryColors.algorithm } },
    { name: 'application', itemStyle: { color: categoryColors.application } }
  ]

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = graph.nodes.find((n: GraphNode) => n.id === params.data.id)
          if (node) {
            const stars = '★'.repeat(node.importance) + '☆'.repeat(5 - node.importance)
            return `<strong>${node.name}</strong><br/>类型: ${categoryLabels[node.category] || node.category}<br/>重要度: ${stars}<br/>描述: ${node.desc}`
          }
        }
        if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}: ${params.data.label?.formatter || ''}`
        }
        return ''
      }
    },
    legend: {
      data: Object.keys(categoryLabels),
      orient: 'vertical',
      right: 10,
      top: 10,
      formatter: (name: string) => categoryLabels[name] || name,
      textStyle: { color: '#6E6B7B', fontSize: 12 }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: edges,
      categories,
      roam: true,
      draggable: true,
      force: {
        repulsion: 200,
        edgeLength: 120,
        gravity: 0.1
      },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 8],
      label: {
        position: 'right',
        formatter: '{b}',
        color: '#2F2B3D',
        fontSize: 12
      },
      lineStyle: {
        color: '#A8AAAE',
        curveness: 0.2
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 }
      }
    }]
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  chart.setOption(option, true)
  chart.resize()
}

onMounted(() => {
  renderGraph()
  resizeHandler = () => chart?.resize()
  window.addEventListener('resize', resizeHandler)
  // 延迟 resize，确保 modal transition 完成后图表尺寸正确
  setTimeout(() => chart?.resize(), 300)
})

watch(() => props.content, renderGraph, { flush: 'post' })

onUnmounted(() => {
  chart?.dispose()
  chart = null
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    resizeHandler = null
  }
})
</script>

<style lang="less" scoped>
.knowledge-graph-container {
  width: 100%;
  height: 500px;
  background: #F8F7FA;
  border-radius: 10px;
  border: 1px solid #EBE9F1;
}

.graph-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
.empty-text { color: #A8AAAE; font-size: 13px; }
</style>