<template>
  <span class="quality-badge" :class="levelClass" :title="tooltip">
    <span class="quality-icon">{{ icon }}</span>
    <span class="quality-level">{{ quality.level }}</span>
    <span class="quality-score">{{ quality.score }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface QualityInfo {
  score: number
  level: string
  dimensions: string[]
}

const props = defineProps<{ quality: QualityInfo }>()

const levelClass = computed(() => {
  switch (props.quality.level) {
    case '优质': return 'level-excellent'
    case '良好': return 'level-good'
    case '基础': return 'level-basic'
    default: return 'level-pending'
  }
})

const icon = computed(() => {
  switch (props.quality.level) {
    case '优质': return '💎'
    case '良好': return '✨'
    case '基础': return '📋'
    default: return '📝'
  }
})

const tooltip = computed(() => {
  return `质量评分: ${props.quality.score}/100\n评估维度: ${props.quality.dimensions.join('、') || '无'}`
})
</script>

<style lang="less" scoped>
.quality-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: help;

  &.level-excellent {
    background: rgba(16, 185, 129, 0.12);
    color: #059669;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }
  &.level-good {
    background: rgba(37, 99, 235, 0.1);
    color: #2563eb;
    border: 1px solid rgba(37, 99, 235, 0.2);
  }
  &.level-basic {
    background: rgba(245, 158, 11, 0.1);
    color: #d97706;
    border: 1px solid rgba(245, 158, 11, 0.2);
  }
  &.level-pending {
    background: rgba(148, 163, 184, 0.1);
    color: #64748b;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }
}
.quality-icon { font-size: 10px; }
.quality-score {
  font-size: 10px;
  opacity: 0.8;
  font-weight: 700;
}
</style>
