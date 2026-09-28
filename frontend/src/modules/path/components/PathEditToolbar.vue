<template>
  <div class="edit-toolbar">
    <div class="toolbar-left">
      <span class="toolbar-icon">✏️</span>
      <span class="toolbar-label">编辑模式</span>
    </div>
    <div class="toolbar-actions">
      <button class="tb-btn add" aria-label="添加学习阶段" @click="$emit('addStage')">
        <span class="tb-icon">+</span> 添加阶段
      </button>
      <button class="tb-btn save" aria-label="保存修改" @click="$emit('save')">保存</button>
      <button class="tb-btn cancel" aria-label="取消编辑" @click="$emit('cancel')">取消</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  addStage: []
  save: []
  cancel: []
}>()
</script>

<style lang="less" scoped>
.edit-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: 10px;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-icon { font-size: 14px; }
.toolbar-label { font-size: 12px; font-weight: 600; color: #f59e0b; }

.toolbar-actions {
  display: flex;
  gap: 6px;
}

.tb-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid;

  &.add {
    border-color: rgba(167, 139, 250, 0.3);
    background: rgba(167, 139, 250, 0.08);
    color: #a78bfa;
    &:hover { background: rgba(167, 139, 250, 0.15); }
  }
  &.save {
    border-color: rgba(52, 211, 153, 0.3);
    background: rgba(52, 211, 153, 0.08);
    color: #34d399;
    &:hover { background: rgba(52, 211, 153, 0.15); }
  }
  &.cancel {
    border-color: rgba(255, 255, 255, 0.1);
    background: transparent;
    color: #5a7a8a;
    &:hover { color: #e8f4fd; border-color: rgba(255, 255, 255, 0.2); }
  }
}

.tb-icon { font-size: 13px; }
</style>
