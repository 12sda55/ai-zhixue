<template>
  <Teleport to="body" :disabled="!isMounted">
    <Transition name="modal">
      <div v-if="visible && isMounted" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-box" role="dialog" aria-labelledby="resource-modal-title">
          <div class="modal-header">
            <span id="resource-modal-title" class="modal-title">添加学习资源</span>
            <button class="modal-close" aria-label="关闭弹窗" @click="$emit('close')">✕</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <span class="form-label">资源类型</span>
              <div class="type-grid" role="radiogroup" aria-label="选择资源类型">
                <button
                  v-for="(item, key) in RESOURCE_TYPE_MAP"
                  :key="key"
                  class="type-btn"
                  :class="{ active: selectedType === key }"
                  :aria-pressed="selectedType === key"
                  @click="selectedType = key as ResourceType"
                >
                  <span class="type-icon">{{ item.icon }}</span>
                  <span class="type-name">{{ item.label }}</span>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="resource-name" class="form-label">资源名称</label>
              <input
                id="resource-name"
                name="resourceName"
                v-model="resourceName"
                class="form-input"
                placeholder="输入资源名称"
                @keyup.enter="handleAdd"
              />
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-cancel" aria-label="取消添加" @click="$emit('close')">取消</button>
            <button class="btn-confirm" :disabled="!resourceName.trim()" aria-label="确认添加" @click="handleAdd">添加</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { ResourceType } from '../../../shared/types'
import { RESOURCE_TYPE_MAP } from '../../../shared/utils/constants'

// isMounted 状态，用于防止 Teleport 在 DOM 未准备好时渲染
const isMounted = ref(false)

onMounted(() => {
  isMounted.value = true
})

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [type: ResourceType, name: string]
}>()

const selectedType = ref<ResourceType>('document')
const resourceName = ref('')

function handleAdd() {
  const name = resourceName.value.trim()
  if (!name) return
  emit('confirm', selectedType.value, name)
  resourceName.value = ''
}
</script>

<style lang="less" scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

.modal-box {
  width: 360px;
  background: #111730;
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 14px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.08);
}

.modal-title {
  font-size: 14px;
  font-weight: 600;
  color: #e8f4fd;
}

.modal-close {
  font-size: 14px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: #5a7a8a;
  cursor: pointer;
  &:hover { color: #e8f4fd; }
}

.modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 11px;
  font-weight: 600;
  color: #5a7a8a;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 4px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s;

  &:hover { border-color: rgba(0, 212, 255, 0.2); }
  &.active {
    border-color: rgba(0, 212, 255, 0.4);
    background: rgba(0, 212, 255, 0.08);
  }
}

.type-icon { font-size: 16px; }
.type-name { font-size: 9px; color: #5a7a8a; }
.type-btn.active .type-name { color: #00d4ff; }

.form-input {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.12);
  background: rgba(0, 0, 0, 0.2);
  color: #e8f4fd;
  font-size: 13px;
  outline: none;

  &::placeholder { color: #3a5a6a; }
  &:focus { border-color: rgba(0, 212, 255, 0.3); }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 212, 255, 0.08);
}

.btn-cancel, .btn-confirm {
  padding: 6px 18px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: #5a7a8a;
  &:hover { color: #e8f4fd; }
}

.btn-confirm {
  border: 1px solid rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
  &:hover { background: rgba(0, 212, 255, 0.18); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
