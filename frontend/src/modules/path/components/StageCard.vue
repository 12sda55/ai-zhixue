<template>
  <div class="stage-card" :class="[stage.status, { expanded, editing: isEditing }]">
    <!-- 折叠状态：标题行 -->
    <div class="stage-header" @click="$emit('toggle')">
      <div class="stage-left">
        <span class="status-dot" :class="stage.status" />
        <span class="stage-title">{{ stage.title }}</span>
      </div>
      <div class="stage-right">
        <span class="stage-days">{{ stage.suggestedDays }}天</span>
        <span class="reason-tag" :class="stage.reasonType">{{ reasonLabel }}</span>
        <span class="expand-icon" :class="{ rotated: expanded }">▾</span>
      </div>
    </div>

    <!-- 展开状态：详情 -->
    <Transition name="slide">
      <div v-if="expanded" class="stage-body">
        <!-- 推荐理由 -->
        <div class="detail-row">
          <span class="detail-label">推荐理由</span>
          <span class="detail-value">{{ stage.reason }}</span>
        </div>

        <!-- 学习建议 -->
        <div v-if="stage.learningTips" class="detail-row">
          <span class="detail-label">学习建议</span>
          <span class="detail-value tips">{{ stage.learningTips }}</span>
        </div>

        <!-- 天数编辑 -->
        <div class="detail-row">
          <span class="detail-label">建议天数</span>
          <div v-if="isEditing" class="days-editor">
            <button class="days-btn" @click.stop="$emit('updateDays', stage.id, Math.max(1, stage.suggestedDays - 1))">−</button>
            <span class="days-val">{{ stage.suggestedDays }}</span>
            <button class="days-btn" @click.stop="$emit('updateDays', stage.id, Math.min(30, stage.suggestedDays + 1))">+</button>
          </div>
          <span v-else class="detail-value">{{ stage.suggestedDays }} 天</span>
        </div>

        <!-- 进度条 -->
        <div class="progress-section">
          <div class="progress-header">
            <span class="progress-label">进度</span>
            <span class="progress-val">{{ stage.progress }}%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" :style="{ width: stage.progress + '%' }" />
          </div>
        </div>

        <!-- 资源列表 -->
        <div class="resource-section">
          <div class="section-head">
            <span class="section-title">学习资源</span>
            <button v-if="isEditing" class="add-res-btn" @click.stop="$emit('addResource', stage.id)">+ 添加</button>
          </div>
          <div class="resource-list">
            <div
              v-for="res in stage.resources"
              :key="res.id"
              class="resource-item"
              :class="res.status"
              @click.stop="!isEditing && $emit('toggleResource', stage.id, res.id)"
            >
              <span class="res-icon">{{ typeIcon(res.type) }}</span>
              <span class="res-name">{{ res.name }}</span>
              <span class="res-status">{{ resStatusLabel(res.status) }}</span>
              <button
                v-if="isEditing"
                class="res-remove"
                @click.stop="$emit('removeResource', stage.id, res.id)"
              >✕</button>
            </div>
            <div v-if="!stage.resources.length" class="no-resource">
              {{ isEditing ? '暂无资源，点击上方添加' : '暂无资源' }}
            </div>
          </div>
        </div>

        <!-- 编辑模式：删除阶段 -->
        <div v-if="isEditing" class="stage-edit-actions">
          <button class="remove-stage-btn" @click.stop="$emit('removeStage', stage.id)">删除此阶段</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PathStageExtended } from '../../../shared/types'
import { RESOURCE_TYPE_MAP } from '../../../shared/utils/constants'

const props = defineProps<{
  stage: PathStageExtended
  expanded: boolean
  isEditing: boolean
}>()

defineEmits<{
  toggle: []
  toggleResource: [stageId: string, resourceId: string]
  updateDays: [stageId: string, days: number]
  addResource: [stageId: string]
  removeResource: [stageId: string, resourceId: string]
  removeStage: [stageId: string]
}>()

const reasonLabel = computed(() => {
  const map: Record<string, string> = { foundation: '基础', weakness: '薄弱', advanced: '进阶' }
  return map[props.stage.reasonType] || '基础'
})

function typeIcon(type: string): string {
  const item = RESOURCE_TYPE_MAP[type as keyof typeof RESOURCE_TYPE_MAP]
  return item?.icon || '📄'
}

function resStatusLabel(status: string): string {
  const map: Record<string, string> = { pending: '待开始', active: '进行中', completed: '已完成' }
  return map[status] || ''
}
</script>

