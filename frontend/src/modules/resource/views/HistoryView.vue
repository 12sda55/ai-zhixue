<template>
  <div class="history-view">
    <div class="history-header">
      <div class="header-left">
        <div class="header-icon">📋</div>
        <div>
          <div class="history-title">历史生成记录</div>
          <div class="history-desc">所有 AI 生成资源的完整记录</div>
        </div>
      </div>
      <div class="history-actions">
        <a-select v-model:value="filterType" style="width: 120px" placeholder="资源类型">
          <a-select-option value="all">全部类型</a-select-option>
          <a-select-option value="document">文档</a-select-option>
          <a-select-option value="mindmap">导图</a-select-option>
          <a-select-option value="exercise">题库</a-select-option>
          <a-select-option value="code">代码</a-select-option>
          <a-select-option value="video">视频</a-select-option>
          <a-select-option value="knowledge-graph">图谱</a-select-option>
        </a-select>
        <a-button type="default" @click="clearAllHistory" :disabled="filteredResources.length === 0">
          清空历史
        </a-button>
      </div>
    </div>

    <div class="history-stats">
      <div class="stat-item">
        <span class="stat-icon">📊</span>
        <span class="stat-value">{{ filteredResources.length }}</span>
        <span class="stat-label">条记录</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">🤖</span>
        <span class="stat-value">{{ filteredResources.filter(r => r.aiGenerated).length }}</span>
        <span class="stat-label">AI生成</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">🎬</span>
        <span class="stat-value">{{ filteredResources.filter(r => r.type === 'video').length }}</span>
        <span class="stat-label">视频</span>
      </div>
    </div>

    <div class="history-list" v-if="filteredResources.length > 0">
      <div class="history-item" v-for="item in filteredResources" :key="item.id">
        <div class="item-icon">{{ getTypeIcon(item.type) }}</div>
        <div class="item-content" @click="viewItem(item)" style="cursor: pointer">
          <div class="item-title">{{ item.title }}</div>
          <div class="item-meta">
            <span class="item-type">{{ getTypeName(item.type) }}</span>
            <span class="item-time">{{ formatTime(item.createdAt) }}</span>
            <span v-if="item.aiGenerated" class="ai-badge">AI</span>
            <span v-if="item.status === 'completed'" class="done-badge">已完成</span>
          </div>
        </div>
        <div class="item-actions">
          <a-button type="link" size="small" @click="viewItem(item)">查看</a-button>
          <a-button type="link" size="small" @click="deleteItem(item.id)">删除</a-button>
        </div>
      </div>
    </div>

    <div class="history-empty" v-else>
      <div class="empty-icon">📭</div>
      <div class="empty-text">暂无历史记录</div>
      <div class="empty-desc">运行智能体生成资源后，记录会保存在这里</div>
    </div>

    <!-- 资源详情弹窗 -->
    <div v-if="selectedItem" class="detail-overlay" @click.self="selectedItem = null">
      <div class="detail-panel">
        <div class="detail-header">
          <span class="detail-type-badge" :style="{ background: getTypeColor(selectedItem.type) }">
            {{ getTypeIcon(selectedItem.type) }} {{ getTypeName(selectedItem.type) }}
          </span>
          <h3 class="detail-title">{{ selectedItem.title }}</h3>
          <button class="detail-close" @click="selectedItem = null">✕</button>
        </div>
        <div class="detail-body">
          <!-- 视频 -->
          <div v-if="selectedItem.type === 'video' && selectedItem.url" class="detail-video">
            <video :src="selectedItem.url" controls style="width: 100%; border-radius: 8px; max-height: 400px" />
          </div>
          <!-- 内容 -->
          <div v-if="selectedItem.content" class="detail-content" v-html="renderMarkdown(selectedItem.content)"></div>
          <div v-else class="detail-empty">暂无详细内容</div>
        </div>
        <div class="detail-footer">
          <span class="detail-time">{{ selectedItem.createdAt ? formatTime(selectedItem.createdAt) : '' }}</span>
          <button
            v-if="selectedItem.status !== 'completed'"
            class="detail-complete-btn"
            @click="markComplete(selectedItem)"
          >✅ 标记完成</button>
          <span v-else class="detail-done">✅ 已完成</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useResourceStore } from '../stores/resourceStore'
import { message } from 'ant-design-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import type { ResourceItem } from '../../../shared/types'
import { getContent } from '../../path/api/learningApi'

const resourceStore = useResourceStore()
const selectedItem = ref<ResourceItem | null>(null)
const filterType = ref('all')

const md = new MarkdownIt({ html: false, linkify: true })
function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(md.render(text), {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'span', 'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
  }) as string
}

const filteredResources = computed(() => {
  const all = resourceStore.resources
  if (filterType.value === 'all') return all
  return all.filter(r => r.type === filterType.value)
})

