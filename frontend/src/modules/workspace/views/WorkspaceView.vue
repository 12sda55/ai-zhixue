<template>
  <div class="workspace-view">
    <!-- 左侧：学习路线时间轴 -->
    <aside class="workspace-sidebar">
      <div class="sidebar-header">
        <div class="header-left">
          <div class="header-icon">🗺️</div>
          <div>
            <div class="sidebar-title">学习工作台</div>
            <div class="sidebar-subtitle">路径 + 资源 · 一站式学习</div>
          </div>
        </div>
        <span v-if="overallProgress > 0" class="progress-badge">{{ overallProgress }}%</span>
      </div>

      <div v-if="overallProgress > 0" class="overall-bar">
        <div class="overall-fill" :style="{ width: overallProgress + '%' }"></div>
      </div>

      <div class="stage-list">
        <!-- 空状态 -->
        <div v-if="stages.length === 0" class="empty-state">
          <span class="empty-icon">🗺️</span>
          <div class="empty-title">暂无学习路径</div>
          <div class="empty-desc">去智能体页面生成你的专属学习路径</div>
        </div>

        <!-- 阶段列表 -->
        <div
          v-for="stage in stages"
          :key="stage.id"
          class="stage-item"
          :class="{
            completed: stage.status === 'completed',
            active: stage.status === 'active',
            expanded: wsStore.isStageExpanded(stage.id),
          }"
        >
          <!-- 阶段头部 -->
          <div class="stage-header" @click="wsStore.toggleStage(stage.id)">
            <div class="stage-indicator">
              <span v-if="stage.status === 'completed'" class="stage-dot done">✅</span>
              <span v-else-if="stage.status === 'active'" class="stage-dot active">●</span>
              <span v-else class="stage-dot pending">○</span>
            </div>
            <div class="stage-info">
              <div class="stage-name">{{ stage.title }}</div>
              <div class="stage-meta">
                <span>{{ stage.suggestedDays ?? '--' }}天</span>
                <span>{{ wsStore.getStageProgress(stage) }}%</span>
              </div>
            </div>
            <span class="stage-arrow">{{ wsStore.isStageExpanded(stage.id) ? '▾' : '▸' }}</span>
          </div>

          <!-- 阶段资源 -->
          <div v-if="wsStore.isStageExpanded(stage.id)" class="stage-resources">
            <div v-if="wsStore.getStageResources(stage).length === 0" class="no-resources">
              暂无匹配资源
            </div>
            <div
              v-for="res in wsStore.getStageResources(stage)"
              :key="res.id"
              class="resource-mini"
              :class="{ selected: wsStore.selectedResourceId === res.id }"
              @click="wsStore.selectResource(res.id)"
            >
              <span class="resource-type-icon">{{ getTypeIcon(res.type) }}</span>
              <span class="resource-name">{{ res.title }}</span>
              <span v-if="res.isWeakPoint" class="weak-tag">薄弱</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧：内容阅读面板 -->
    <main class="workspace-content">
      <!-- 未选中资源时的引导 -->
      <div v-if="!wsStore.selectedResource" class="content-placeholder">
        <span class="placeholder-icon">📚</span>
        <div class="placeholder-title">学习工作台</div>
        <div class="placeholder-desc">从左侧选择一个阶段和资源，开始学习</div>
        <div class="placeholder-hint">资源已按画像匹配度从高到低排列</div>
      </div>

      <!-- 选中资源的内容阅读 -->
      <div v-else class="content-reader">
        <div class="reader-header">
          <span class="reader-type-badge" :style="{ background: getTypeColor(wsStore.selectedResource.type) }">
            {{ getTypeIcon(wsStore.selectedResource.type) }} {{ getTypeLabel(wsStore.selectedResource.type) }}
          </span>
          <h2 class="reader-title">{{ wsStore.selectedResource.title }}</h2>
          <div class="reader-actions">
            <button class="action-btn complete-btn" @click="markComplete" :disabled="markingDone || wsStore.selectedResource?.status === 'completed'">
              {{ wsStore.selectedResource?.status === 'completed' ? '✅ 已完成' : '✅ 标记完成' }}
            </button>
            <button class="action-btn close-btn" @click="wsStore.clearSelection()">✕ 关闭</button>
          </div>
        </div>

        <div class="reader-body">
          <!-- 视频类型 -->
          <div v-if="wsStore.selectedResource.type === 'video' && wsStore.selectedResource.url" class="video-player">
            <video :src="wsStore.selectedResource.url" controls class="video-element"></video>
          </div>

          <!-- 知识图谱：ECharts 渲染 -->
          <div v-else-if="wsStore.selectedResource.type === 'knowledge-graph' && wsStore.selectedResource.content" class="graph-section">
            <div class="graph-header">
              <div class="graph-title">🔗 知识关联图谱</div>
              <div class="graph-desc">展示当前知识点的核心概念、进阶知识和关联关系。拖拽节点可重新布局，滚轮缩放，悬停查看详情。</div>
              <div class="graph-legend">
                <span class="legend-item"><span class="legend-dot" style="background:#3b82f6"></span>核心概念</span>
                <span class="legend-item"><span class="legend-dot" style="background:#8b5cf6"></span>进阶知识</span>
                <span class="legend-item"><span class="legend-dot" style="background:#10b981"></span>算法方法</span>
                <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span>应用实践</span>
              </div>
            </div>
            <KnowledgeGraph :content="wsStore.selectedResource.content" :weak-points="profileStore.profileData.weak_points" />
          </div>

          <!-- 思维导图：Markmap 渲染 -->
          <div v-else-if="wsStore.selectedResource.type === 'mindmap' && wsStore.selectedResource.content" class="mindmap-section">
            <MindMapViewer :content="wsStore.selectedResource.content" />
          </div>

          <!-- 代码类型 -->
          <div v-else-if="wsStore.selectedResource.type === 'code' && wsStore.selectedResource.content" class="code-block-wrapper">
            <pre class="code-block"><code>{{ wsStore.selectedResource.content }}</code></pre>
            <button class="copy-btn" @click="copyCode(wsStore.selectedResource.content!)">📋 复制代码</button>
          </div>

          <!-- Markdown 内容（文档/练习题等） -->
          <div v-else-if="wsStore.selectedResource.content" class="markdown-body" v-html="renderMarkdown(wsStore.selectedResource.content)"></div>

          <!-- 无内容提示：视频有URL不算无内容 -->
          <div v-if="!wsStore.selectedResource.content && !(wsStore.selectedResource.type === 'video' && wsStore.selectedResource.url)" class="no-content-hint">
            <div class="no-content-text">该资源暂无详细内容</div>
            <div class="no-content-desc">内容可能未成功保存，请前往智能体页面重新生成资源</div>
            <button class="action-btn" style="margin-top: 12px; border-color: rgba(37,99,235,0.2); background: rgba(37,99,235,0.06); color: #2563eb;" @click="$router.push('/agent')">前往智能体生成</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { message } from 'ant-design-vue'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import KnowledgeGraph from '../../resource/components/KnowledgeGraph.vue'
