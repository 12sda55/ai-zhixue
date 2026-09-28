<template>
  <div class="draggable-stages">
    <div
      v-for="(stage, index) in stages"
      :key="stage.id"
      class="drag-item"
      :class="{ dragging: dragIndex === index, 'drag-over': dropIndex === index && dragIndex !== index }"
      :draggable="isEditing"
      @dragstart="onDragStart(index, $event)"
      @dragover.prevent="onDragOver(index)"
      @dragleave="onDragLeave"
      @drop="onDrop(index)"
      @dragend="onDragEnd"
    >
      <!-- 拖拽手柄（编辑模式） -->
      <div v-if="isEditing" class="drag-handle">
        <span class="handle-bar" />
        <span class="handle-bar" />
        <span class="handle-bar" />
      </div>

      <!-- 上下移动按钮（编辑模式） -->
      <div v-if="isEditing" class="move-buttons">
        <button
          class="move-btn"
          :disabled="index === 0"
          @click.stop="$emit('reorder', index, index - 1)"
        >↑</button>
        <button
          class="move-btn"
          :disabled="index === stages.length - 1"
          @click.stop="$emit('reorder', index, index + 1)"
        >↓</button>
      </div>

      <!-- 阶段内容插槽 -->
      <div class="drag-content">
        <slot :stage="stage" :index="index" />
      </div>

      <!-- 连接线 -->
      <div v-if="index < stages.length - 1" class="connector" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { PathStageExtended } from '../../../shared/types'

defineProps<{
  stages: PathStageExtended[]
  isEditing: boolean
}>()

defineEmits<{
  reorder: [fromIndex: number, toIndex: number]
}>()

const dragIndex = ref<number | null>(null)
const dropIndex = ref<number | null>(null)

function onDragStart(index: number, event: DragEvent) {
  dragIndex.value = index
  event.dataTransfer!.effectAllowed = 'move'
}

function onDragOver(index: number) {
  dropIndex.value = index
}

function onDragLeave() {
  dropIndex.value = null
}

function onDrop(index: number) {
  if (dragIndex.value !== null && dragIndex.value !== index) {
    // emit is handled by parent
  }
  dropIndex.value = null
  dragIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dropIndex.value = null
}
</script>

<style lang="less" scoped>
.draggable-stages {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.drag-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 0;
  transition: opacity 0.2s;

  &.dragging { opacity: 0.4; }
  &.drag-over { border-top: 2px solid #a78bfa; }
}

.drag-handle {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 4px;
  cursor: grab;
  opacity: 0.4;
  transition: opacity 0.2s;

  &:hover { opacity: 0.8; }
  &:active { cursor: grabbing; }
}

.handle-bar {
  width: 14px;
  height: 2px;
  border-radius: 1px;
  background: #5a7a8a;
}

.move-buttons {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.move-btn {
  width: 20px;
  height: 16px;
  border-radius: 3px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  background: rgba(167, 139, 250, 0.06);
  color: #a78bfa;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover:not(:disabled) { background: rgba(167, 139, 250, 0.12); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.drag-content {
  flex: 1;
  min-width: 0;
}

.connector {
  position: absolute;
  left: 22px;
  bottom: -4px;
  width: 2px;
  height: 8px;
  background: rgba(0, 212, 255, 0.15);
  border-radius: 1px;
}
</style>
