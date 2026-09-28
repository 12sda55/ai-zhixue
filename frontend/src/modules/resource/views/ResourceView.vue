<template>
  <div class="resource-view">
    <div class="resource-header">
      <div class="header-left">
        <div class="header-icon">📚</div>
        <div>
          <div class="header-title">资源中心</div>
          <div class="header-desc">AI 智能生成 · 紧扣画像 · 按需取用</div>
        </div>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" :disabled="isGenerating" @click="store.generateResources()">
          {{ isGenerating ? '生成中...' : '🔄 刷新资源' }}
        </button>
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input v-model="searchKeyword" placeholder="搜索资源..." class="search-input" />
        </div>
      </div>
    </div>

    <!-- 空状态：资源尚未生成 -->
    <div v-if="resources.length === 0 && !isGenerating" class="empty-state">
      <div class="empty-icon">📚</div>
      <div class="empty-title">暂无资源</div>
      <div class="empty-desc">完成画像采集后，启动智能体即可生成个性化学习资源</div>
      <button class="empty-btn" @click="router.push('/agent')">前往智能体面板 →</button>
    </div>

    <!-- 生成中状态 -->
    <div v-if="isGenerating" class="generating-state">
      <div class="gen-spinner"></div>
      <div class="gen-text">AI 正在生成资源...</div>
    </div>

    <!-- 筛选标签 -->
    <div v-if="resources.length > 0" class="filter-tabs">
      <button
        v-for="t in filterTypes"
        :key="t.key"
        class="filter-tab"
        :class="{ active: activeFilter === t.key }"
        @click="activeFilter = t.key"
      >{{ t.icon }} {{ t.label }} <span class="tab-count">{{ t.count }}</span></button>
    </div>

    <!-- 资源列表 -->
    <div v-if="filteredResources.length > 0" class="resource-grid">
      <ResourceCard
        v-for="item in filteredResources"
        :key="item.id"
        :item="item"
        @click="selectedItem = item"
        @update:item="onCardItemUpdate"
      />
    </div>

    <!-- 无搜索结果 -->
    <div v-if="resources.length > 0 && filteredResources.length === 0" class="no-result">
      没有找到匹配的资源
    </div>

    <!-- 资源详情弹窗 -->
    <div v-if="selectedItem" class="detail-overlay" @click.self="selectedItem = null">
      <div class="detail-panel">
        <ResourceDetail :resource="selectedItem" @update:resource="onResourceUpdate" />
        <div class="detail-actions">
          <button class="complete-btn" @click="handleCompleteResource(selectedItem)">
            ✅ 标记完成
          </button>
          <button class="close-btn" @click="selectedItem = null">✕ 关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceDetail from '../components/ResourceDetail.vue'
import { useResourceStore } from '../stores/resourceStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { sortByMatchScore } from '../../../shared/utils/matchScorer'
import type { ResourceItem } from '../../../shared/types'

const router = useRouter()
const store = useResourceStore()
const profileStore = useProfileStore()
const searchKeyword = ref('')
const activeFilter = ref('all')
const selectedItem = ref<ResourceItem | null>(null)

// 处理资源更新（视频生成完成后保存 URL）
function onResourceUpdate(updated: ResourceItem) {
  selectedItem.value = updated
  // 同步更新 store 中的资源
  const idx = store.resources.findIndex(r => r.id === updated.id)
  if (idx !== -1) {
    store.resources[idx] = updated
  }
}

// 处理卡片上的资源更新
function onCardItemUpdate(updated: ResourceItem) {
  const idx = store.resources.findIndex(r => r.id === updated.id)
  if (idx !== -1) {
    store.resources[idx] = updated
  }
  // 如果当前选中的是这个资源，也更新 selectedItem
  if (selectedItem.value?.id === updated.id) {
    selectedItem.value = updated
  }
}

const resources = computed(() => store.resources)
const isGenerating = computed(() => store.isGenerating)