import MindMapViewer from '../../resource/components/MindMapViewer.vue'

const wsStore = useWorkspaceStore()
const profileStore = useProfileStore()
const markingDone = ref(false)

const TYPE_ICONS: Record<string, string> = {
  document: '📄', video: '🎬', exercise: '📝', code: '💻', mindmap: '🧠', 'knowledge-graph': '🔗', extension: '📚',
}
const TYPE_LABELS: Record<string, string> = {
  document: '文档', video: '视频', exercise: '练习', code: '代码', mindmap: '思维导图', 'knowledge-graph': '图谱', extension: '拓展',
}
const TYPE_COLORS: Record<string, string> = {
  document: '#3b82f6', video: '#ef4444', exercise: '#22c55e', code: '#c084fc', mindmap: '#f59e0b', 'knowledge-graph': '#8b5cf6', extension: '#06b6d4',
}

const stages = computed(() => wsStore.stages)

const overallProgress = computed(() => {
  const s = stages.value
  if (s.length === 0) return 0
  const total = s.reduce((sum, st) => sum + wsStore.getStageProgress(st), 0)
  return Math.round(total / s.length)
})

function getTypeIcon(type: string) { return TYPE_ICONS[type] || '📄' }
function getTypeLabel(type: string) { return TYPE_LABELS[type] || '资源' }
function getTypeColor(type: string) { return TYPE_COLORS[type] || '#6b7280' }

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
const purifyConfig = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'span', 'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img'],
  ALLOWED_ATTR: ['href', 'class', 'target', 'rel', 'src', 'alt'],
}

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text), purifyConfig) as string
}

function copyCode(code: string) {
  navigator.clipboard.writeText(code)
  message.success('代码已复制')
}

async function markComplete() {
  const res = wsStore.selectedResource
  if (!res || res.status === 'completed') return
  markingDone.value = true
  wsStore.markResourceComplete(res.id)
  message.success(`已完成「${res.title}」，画像已更新！`)
  markingDone.value = false
}
</script>

<style lang="less" scoped>
.workspace-view {
  display: flex;
  height: calc(100vh - 60px);
  background: transparent;
}

/* ===== 左侧边栏 ===== */
.workspace-sidebar {
  width: 320px;
  min-width: 320px;
  border-right: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 10px rgba(37, 99, 235, 0.3);
  font-size: 14px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.sidebar-subtitle {
  font-size: 11px;
  color: #64748b;
}

.progress-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-weight: 600;
}

.overall-bar {
  height: 3px;
  background: rgba(37, 99, 235, 0.08);
  overflow: hidden;
}

