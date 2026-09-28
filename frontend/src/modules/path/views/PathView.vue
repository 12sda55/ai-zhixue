<template>
  <div class="path-view">
    <!-- 头部 -->
    <div class="path-header">
      <div class="header-left">
        <span class="header-icon">🗺️</span>
        <div class="header-info">
          <div class="header-title">学习路径</div>
          <div v-if="store.hasPath" class="header-sub">
            {{ store.stages.length }} 阶段 · {{ store.totalDays }} 天 · 进度 {{ store.totalProgress }}%
          </div>
          <div v-else class="header-sub">基于画像生成个性化学习路径</div>
        </div>
      </div>
      <div class="header-actions">
        <button v-if="store.hasPath && !store.isEditing" class="action-btn edit"
                aria-label="编辑学习路径" @click="store.startEditing()">
          ✏️ 编辑
        </button>
        <button v-if="store.hasPath" class="action-btn regen"
                aria-label="重新生成学习路径" @click="store.generatePath()">
          🔄 重新生成
        </button>
      </div>
    </div>

    <!-- Diff 提示 -->
    <StageDiffIndicator
      v-if="store.pathDiff"
      :diff="store.pathDiff"
      @dismiss="store.clearDiff()"
    />

    <!-- 当前活动路径 + 历史路径归档 -->
    <div class="archive-section">
      <!-- 当前路径 -->
      <div v-if="store.hasPath" class="current-path-info">
        <div class="current-left">
          <span class="current-label">当前路径</span>
          <span class="current-name">{{ store.pathSummary || store.stages[0]?.title || '学习路径' }}</span>
          <span class="current-meta">{{ store.stages.length }} 阶段</span>
        </div>
        <button class="archive-btn delete" @click="handleClearCurrent">清空</button>
      </div>

      <!-- 历史归档 -->
      <div v-if="store.pathArchives.length > 0">
        <div class="archive-header" @click="showArchives = !showArchives">
          <span class="archive-title">历史路径 ({{ store.pathArchives.length }})</span>
          <span class="archive-arrow">{{ showArchives ? '▾' : '▸' }}</span>
        </div>
        <div v-if="showArchives" class="archive-list">
          <div v-for="archive in store.pathArchives" :key="archive.id" class="archive-item">
            <div class="archive-info">
              <div class="archive-name">{{ archive.name }}</div>
              <div class="archive-meta">{{ archive.stages.length }} 阶段 · {{ formatDate(archive.createdAt) }}</div>
            </div>
            <div class="archive-actions">
              <button class="archive-btn switch" @click="store.switchToPath(archive.id)">切换</button>
              <button class="archive-btn delete" @click="store.deleteArchive(archive.id)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑工具栏 -->
    <PathEditToolbar
      v-if="store.isEditing"
      @add-stage="showAddStage = true"
      @save="store.saveEditing()"
      @cancel="store.cancelEditing()"
    />

    <!-- 生成中 / 空状态 -->
    <PathGenerator
      v-if="!store.hasPath || store.generationStatus === 'generating'"
      :status="store.generationStatus"
      :progress="store.generationProgress"
      :error="store.generationError"
      @generate="store.generatePath()"
      @cancel="store.cancelGeneration()"
    />

    <!-- 路径时间线 -->
    <div v-else-if="store.hasPath" class="path-timeline">
      <DraggableStages
        :stages="store.stages"
        :is-editing="store.isEditing"
        @reorder="store.reorderStages"
      >
        <template #default="{ stage }">
          <StageCard
            :stage="stage"
            :expanded="expandedStageId === stage.id"
            :is-editing="store.isEditing"
            @toggle="toggleExpand(stage.id)"
            @toggle-resource="openLearningModal"
            @update-days="store.updateSuggestedDays"
            @add-resource="openResourceModal"
            @remove-resource="store.removeResource"
            @remove-stage="store.removeStage"
          />
        </template>
      </DraggableStages>
    </div>

    <!-- 添加阶段弹窗 -->
    <Teleport to="body" :disabled="!isMounted">
      <Transition name="modal">
        <div v-if="showAddStage && isMounted" class="modal-overlay" @click.self="showAddStage = false">
          <div class="modal-box" role="dialog" aria-labelledby="modal-title">
            <div class="modal-header">
              <span id="modal-title" class="modal-title">添加学习阶段</span>
              <button class="modal-close" aria-label="关闭弹窗" @click="showAddStage = false">✕</button>
            </div>
            <div class="modal-body">
              <div class="form-group">
                <label for="stage-title" class="form-label">阶段标题</label>
                <input id="stage-title" name="stageTitle" v-model="newStageTitle"
                       class="form-input" placeholder="如：高级树结构"
                       @keyup.enter="handleAddStage" />
              </div>
              <div class="form-group">
                <label for="stage-days" class="form-label">建议天数</label>
                <div class="days-picker">
                  <button class="days-btn" aria-label="减少天数"
                          @click="newStageDays = Math.max(1, newStageDays - 1)">−</button>
                  <span id="stage-days" class="days-val">{{ newStageDays }}</span>
                  <button class="days-btn" aria-label="增加天数"
                          @click="newStageDays = Math.min(30, newStageDays + 1)">+</button>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-cancel" aria-label="取消添加" @click="showAddStage = false">取消</button>
              <button class="btn-confirm" :disabled="!newStageTitle.trim()"
                      aria-label="确认添加" @click="handleAddStage">添加</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 添加资源弹窗 -->
    <ResourceEditModal
      :visible="showResourceModal"
      @close="showResourceModal = false"
      @confirm="handleAddResource"
    />

    <!-- 学习弹窗 -->
    <ResourceLearningModal
      :visible="showLearningModal"
      :resource="learningResource"
      :stage-id="learningStageId"
      @close="showLearningModal = false"
      @complete="handleLearningComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { ResourceType, PathResource } from '../../../shared/types'