<style lang="less" scoped>
.stage-card {
  background: transparent;
  border: 1px solid #EBE9F1;
  border-radius: 12px;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &:hover { border-color: #D8D6DE; box-shadow: 0 4px 12px rgba(76, 78, 100, 0.08); }
  &.active { border-color: #00CFE8; box-shadow: 0 4px 12px rgba(0, 207, 232, 0.15); }
  &.completed { border-color: #28C76F; box-shadow: 0 2px 8px rgba(40, 199, 111, 0.1); }
  &.editing { border-color: #7367F0; box-shadow: 0 4px 12px rgba(115, 103, 240, 0.15); }
}

.stage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
}

.stage-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;

  &.pending { background: #5a7a8a; }
  &.active { background: #00d4ff; box-shadow: 0 0 6px rgba(0, 212, 255, 0.5); }
  &.completed { background: #34d399; }
}

.stage-title {
  font-size: 14px;
  font-weight: 600;
  color: #2F2B3D;
}

.stage-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-days {
  font-size: 12px;
  color: #6E6B7B;
  font-weight: 500;
}

.reason-tag {
  font-size: 9px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;

  &.foundation { background: rgba(0, 212, 255, 0.1); color: #00d4ff; }
  &.weakness { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
  &.advanced { background: rgba(167, 139, 250, 0.1); color: #a78bfa; }
}

.expand-icon {
  font-size: 12px;
  color: #A8AAAE;
  transition: transform 0.3s;

  &.rotated { transform: rotate(180deg); }
}

/* ===== 展开详情 ===== */
.stage-body {
  padding: 0 14px 14px;
  border-top: 1px solid #F3F2F7;
  margin-top: 0;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #F3F2F7;
}

.detail-label {
  font-size: 12px;
  color: #A8AAAE;
  width: 70px;
  flex-shrink: 0;
  padding-top: 1px;
  font-weight: 500;
}

.detail-value {
  font-size: 13px;
  color: #5E5873;
  flex: 1;
  line-height: 1.5;

  &.tips {
    color: #7367F0;
    font-style: italic;
  }
}

.days-editor {
  display: flex;
  align-items: center;
  gap: 6px;
}

.days-btn {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.08);
  color: #f59e0b;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover { background: rgba(245, 158, 11, 0.15); }
}

.days-val {
  font-size: 14px;
  font-weight: 600;
  color: #2F2B3D;
  min-width: 24px;
  text-align: center;
}

/* ===== 进度 ===== */
.progress-section {
  padding: 10px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.progress-label {
  font-size: 12px;
  color: #A8AAAE;
  font-weight: 500;
}

.progress-val {
  font-size: 12px;
  font-weight: 600;
  color: #00CFE8;
}

.progress-bar-bg {
  height: 6px;
  border-radius: 4px;
  background: rgba(37, 99, 235, 0.06);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #00CFE8, #6FE4F0);
  transition: width 0.5s ease;
}

/* ===== 资源 ===== */
.resource-section {
  padding: 10px 0;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #2F2B3D;
}

.add-res-btn {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(115, 103, 240, 0.3);
  background: rgba(115, 103, 240, 0.08);
  color: #7367F0;
  cursor: pointer;
  font-weight: 500;

  &:hover { background: rgba(115, 103, 240, 0.15); }
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.08);
  cursor: pointer;
  transition: all 0.2s;

  &:hover { background: rgba(37, 99, 235, 0.08); border-color: rgba(37, 99, 235, 0.15); }

  &.completed { opacity: 0.7; }
  &.completed .res-name { text-decoration: line-through; }
}

.res-icon { font-size: 14px; }
.res-name { flex: 1; font-size: 13px; color: #5E5873; }

.res-status {
  font-size: 11px;
  color: #A8AAAE;
  font-weight: 500;
}

.resource-item.active .res-status { color: #00CFE8; }
.resource-item.completed .res-status { color: #28C76F; }

.res-remove {
  font-size: 10px;
  padding: 2px 4px;
  border: none;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-radius: 3px;
  cursor: pointer;

  &:hover { background: rgba(239, 68, 68, 0.2); }
}

.no-resource {
  font-size: 11px;
  color: #5a7a8a;
  padding: 8px;
  text-align: center;
}

.stage-edit-actions {
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}

.remove-stage-btn {
  font-size: 11px;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.06);
  color: #ef4444;
  cursor: pointer;

  &:hover { background: rgba(239, 68, 68, 0.12); }
}
</style>