const filterTypes = computed(() => [
  { key: 'all', label: '全部', icon: '📋', count: resources.value.length },
  { key: 'document', label: '文档', icon: '📄', count: resources.value.filter(r => r.type === 'document').length },
  { key: 'mindmap', label: '导图', icon: '🗺️', count: resources.value.filter(r => r.type === 'mindmap').length },
  { key: 'knowledge-graph', label: '图谱', icon: '🕸️', count: resources.value.filter(r => r.type === 'knowledge-graph').length },
  { key: 'exercise', label: '习题', icon: '📝', count: resources.value.filter(r => r.type === 'exercise').length },
  { key: 'code', label: '代码', icon: '💻', count: resources.value.filter(r => r.type === 'code').length },
  { key: 'video', label: '视频', icon: '🎬', count: resources.value.filter(r => r.type === 'video').length },
])

const filteredResources = computed(() => {
  let list = resources.value
  if (activeFilter.value !== 'all') {
    list = list.filter(r => r.type === activeFilter.value)
  }
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(r =>
      r.title.toLowerCase().includes(kw) ||
      r.module?.toLowerCase().includes(kw) ||
      r.description?.toLowerCase().includes(kw)
    )
  }
  // UX-3: 按画像匹配度排序（推荐资源优先展示）
  return sortByMatchScore(list, profileStore.profileData)
})

function handleCompleteResource(item: ResourceItem) {
  store.completeResource(item.id)
  selectedItem.value = null
  message.success(`已完成「${item.title}」，画像已更新！`)
}
</script>

<style lang="less" scoped>
.resource-view {
  padding: 16px;
  height: 100%;
  overflow: auto;
  background: transparent;
}

.resource-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.header-title { color: #1e293b; font-size: 16px; font-weight: 700; }
.header-desc { color: #475569; font-size: 12px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  color: #2563eb;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &:hover:not(:disabled) { background: transparent; border-color: rgba(37, 99, 235, 0.2); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.search-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 8px;
  padding: 6px 12px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.search-icon { font-size: 12px; }

.search-input {
  background: none;
  border: none;
  color: #1e293b;
  font-size: 12px;
  outline: none;
  width: 140px;
  &::placeholder { color: #94a3b8; }
}

/* ===== 空状态 ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-title { font-size: 18px; font-weight: 700; color: #1e293b; margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #475569; margin-bottom: 20px; max-width: 300px; }

.empty-btn {
  padding: 8px 20px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  color: #2563eb;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &:hover { background: transparent; border-color: rgba(37, 99, 235, 0.2); }
}

/* ===== 生成中 ===== */
.generating-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  margin-bottom: 14px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.gen-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(37, 99, 235, 0.2);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.gen-text { color: #2563eb; font-size: 13px; }

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 筛选标签 ===== */
.filter-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
  overflow-x: auto;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &:hover { background: transparent; }
  &.active {
    background: rgba(37, 99, 235, 0.08);
    border-color: rgba(37, 99, 235, 0.3);
    color: #2563eb;
  }
}

.tab-count {
  background: rgba(37, 99, 235, 0.08);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 10px;
  color: #2563eb;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.no-result {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 13px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

/* ===== 详情弹窗 ===== */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;  // 提高z-index确保全屏视频能正常显示
  backdrop-filter: blur(4px);
}

.detail-panel {
  width: 800px;  // 加宽以适应视频播放
  max-height: 85vh;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 16px;
  overflow: visible;  // 改为visible以支持全屏视频
  box-shadow: 0 10px 40px rgba(76, 78, 100, 0.15);

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 2px; }
}

.detail-actions {
  padding: 12px 16px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #FFFFFF;
}

.complete-btn {
  padding: 8px 20px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
  }
}

.close-btn {
  background: none;
  border: 1px solid rgba(37, 99, 235, 0.1);
  color: #475569;
  font-size: 12px;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;

  &:hover { color: #1e293b; border-color: rgba(37, 99, 235, 0.2); }
}
</style>
