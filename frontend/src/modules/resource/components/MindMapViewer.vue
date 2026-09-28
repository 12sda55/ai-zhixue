<template>
  <div class="mindmap-viewer">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="mindmap-loading">
      <div class="loading-spinner"></div>
      <div class="loading-text">正在渲染思维导图...</div>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="isEmpty" class="mindmap-empty">
      <div class="empty-icon">🗺️</div>
      <div class="empty-text">导图数据为空，请刷新资源重试</div>
    </div>
    
    <!-- SVG 思维导图 -->
    <div v-else ref="containerRef" class="mindmap-container">
      <svg ref="svgRef" class="mindmap-svg"></svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'

interface MindMapNode {
  name: string
  desc?: string
  highlight?: boolean
  children?: MindMapNode[]
}

const props = defineProps<{ content: string }>()
const containerRef = ref<HTMLElement>()
const svgRef = ref<SVGSVGElement>()
const isLoading = ref(true)
const parsedData = ref<MindMapNode | null>(null)

const isEmpty = computed(() => !parsedData.value || !parsedData.value.name)

onMounted(() => {
  parseAndRender()
})

onUnmounted(() => {
  parsedData.value = null
})

watch(() => props.content, () => {
  nextTick(() => parseAndRender())
})

function parseAndRender() {
  isLoading.value = true
  
  try {
    // 尝试解析 JSON 格式
    const jsonMatch = props.content.match(/```mindmap-data\s*([\s\S]*?)```/)
    if (jsonMatch) {
      const jsonStr = jsonMatch[1].trim()
      const data = JSON.parse(jsonStr)
      parsedData.value = data
      isLoading.value = false
      nextTick(() => renderSvgMindMap())
      return
    }
    
    // 尝试直接解析 JSON（无代码块包裹）
    try {
      const data = JSON.parse(props.content.trim())
      if (data.name && (data.children || data.desc)) {
        parsedData.value = data
        isLoading.value = false
        nextTick(() => renderSvgMindMap())
        return
      }
    } catch {
      // 不是 JSON，尝试 Markdown
    }
    
    // Markdown 格式：转换为简单的树结构
    if (props.content.includes('#') || props.content.includes('-')) {
      parsedData.value = parseMarkdownToTree(props.content)
      isLoading.value = false
      nextTick(() => renderSvgMindMap())
      return
    }
    
    parsedData.value = null
    isLoading.value = false
  } catch (e) {
    console.warn('[MindMap] 解析失败:', e)
    parsedData.value = null
    isLoading.value = false
  }
}