import { usePathStore } from '../stores/pathStore'
import PathGenerator from '../components/PathGenerator.vue'

// isMounted 状态，用于防止 Teleport 在 DOM 未准备好时渲染
const isMounted = ref(false)
import StageCard from '../components/StageCard.vue'
import PathEditToolbar from '../components/PathEditToolbar.vue'
import DraggableStages from '../components/DraggableStages.vue'
import ResourceEditModal from '../components/ResourceEditModal.vue'
import ResourceLearningModal from '../components/ResourceLearningModal.vue'
import StageDiffIndicator from '../components/StageDiffIndicator.vue'

const store = usePathStore()

const expandedStageId = ref<string | null>(null)
const showArchives = ref(false)
const showAddStage = ref(false)
const newStageTitle = ref('')
const newStageDays = ref(7)
const showResourceModal = ref(false)
const resourceTargetStageId = ref('')

// 学习弹窗状态
const showLearningModal = ref(false)
const learningResource = ref<PathResource | null>(null)
const learningStageId = ref('')

function toggleExpand(stageId: string) {
  expandedStageId.value = expandedStageId.value === stageId ? null : stageId
}

// 打开学习弹窗
function openLearningModal(stageId: string, resourceId: string) {
  const stage = store.stages.find(s => s.id === stageId)
  if (!stage) return
  const resource = stage.resources.find(r => r.id === resourceId)
  if (!resource) return
  
  learningStageId.value = stageId
  learningResource.value = resource
  showLearningModal.value = true
}

// 处理学习完成
function handleLearningComplete(stageId: string, resourceId: string) {
  store.completeResource(stageId, resourceId)
  showLearningModal.value = false
  learningResource.value = null
}

function openResourceModal(stageId: string) {
  resourceTargetStageId.value = stageId
  showResourceModal.value = true
}

function handleAddResource(type: ResourceType, name: string) {
  store.addResource(resourceTargetStageId.value, type, name)
  showResourceModal.value = false
}

