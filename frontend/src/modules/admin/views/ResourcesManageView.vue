<template>
  <div class="resources-manage-view">
    <!-- 顶部操作栏 -->
    <div class="action-bar">
      <div class="search-area">
        <a-input v-model:value="searchKeyword" placeholder="搜索资源名称..." allow-clear>
          <template #prefix>
            <SvgIcon name="search" :size="16" />
          </template>
        </a-input>
        <a-select v-model:value="filterType" placeholder="资源类型" style="width: 120px" allow-clear>
          <a-select-option value="">全部类型</a-select-option>
          <a-select-option value="document">文档</a-select-option>
          <a-select-option value="mindmap">思维导图</a-select-option>
          <a-select-option value="video">视频</a-select-option>
          <a-select-option value="code">代码</a-select-option>
          <a-select-option value="exercise">练习题</a-select-option>
        </a-select>
      </div>
      <div class="action-buttons">
        <a-button type="primary" @click="showCreateModal">
          <template #icon><SvgIcon name="plus" :size="16" /></template>
          新建资源
        </a-button>
      </div>
    </div>

    <!-- 资源列表 -->
    <div class="resources-list">
      <div class="list-header">
        <span class="col-title">资源名称</span>
        <span class="col-type">类型</span>
        <span class="col-difficulty">难度</span>
        <span class="col-duration">时长</span>
        <span class="col-weak">薄弱点</span>
        <span class="col-date">创建时间</span>
        <span class="col-actions">操作</span>
      </div>
      <div class="list-body">
        <div v-for="resource in filteredResources" :key="resource.id" class="resource-row">
          <span class="col-title">
            <div class="resource-title">
              <SvgIcon :name="getResourceIcon(resource.type)" :size="18" />
              <span>{{ resource.title }}</span>
            </div>
            <div class="resource-desc">{{ resource.description || '暂无描述' }}</div>
          </span>
          <span class="col-type">
            <span class="type-tag" :class="resource.type">{{ getTypeName(resource.type) }}</span>
          </span>
          <span class="col-difficulty">
            <span class="difficulty-tag" :class="resource.difficulty">{{ getDifficultyName(resource.difficulty) }}</span>
          </span>
          <span class="col-duration">{{ resource.duration || '30分钟' }}</span>
          <span class="col-weak">
            <span v-if="resource.isWeakPoint" class="weak-tag">⭐ 薄弱点</span>
            <span v-else class="normal-tag">普通</span>
          </span>
          <span class="col-date">{{ resource.createdAt || '-' }}</span>
          <span class="col-actions">
            <a-button size="small" type="link" @click="showEditModal(resource)">编辑</a-button>
            <a-popconfirm title="确定删除此资源？" @confirm="handleDelete(resource.id)">
              <a-button size="small" type="link" danger>删除</a-button>
            </a-popconfirm>
          </span>
        </div>
        <div v-if="filteredResources.length === 0" class="empty-state">
          <SvgIcon name="file-x" :size="48" />
          <p>暂无资源数据</p>
        </div>
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEditing ? '编辑资源' : '新建资源'"
      width="600px"
      @ok="handleSubmit"
      @cancel="handleCancel"
    >
      <a-form :model="formData" :label-col="{ span: 4 }" :wrapper-col="{ span: 20 }">
        <a-form-item label="资源名称" required>
          <a-input v-model:value="formData.title" placeholder="请输入资源名称" />
        </a-form-item>
        <a-form-item label="资源描述">
          <a-textarea v-model:value="formData.description" placeholder="请输入资源描述" :rows="3" />
        </a-form-item>
        <a-form-item label="资源类型" required>
          <a-select v-model:value="formData.type" placeholder="选择资源类型">
            <a-select-option value="document">文档</a-select-option>
            <a-select-option value="mindmap">思维导图</a-select-option>
            <a-select-option value="video">视频</a-select-option>
            <a-select-option value="code">代码</a-select-option>
            <a-select-option value="exercise">练习题</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="难度等级">
          <a-select v-model:value="formData.difficulty" placeholder="选择难度">
            <a-select-option value="basic">基础</a-select-option>
            <a-select-option value="intermediate">中级</a-select-option>
            <a-select-option value="advanced">高级</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="学习时长">
          <a-input v-model:value="formData.duration" placeholder="如：30分钟" />
        </a-form-item>
        <a-form-item label="薄弱点标记">
          <a-switch v-model:checked="formData.isWeakPoint" />
          <span class="switch-label">{{ formData.isWeakPoint ? '标记为薄弱点资源' : '普通资源' }}</span>
        </a-form-item>
        <a-form-item label="资源内容">
          <a-textarea v-model:value="formData.content" placeholder="AI生成的资源内容（Markdown格式）" :rows="6" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { getResourceList, createResource, updateResource, deleteResource } from '../api/adminApi'
import SvgIcon from '../../../shared/components/SvgIcon.vue'

interface ResourceItem {
  id: string
  title: string
  description: string
  type: string
  difficulty: string
  duration: string
  isWeakPoint: boolean
  createdAt: string
}