.overall-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  transition: width 0.5s ease;
}

/* ===== 阶段列表 ===== */
.stage-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon { font-size: 36px; margin-bottom: 8px; }
.empty-title { font-size: 15px; font-weight: 600; color: #1e293b; }
.empty-desc { font-size: 12px; color: #64748b; margin-top: 4px; }

.stage-item {
  margin: 2px 8px;
  border-radius: 8px;
  transition: all 0.2s;
}

.stage-item.active {
  background: rgba(37, 99, 235, 0.04);
}

.stage-item.completed {
  opacity: 0.65;
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  border-radius: 8px;
  transition: background 0.15s;
}

.stage-header:hover {
  background: rgba(37, 99, 235, 0.04);
}

.stage-dot {
  font-size: 12px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.stage-dot.done { opacity: 0.7; }
.stage-dot.active { color: #2563eb; animation: pulse 2s infinite; }
.stage-dot.pending { color: #94a3b8; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.stage-info {
  flex: 1;
  min-width: 0;
}

.stage-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stage-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
}

.stage-arrow {
  font-size: 14px;
  color: #94a3b8;
}

/* 阶段资源 */
.stage-resources {
  padding: 2px 12px 8px 38px;
}

.no-resources {
  font-size: 12px;
  color: #94a3b8;
  padding: 6px 0;
}

.resource-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #475569;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.resource-mini:hover {
  background: rgba(37, 99, 235, 0.04);
  border-color: rgba(37, 99, 235, 0.08);
}

.resource-mini.selected {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.2);
  color: #1e293b;
}

.resource-type-icon { font-size: 14px; flex-shrink: 0; }
.resource-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.weak-tag {
  font-size: 10px;
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

/* ===== 右侧内容区 ===== */
.workspace-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px;
}

.content-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.placeholder-icon { font-size: 44px; margin-bottom: 12px; }
.placeholder-title { font-size: 18px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
.placeholder-desc { font-size: 13px; color: #475569; }
.placeholder-hint { font-size: 12px; color: #94a3b8; margin-top: 4px; }

/* 内容阅读器 */
.content-reader {
  max-width: 860px;
}

.reader-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
}

.reader-type-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.reader-title {
  flex: 1;
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.reader-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.complete-btn {
  border-color: rgba(34, 197, 94, 0.2);
  background: rgba(34, 197, 94, 0.06);
  color: #22c55e;
}

.complete-btn:hover:not(:disabled) { background: rgba(34, 197, 94, 0.12); }
.complete-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.close-btn {
  border-color: rgba(37, 99, 235, 0.1);
  background: transparent;
  color: #475569;
}

.close-btn:hover { background: rgba(37, 99, 235, 0.04); }

.reader-body {
  line-height: 1.8;
}

.video-player {
  margin-bottom: 18px;
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  border: 1px solid rgba(37, 99, 235, 0.08);
}

.video-element {
  width: 100%;
  max-height: 480px;
}

.markdown-body {
  color: #334155;
  font-size: 14px;
}

.no-content-hint {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
}
.no-content-text { font-size: 16px; font-weight: 600; color: #64748b; margin-bottom: 6px; }
.no-content-desc { font-size: 13px; }

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  color: #1e293b;
  margin: 18px 0 8px;
}

.markdown-body :deep(p) { margin: 6px 0; }

.markdown-body :deep(code) {
  background: rgba(37, 99, 235, 0.06);
  color: #2563eb;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}

.markdown-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid rgba(37, 99, 235, 0.08);
  margin: 8px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 18px;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #2563eb;
  margin: 8px 0;
  padding: 6px 12px;
  background: rgba(37, 99, 235, 0.03);
  color: #475569;
}

/* 知识图谱/思维导图容器 */
.graph-section, .mindmap-section {
  min-height: 400px;
  margin-bottom: 18px;
}

.graph-header {
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.06), rgba(59, 130, 246, 0.04));
  border-radius: 10px;
  margin-bottom: 12px;
  border: 1px solid rgba(139, 92, 246, 0.12);
}

.graph-title {
  font-size: 17px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 6px;
}

.graph-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 10px;
}

.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #475569;
}

.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.code-block-wrapper {
  position: relative;
}

.code-block {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid rgba(37, 99, 235, 0.08);
  margin: 8px 0;
  font-size: 13px;
  line-height: 1.6;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.15);
  color: #2563eb;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.copy-btn:hover { background: rgba(37, 99, 235, 0.15); }

/* 滚动条 */
.stage-list::-webkit-scrollbar,
.workspace-content::-webkit-scrollbar {
  width: 4px;
}

.stage-list::-webkit-scrollbar-thumb,
.workspace-content::-webkit-scrollbar-thumb {
  background: rgba(37, 99, 235, 0.12);
  border-radius: 2px;
}
</style>