function handleAddStage() {
  if (!newStageTitle.value.trim()) return
  store.addStage(newStageTitle.value.trim(), newStageDays.value)
  newStageTitle.value = ''
  newStageDays.value = 7
  showAddStage.value = false
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function handleClearCurrent() {
  if (!store.hasPath) return
  if (window.confirm('确定清空当前路径吗？清空后将归档到历史路径。')) {
    try {
      store.archiveCurrentPath()
    } catch (e) {
      console.error('[Path] 归档失败', e)
    }
    setTimeout(() => {
      try {
        store.resetPath()
      } catch (e) {
        console.error('[Path] 重置路径失败', e)
      }
    }, 50)
  }
}

onMounted(() => {
  isMounted.value = true
  // 启动画像监听，路径会在画像稳定后自动更新
  store.startProfileWatch()
})

onUnmounted(() => {
  store.stopProfileWatch()
})
</script>

<style lang="less" scoped>
/* CSS 兼容性修复 */
.text-size-adjust-100 {
  -webkit-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
  text-size-adjust: 100%;
}

.path-view {
  height: 100%;
  padding: 24px;
  overflow-y: auto;
  background: transparent;
  .text-size-adjust-100();

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 3px; }
}

/* ===== 头部 ===== */
.path-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon { font-size: 28px; }

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.header-sub {
  font-size: 13px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &.edit {
    border: 1px solid rgba(37, 99, 235, 0.1);
    background: transparent;
    backdrop-filter: blur(16px) saturate(1.3);
    color: #475569;
    &:hover { background: transparent; color: #1e293b; }
  }
  &.regen {
    border: 1px solid rgba(37, 99, 235, 0.2);
    background: rgba(37, 99, 235, 0.08);
    color: #2563eb;
    &:hover { background: rgba(37, 99, 235, 0.15); }
  }
}

/* ===== 时间线 ===== */
.path-timeline {
  max-width: 720px;
}

/* ===== 归档列表 ===== */
.archive-section {
  max-width: 720px;
  margin-bottom: 16px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.08);
  overflow: hidden;
}

.current-path-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(6, 182, 212, 0.04));
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
}

.current-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.current-label {
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(37, 99, 235, 0.1);
  flex-shrink: 0;
}

.current-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.current-meta {
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}

.archive-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  background: rgba(37, 99, 235, 0.03);
  transition: background 0.15s;
  &:hover { background: rgba(37, 99, 235, 0.06); }
}

.archive-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.archive-arrow {
  font-size: 14px;
  color: #94a3b8;
}

.archive-list {
  padding: 4px 0;
}

.archive-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-top: 1px solid rgba(37, 99, 235, 0.04);
  transition: background 0.15s;
  &:hover { background: rgba(37, 99, 235, 0.03); }
}

.archive-info {
  flex: 1;
  min-width: 0;
}

.archive-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.archive-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.archive-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  margin-left: 12px;
}

.archive-btn {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
  &.switch {
    border-color: rgba(37, 99, 235, 0.2);
    background: rgba(37, 99, 235, 0.06);
    color: #2563eb;
    &:hover { background: rgba(37, 99, 235, 0.12); }
  }
  &.delete {
    border-color: rgba(239, 68, 68, 0.15);
    background: transparent;
    color: #ef4444;
    &:hover { background: rgba(239, 68, 68, 0.06); }
  }
}

/* ===== 弹窗通用 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

.modal-box {
  width: 400px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.modal-close {
  font-size: 16px;
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 6px;
  &:hover { color: #1e293b; background: rgba(37, 99, 235, 0.08); }
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.form-input {
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  color: #1e293b;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  &::placeholder { color: #94a3b8; }
  &:focus { border-color: #2563eb; background: transparent; }
}

.days-picker {
  display: flex;
  align-items: center;
  gap: 14px;
}

.days-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  color: #475569;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  &:hover { background: rgba(37, 99, 235, 0.08); color: #1e293b; }
}

.days-val {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  min-width: 36px;
  text-align: center;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
}

.btn-cancel, .btn-confirm {
  padding: 8px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  color: #475569;
  &:hover { background: rgba(37, 99, 235, 0.08); }
}

.btn-confirm {
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #FFFFFF;
  &:hover { box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
