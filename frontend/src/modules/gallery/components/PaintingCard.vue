<template>
  <div class="painting-card" @click="handleClick">
    <!-- 雷达图预览 -->
    <div class="card-radar">
      <MiniRadarChart :dimensions="dimensions" :size="160" :show-axis-name="false" />
    </div>

    <!-- 信息区域 -->
    <div class="card-info">
      <div class="card-title-row">
        <h3 class="card-title">{{ snapshot.title }}</h3>
        <span v-if="snapshot.subject" class="card-subject">{{ snapshot.subject }}</span>
      </div>
      <p class="card-desc">{{ snapshot.description || '暂无描述' }}</p>
      <div class="card-meta">
        <span class="card-score">总分 {{ snapshot.totalScore }}</span>
        <span class="card-date">{{ formatDate(snapshot.createdAt) }}</span>
      </div>
    </div>

    <!-- 悬浮操作 -->
    <div class="card-actions">
      <button class="action-btn action-delete" @click.stop="handleDelete" title="删除">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4h9.34z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RadarSnapshot } from '../../../shared/types'
import MiniRadarChart from './MiniRadarChart.vue'

const props = defineProps<{
  snapshot: RadarSnapshot
}>()

const emit = defineEmits<{
  click: []
  delete: [id: string]
}>()

const dimensions = computed(() => props.snapshot.dimensions || [])

function handleClick() {
  emit('click')
}

function handleDelete() {
  emit('delete', props.snapshot.id)
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style lang="less" scoped>
.painting-card {
  position: relative;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(37, 99, 235, 0.1);
    border-color: rgba(37, 99, 235, 0.2);

    .card-actions {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

.card-radar {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 14px;
}

.card-info {
  position: relative;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.card-subject {
  font-size: 10px;
  font-weight: 600;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}

.card-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 10px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-score {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
}

.card-date {
  font-size: 12px;
  color: #94a3b8;
}

// 悬浮操作按钮
.card-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 6px;
  opacity: 0;
  transform: translateY(-4px);
  transition: all 0.2s ease;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-delete {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;

  &:hover {
    background: rgba(239, 68, 68, 0.2);
    transform: scale(1.1);
  }
}
</style>