function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    'document': '📄', 'mindmap': '🗺️', 'exercise': '📝', 'code': '💻',
    'video': '🎬', 'knowledge-graph': '🔗',
  }
  return icons[type] || '📦'
}

function getTypeName(type: string): string {
  const names: Record<string, string> = {
    'document': '文档', 'mindmap': '导图', 'exercise': '题库', 'code': '代码',
    'video': '视频', 'knowledge-graph': '图谱',
  }
  return names[type] || type
}

function getTypeColor(type: string): string {
  const colors: Record<string, string> = {
    document: '#3b82f6', video: '#ef4444', exercise: '#22c55e', code: '#c084fc', mindmap: '#f59e0b', 'knowledge-graph': '#06b6d4',
  }
  return colors[type] || '#6b7280'
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString()
}

async function viewItem(item: ResourceItem) {
  selectedItem.value = item
  if (!item.content) {
    try {
      const res = await getContent(item.id)
      if (res.success && (res as any).data?.content) {
        selectedItem.value = { ...item, content: (res as any).data.content }
      }
    } catch (e) {
      console.warn('[Resource] 加载内容失败:', e)
    }
  }
}

function deleteItem(id: string) {
  resourceStore.removeResource(id)
  if (selectedItem.value?.id === id) {
    selectedItem.value = null
  }
}

function clearAllHistory() {
  resourceStore.clearAllResources()
  selectedItem.value = null
}

function markComplete(item: ResourceItem) {
  resourceStore.completeResource(item.id)
  item.status = 'completed'
  message.success(`已完成「${item.title}」，画像已更新！`)
}
</script>

<style lang="less" scoped>
.history-view {
  height: 100%;
  padding: 16px;
  background: transparent;
  overflow-y: auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
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

.history-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.history-desc {
  font-size: 12px;
  color: #475569;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.history-stats {
  display: flex;
  gap: 16px;
  padding: 10px 14px;
  margin-bottom: 14px;
  background: transparent;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  backdrop-filter: blur(16px) saturate(1.3);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon { font-size: 14px; }
.stat-value { font-size: 14px; font-weight: 600; color: #1e293b; }
.stat-label { font-size: 12px; color: #64748b; }

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: transparent;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  backdrop-filter: blur(16px) saturate(1.3);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  transition: all 0.2s;

  &:hover {
    background: rgba(37, 99, 235, 0.04);
    border-color: rgba(37, 99, 235, 0.2);
  }
}

.item-icon { font-size: 20px; }

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.item-type { font-size: 11px; color: #64748b; }
.item-time { font-size: 11px; color: #94a3b8; }

.ai-badge {
  background: rgba(0, 207, 232, 0.1);
  border-radius: 3px;
  padding: 1px 4px;
  color: #00CFE8;
  font-size: 10px;
}

.done-badge {
  background: rgba(34, 197, 94, 0.1);
  border-radius: 3px;
  padding: 1px 4px;
  color: #22c55e;
  font-size: 10px;
}

.item-actions {
  display: flex;
  gap: 4px;
}

.history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-text { font-size: 16px; font-weight: 500; color: #1e293b; margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #64748b; }

/* ===== 详情弹窗 ===== */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.detail-panel {
  width: 640px;
  max-height: 80vh;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 20px 60px rgba(37, 99, 235, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
}

.detail-type-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.detail-title {
  flex: 1;
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.detail-close:hover { color: #1e293b; background: rgba(37, 99, 235, 0.04); }

.detail-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

.detail-video {
  margin-bottom: 12px;
}

.detail-content {
  color: #334155;
  font-size: 14px;
  line-height: 1.7;

  :deep(p) { margin: 6px 0; }
  :deep(strong) { color: #1e293b; }
  :deep(code) {
    background: rgba(37, 99, 235, 0.06);
    color: #2563eb;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 12px;
  }
  :deep(pre) {
    background: #1e293b;
    color: #e2e8f0;
    padding: 10px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 12px;
  }
  :deep(pre code) { background: none; color: inherit; padding: 0; }
  :deep(blockquote) {
    border-left: 3px solid #2563eb;
    margin: 6px 0;
    padding: 6px 12px;
    background: rgba(37, 99, 235, 0.03);
    color: #475569;
  }
}

.detail-empty {
  text-align: center;
  padding: 30px;
  color: #94a3b8;
  font-size: 13px;
}

.detail-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid rgba(37, 99, 235, 0.08);
}

.detail-time { font-size: 11px; color: #94a3b8; }

.detail-complete-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid rgba(34, 197, 94, 0.2);
  background: rgba(34, 197, 94, 0.06);
  color: #22c55e;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.detail-complete-btn:hover { background: rgba(34, 197, 94, 0.12); }

.detail-done {
  font-size: 12px;
  color: #22c55e;
}
</style>