const resources = ref<ResourceItem[]>([])
const searchKeyword = ref('')
const filterType = ref('')
const modalVisible = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const formData = ref({
  title: '',
  description: '',
  type: 'document',
  difficulty: 'basic',
  duration: '30分钟',
  isWeakPoint: false,
  content: ''
})

const filteredResources = computed(() => {
  return resources.value.filter(r => {
    const matchKeyword = !searchKeyword.value || r.title.includes(searchKeyword.value)
    const matchType = !filterType.value || r.type === filterType.value
    return matchKeyword && matchType
  })
})

function getResourceIcon(type: string) {
  const icons: Record<string, string> = {
    document: 'file-text',
    mindmap: 'git-branch',
    video: 'video',
    code: 'code',
    exercise: 'clipboard-list'
  }
  return icons[type] || 'file'
}

function getTypeName(type: string) {
  const names: Record<string, string> = {
    document: '文档',
    mindmap: '导图',
    video: '视频',
    code: '代码',
    exercise: '练习'
  }
  return names[type] || type
}

function getDifficultyName(difficulty: string) {
  const names: Record<string, string> = {
    basic: '基础',
    intermediate: '中级',
    advanced: '高级'
  }
  return names[difficulty] || difficulty
}

function showCreateModal() {
  isEditing.value = false
  editingId.value = ''
  formData.value = {
    title: '',
    description: '',
    type: 'document',
    difficulty: 'basic',
    duration: '30分钟',
    isWeakPoint: false,
    content: ''
  }
  modalVisible.value = true
}

function showEditModal(resource: ResourceItem) {
  isEditing.value = true
  editingId.value = resource.id
  formData.value = {
    title: resource.title,
    description: resource.description,
    type: resource.type,
    difficulty: resource.difficulty,
    duration: resource.duration,
    isWeakPoint: resource.isWeakPoint,
    content: ''
  }
  modalVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.title) {
    message.warning('请输入资源名称')
    return
  }

  try {
    const payload = {
      name: formData.value.title,
      description: formData.value.description,
      type: formData.value.type,
      difficulty: formData.value.difficulty,
      duration: formData.value.duration,
      is_weak_point: formData.value.isWeakPoint,
      content: formData.value.content,
    }

    if (isEditing.value) {
      await updateResource(editingId.value, payload)
      message.success('资源更新成功')
    } else {
      const result = await createResource(payload)
      if (result && result.id) {
        message.success('资源创建成功')
      }
    }
    modalVisible.value = false
    await loadResources()
  } catch {
    message.error('操作失败')
  }
}

function handleCancel() {
  modalVisible.value = false
}

async function handleDelete(id: string) {
  try {
    await deleteResource(id)
    message.success('资源删除成功')
    await loadResources()
  } catch {
    message.error('删除失败')
  }
}

async function loadResources() {
  try {
    const data = await getResourceList()
    if (data && data.items) {
      resources.value = data.items.map((r: any) => ({
        id: r.id,
        title: r.title || r.name || '',
        description: r.description || '',
        type: r.type || 'document',
        difficulty: r.difficulty || 'basic',
        duration: r.duration || '30分钟',
        isWeakPoint: r.isWeakPoint ?? r.is_weak_point ?? false,
        createdAt: r.created_at || r.createdAt || ''
      }))
    } else {
      resources.value = []
    }
  } catch {
    resources.value = []
  }
}

onMounted(() => {
  loadResources()
})
</script>

<style lang="less" scoped>
.resources-manage-view {
  padding: 0;
}

/* 操作栏 */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.search-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 资源列表 */
.resources-list {
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.list-header {
  display: flex;
  padding: 16px 20px;
  background: #f8fafc;
  border-radius: 12px 12px 0 0;
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  border-bottom: 1px solid #e2e8f0;
}

.list-body {
  padding: 12px;
}

.resource-row {
  display: flex;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid #e2e8f0;
  margin-bottom: 8px;
  transition: all 0.2s;

  &:hover {
    background: #f8fafc;
    border-color: #2563eb;
  }

  &:last-child { margin-bottom: 0; }
}

.col-title { flex: 2; min-width: 200px; }
.col-type { width: 80px; }
.col-difficulty { width: 80px; }
.col-duration { width: 80px; }
.col-weak { width: 100px; }
.col-date { width: 100px; }
.col-actions { width: 120px; }

.resource-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #1e293b;
  font-weight: 500;
}

.resource-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  margin-left: 26px;
}

.type-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;

  &.document { background: rgba(37, 99, 235, 0.1); color: #2563eb; }
  &.mindmap { background: rgba(16, 185, 129, 0.1); color: #10b981; }
  &.video { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
  &.code { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
  &.exercise { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
}

.difficulty-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;

  &.basic { background: #dcfce7; color: #16a34a; }
  &.intermediate { background: #fef3c7; color: #d97706; }
  &.advanced { background: #fee2e2; color: #dc2626; }
}

.weak-tag {
  font-size: 12px;
  color: #f59e0b;
}

.normal-tag {
  font-size: 12px;
  color: #94a3b8;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #94a3b8;

  p { margin-top: 12px; }
}

/* 弹窗表单 */
.switch-label {
  margin-left: 8px;
  font-size: 13px;
  color: #64748b;
}
</style>