function parseMarkdownToTree(markdown: string): MindMapNode {
  const lines = markdown.split('\n').filter(l => l.trim())
  const root: MindMapNode = { name: '知识导图', children: [] }
  const stack: { node: MindMapNode; level: number }[] = [{ node: root, level: -1 }]
  
  for (const line of lines) {
    const match = line.match(/^(#{1,6})\s+(.+)$/) || line.match(/^(\s*[-*])\s+(.+)$/)
    if (!match) continue
    
    const level = match[1] ? match[1].length : stack[stack.length - 1].level + 1
    const name = match[2].trim()
    const node: MindMapNode = { name }
    
    // 找到父节点
    while (stack.length > 1 && stack[stack.length - 1].level >= level) {
      stack.pop()
    }
    
    const parent = stack[stack.length - 1].node
    if (!parent.children) parent.children = []
    parent.children.push(node)
    
    stack.push({ node, level })
  }
  
  return root.children?.length === 1 ? root.children[0] : root
}

function renderSvgMindMap() {
  if (!svgRef.value || !parsedData.value) return
  
  const svg = svgRef.value
  const container = containerRef.value
  if (!container) return
  
  // 清空 SVG
  svg.innerHTML = ''
  
  // 计算布局
  const layout = calculateLayout(parsedData.value)
  
  // 设置 SVG 尺寸
  const width = Math.max(layout.width + 100, container.clientWidth)
  const height = Math.max(layout.height + 50, 400)
  svg.setAttribute('width', String(width))
  svg.setAttribute('height', String(height))
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
  
  // 渲染节点和连线
  renderNodes(svg, layout.nodes, layout.edges)
}

interface LayoutNode {
  id: string
  name: string
  desc?: string
  highlight: boolean
  x: number
  y: number
  width: number
  height: number
  depth: number
}

interface LayoutEdge {
  source: LayoutNode
  target: LayoutNode
}

function calculateLayout(root: MindMapNode): { nodes: LayoutNode[]; edges: LayoutEdge[]; width: number; height: number } {
  const nodes: LayoutNode[] = []
  const edges: LayoutEdge[] = []
  
  // 计算每个节点的文本宽度
  function getTextWidth(name: string, desc?: string): number {
    const nameLen = name.length * 14 + 20
    const descLen = desc ? desc.length * 10 + 10 : 0
    return Math.max(nameLen, 80) + descLen
  }
  
  // 递归计算节点位置（从左到右布局）
  function traverse(node: MindMapNode, depth: number, yStart: number, parentId: string): { yEnd: number; node: LayoutNode } {
    const id = `node-${nodes.length}`
    const width = getTextWidth(node.name, node.desc)
    const height = node.desc ? 50 : 36
    
    const x = 50 + depth * 180
    const y = yStart + height / 2
    
    const layoutNode: LayoutNode = {
      id,
      name: node.name,
      desc: node.desc,
      highlight: node.highlight || false,
      x,
      y,
      width,
      height,
      depth,
    }
    
    nodes.push(layoutNode)
    
    // 添加连线
    if (parentId) {
      const parent = nodes.find(n => n.id === parentId)
      if (parent) {
        edges.push({ source: parent, target: layoutNode })
      }
    }
    
    // 处理子节点
    if (node.children && node.children.length > 0) {
      let currentY = yStart
      for (const child of node.children) {
        const result = traverse(child, depth + 1, currentY, id)
        currentY = result.yEnd + 20 // 子节点之间的间距
      }
      return { yEnd: currentY - 20, node: layoutNode }
    }
    
    return { yEnd: yStart + height, node: layoutNode }
  }
  
  traverse(root, 0, 20, '')
  
  // 计算总宽高
  const maxX = Math.max(...nodes.map(n => n.x + n.width))
  const maxY = Math.max(...nodes.map(n => n.y + n.height / 2))
  
  return { nodes, edges, width: maxX, height: maxY }
}

function renderNodes(svg: SVGSVGElement, nodes: LayoutNode[], edges: LayoutEdge[]) {
  // 颜色配置
  const depthColors = ['#2563eb', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
  
  // 先渲染连线
  for (const edge of edges) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    const startX = edge.source.x + edge.source.width / 2
    const startY = edge.source.y
    const endX = edge.target.x - edge.target.width / 2
    const endY = edge.target.y
    
    // 使用贝塞尔曲线
    const midX1 = startX + (endX - startX) * 0.4
    const midX2 = startX + (endX - startX) * 0.6
    
    path.setAttribute('d', `M ${startX} ${startY} C ${midX1} ${startY}, ${midX2} ${endY}, ${endX} ${endY}`)
    path.setAttribute('fill', 'none')
    path.setAttribute('stroke', '#cbd5e1')
    path.setAttribute('stroke-width', '2')
    svg.appendChild(path)
  }
  
  // 渲染节点
  for (const node of nodes) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    
    // 节点背景
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
    const rectX = node.x - node.width / 2
    const rectY = node.y - node.height / 2
    
    rect.setAttribute('x', String(rectX))
    rect.setAttribute('y', String(rectY))
    rect.setAttribute('width', String(node.width))
    rect.setAttribute('height', String(node.height))
    rect.setAttribute('rx', '8')
    rect.setAttribute('ry', '8')
    
    const color = depthColors[node.depth % depthColors.length]
    if (node.highlight) {
      rect.setAttribute('fill', '#fef3c7')
      rect.setAttribute('stroke', '#f59e0b')
      rect.setAttribute('stroke-width', '2')
    } else {
      rect.setAttribute('fill', '#f8fafc')
      rect.setAttribute('stroke', color)
      rect.setAttribute('stroke-width', '1.5')
    }
    
    g.appendChild(rect)
    
    // 节点名称
    const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    nameText.setAttribute('x', String(node.x))
    nameText.setAttribute('y', String(node.y - (node.desc ? 8 : 0)))
    nameText.setAttribute('text-anchor', 'middle')
    nameText.setAttribute('font-size', '14')
    nameText.setAttribute('font-weight', '600')
    nameText.setAttribute('fill', node.highlight ? '#92400e' : '#1e293b')
    nameText.textContent = node.name
    g.appendChild(nameText)
    
    // 节点描述
    if (node.desc) {
      const descText = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      descText.setAttribute('x', String(node.x))
      descText.setAttribute('y', String(node.y + 12))
      descText.setAttribute('text-anchor', 'middle')
      descText.setAttribute('font-size', '11')
      descText.setAttribute('fill', '#64748b')
      descText.textContent = node.desc.length > 20 ? node.desc.slice(0, 20) + '...' : node.desc
      g.appendChild(descText)
    }
    
    // 高亮标记
    if (node.highlight) {
      const star = document.createElementNS('http://www.w3.org/2000/svg', 'text')
      star.setAttribute('x', String(rectX + 8))
      star.setAttribute('y', String(rectY + 12))
      star.setAttribute('font-size', '12')
      star.textContent = '⭐'
      g.appendChild(star)
    }
    
    svg.appendChild(g)
  }
}
</script>

<style lang="less" scoped>
.mindmap-viewer {
  width: 100%;
  height: 400px;
  background: transparent;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  overflow: auto;
}

.mindmap-container {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
}

.mindmap-svg {
  display: block;
  min-width: 100%;
  min-height: 100%;
}

.mindmap-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #F8F7FA;
  border-radius: 10px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 12px;
  color: #64748b;
  font-size: 14px;
}

.mindmap-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #F8F7FA;
  border-radius: 10px;
}

.empty-icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
.empty-text { color: #94a3b8; font-size: 13px; }
</style>