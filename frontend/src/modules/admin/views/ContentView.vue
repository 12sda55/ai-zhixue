<template>
  <div class="content-view">
    <!-- 头部 -->
    <div class="content-header">
      <div class="header-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'courses' }" @click="activeTab = 'courses'">课程管理</button>
        <button class="tab-btn" :class="{ active: activeTab === 'resources' }" @click="activeTab = 'resources'">资源库</button>
      </div>
      <button class="create-btn" @click="handleCreate">
        <PlusOutlined /> {{ activeTab === 'courses' ? '创建课程' : '上传资源' }}
      </button>
    </div>

    <!-- 课程管理 -->
    <div v-show="activeTab === 'courses'" class="courses-section">
      <div class="filter-bar">
        <div class="search-box">
          <SearchOutlined class="search-icon" />
          <input v-model="courseKeyword" placeholder="搜索课程..." class="search-input" @input="searchCourses" />
        </div>
      </div>

      <div class="courses-grid">
        <div v-for="course in courses" :key="course.id" class="course-card">
          <div class="course-header">
            <h3 class="course-name">{{ course.name }}</h3>
            <a-tag :color="course.status === 'active' ? 'green' : 'orange'">
              {{ course.status === 'active' ? '已发布' : '草稿' }}
            </a-tag>
          </div>
          <p class="course-desc">{{ course.description || '暂无描述' }}</p>
          <div class="course-chapters">
            <span class="chapter-count">{{ course.chapters?.length || 0 }} 个章节</span>
          </div>
          <div class="course-actions">
            <a-button type="link" size="small" @click="editCourse(course)">编辑</a-button>
            <a-popconfirm title="确定删除该课程吗？" @confirm="deleteCourseItem(course.id)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>

      <a-empty v-if="courses.length === 0" description="暂无课程" />
    </div>

    <!-- 资源库 -->
    <div v-show="activeTab === 'resources'" class="resources-section">
      <div class="filter-bar">
        <div class="search-box">
          <SearchOutlined class="search-icon" />
          <input v-model="resourceKeyword" placeholder="搜索资源..." class="search-input" />
        </div>
        <div class="filter-group">
          <a-select v-model:value="resourceTypeFilter" style="width: 140px" placeholder="资源类型" allowClear>
            <a-select-option value="document">文档</a-select-option>
            <a-select-option value="mindmap">思维导图</a-select-option>
            <a-select-option value="code">代码</a-select-option>
            <a-select-option value="video">视频</a-select-option>
            <a-select-option value="exercise">习题</a-select-option>
          </a-select>
          <a-select v-model:value="resourceCourseFilter" style="width: 160px" placeholder="关联课程" allowClear>
            <a-select-option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</a-select-option>
          </a-select>
        </div>
      </div>

      <div class="resources-table">
        <a-table
          :columns="resourceColumns"
          :data-source="filteredResources"
          :loading="resourceLoading"
          :pagination="resourcePagination"
          row-key="id"
          @change="handleResourceTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'type'">
              <a-tag :color="getTypeColor(record.type)">{{ getTypeText(record.type) }}</a-tag>
            </template>
            <template v-else-if="column.key === 'file_size'">
              {{ formatFileSize(record.file_size) }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="editResource(record)">编辑</a-button>
              <a-popconfirm title="确定删除该资源吗？" @confirm="deleteResourceItem(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 课程表单弹窗 -->
    <a-modal
      v-model:open="showCourseModal"
      :title="editingCourse ? '编辑课程' : '创建课程'"
      @ok="handleCourseSubmit"
      width="600px"
    >
      <a-form :model="courseForm" :label-col="{ span: 4 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="课程名称" required>
          <a-input v-model:value="courseForm.name" placeholder="请输入课程名称" />
        </a-form-item>
        <a-form-item label="课程描述">
          <a-textarea v-model:value="courseForm.description" placeholder="请输入课程描述" :rows="3" />
        </a-form-item>
        <a-form-item label="章节列表">
          <div class="chapters-editor">
            <div v-for="(ch, idx) in courseForm.chapters" :key="idx" class="chapter-item">
              <a-input v-model:value="ch.title" :placeholder="`章节 ${idx + 1}`" />
              <a-button type="text" danger size="small" @click="removeChapter(idx)">
                <DeleteOutlined />
              </a-button>
            </div>
            <a-button type="dashed" block @click="addChapter">
              <PlusOutlined /> 添加章节
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="状态">
          <a-radio-group v-model:value="courseForm.status">
            <a-radio value="active">发布</a-radio>
            <a-radio value="inactive">草稿</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 资源表单弹窗 -->
    <a-modal
      v-model:open="showResourceModal"
      :title="editingResource ? '编辑资源' : '上传资源'"
      @ok="handleResourceSubmit"
      width="500px"
    >
      <a-form :model="resourceForm" :label-col="{ span: 5 }" :wrapper-col="{ span: 17 }">
        <a-form-item label="资源名称" required>
          <a-input v-model:value="resourceForm.name" placeholder="请输入资源名称" />
        </a-form-item>
        <a-form-item label="资源类型" required>
          <a-select v-model:value="resourceForm.type" placeholder="请选择类型">
            <a-select-option value="document">文档</a-select-option>
            <a-select-option value="mindmap">思维导图</a-select-option>
            <a-select-option value="code">代码</a-select-option>
            <a-select-option value="video">视频</a-select-option>
            <a-select-option value="exercise">习题</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="关联课程">
          <a-select v-model:value="resourceForm.course_id" placeholder="选择关联课程" allowClear>
            <a-select-option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="资源描述">
          <a-textarea v-model:value="resourceForm.description" placeholder="请输入资源描述" :rows="3" />
        </a-form-item>
        <a-form-item label="文件路径">
          <a-input v-model:value="resourceForm.file_path" placeholder="输入文件路径或URL" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import type { TablePaginationConfig } from 'ant-design-vue'
import * as adminApi from '../api/adminApi'
import type { CourseItem, CourseListRes, AdminResourceItem, ResourceListRes } from '../types'

// Tab
const activeTab = ref('courses')

// ========== 课程管理 ==========

const courses = ref<CourseItem[]>([])
const courseKeyword = ref('')
const courseLoading = ref(false)

const courseForm = reactive({
  name: '',
  description: '',
  chapters: [] as { title: string; order: number }[],
  status: 'active'
})

const showCourseModal = ref(false)
const editingCourse = ref<CourseItem | null>(null)

const fetchCourses = async () => {
  courseLoading.value = true
  try {
    const res = await adminApi.getCourseList({ keyword: courseKeyword.value || undefined })
    courses.value = res.items || []
  } catch (e) {
    console.error('获取课程列表失败', e)
  } finally {
    courseLoading.value = false
  }
}

const searchCourses = () => {
  setTimeout(fetchCourses, 300)
}

const addChapter = () => {
  courseForm.chapters.push({ title: '', order: courseForm.chapters.length + 1 })
}

const removeChapter = (idx: number) => {
  courseForm.chapters.splice(idx, 1)
  courseForm.chapters.forEach((ch, i) => ch.order = i + 1)
}

const editCourse = (course: CourseItem) => {
  editingCourse.value = course
  courseForm.name = course.name
  courseForm.description = course.description || ''
  courseForm.chapters = course.chapters ? [...course.chapters] : []
  courseForm.status = course.status
  showCourseModal.value = true
}

const handleCourseSubmit = async () => {
  try {
    if (editingCourse.value) {
      await adminApi.updateCourse(editingCourse.value.id, {
        name: courseForm.name,
        description: courseForm.description,
        chapters: courseForm.chapters.filter(c => c.title),
        status: courseForm.status
      })
      message.success('课程更新成功')
    } else {
      await adminApi.createCourse({
        name: courseForm.name,
        description: courseForm.description,
        chapters: courseForm.chapters.filter(c => c.title)
      })
      message.success('课程创建成功')
    }
    showCourseModal.value = false
    resetCourseForm()
    fetchCourses()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

const deleteCourseItem = async (id: number) => {
  try {
    await adminApi.deleteCourse(id)
    message.success('课程已删除')
    fetchCourses()
  } catch (e) {
    message.error('删除失败')
  }
}

const resetCourseForm = () => {
  courseForm.name = ''
  courseForm.description = ''
  courseForm.chapters = []
  courseForm.status = 'active'
  editingCourse.value = null
}

// ========== 资源管理 ==========

const resources = ref<AdminResourceItem[]>([])
const resourceKeyword = ref('')
const resourceTypeFilter = ref<string>()
const resourceCourseFilter = ref<number>()
const resourceLoading = ref(false)
const resourcePagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const resourceForm = reactive({
  name: '',
  type: 'document',
  course_id: undefined as number | undefined,
  description: '',
  file_path: ''
})

const showResourceModal = ref(false)
const editingResource = ref<AdminResourceItem | null>(null)

const resourceColumns = [
  { title: '资源名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'type', width: 100 },
  { title: '文件大小', key: 'file_size', width: 100 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
  { title: '创建时间', key: 'created_at', width: 160 },
  { title: '操作', key: 'actions', width: 120 }
]

const filteredResources = computed(() => {
  let list = resources.value || []
  if (resourceTypeFilter.value) {
    list = list.filter(r => r && r.type === resourceTypeFilter.value)
  }
  if (resourceCourseFilter.value) {
    list = list.filter(r => r && r.course_id === resourceCourseFilter.value)
  }
  if (resourceKeyword.value) {
    const kw = resourceKeyword.value.toLowerCase()
    list = list.filter(r => r && r.name && r.name.toLowerCase().includes(kw))
  }
  return list
})

const fetchResources = async () => {
  resourceLoading.value = true
  try {
    const res = await adminApi.getResourceList({
      page: resourcePagination.current,
      page_size: resourcePagination.pageSize
    })
    resources.value = res.items || []
    resourcePagination.total = res.total || 0
  } catch (e) {
    console.error('获取资源列表失败', e)
  } finally {
    resourceLoading.value = false
  }
}

const handleResourceTableChange = (pag: TablePaginationConfig) => {
  resourcePagination.current = pag.current
  resourcePagination.pageSize = pag.pageSize
  fetchResources()
}

const editResource = (resource: AdminResourceItem) => {
  editingResource.value = resource
  resourceForm.name = resource.name
  resourceForm.type = resource.type
  resourceForm.course_id = resource.course_id
  resourceForm.description = resource.description || ''
  resourceForm.file_path = resource.file_path || ''
  showResourceModal.value = true
}

const handleResourceSubmit = async () => {
  try {
    if (editingResource.value) {
      await adminApi.updateResource(editingResource.value.id, {
        name: resourceForm.name,
        type: resourceForm.type,
        course_id: resourceForm.course_id,
        description: resourceForm.description
      })
      message.success('资源更新成功')
    } else {
      await adminApi.createResource({
        name: resourceForm.name,
        type: resourceForm.type,
        course_id: resourceForm.course_id,
        description: resourceForm.description,
        file_path: resourceForm.file_path
      })
      message.success('资源创建成功')
    }
    showResourceModal.value = false
    resetResourceForm()
    fetchResources()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

const deleteResourceItem = async (id: number) => {
  try {
    await adminApi.deleteResource(id)
    message.success('资源已删除')
    fetchResources()
  } catch (e) {
    message.error('删除失败')
  }
}

const resetResourceForm = () => {
  resourceForm.name = ''
  resourceForm.type = 'document'
  resourceForm.course_id = undefined
  resourceForm.description = ''
  resourceForm.file_path = ''
  editingResource.value = null
}

// ========== 工具函数 ==========
const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    document: 'blue',
    mindmap: 'purple',
    code: 'green',
    video: 'red',
    exercise: 'orange'
  }
  return colors[type] || 'default'
}

const getTypeText = (type: string) => {
  const texts: Record<string, string> = {
    document: '文档',
    mindmap: '思维导图',
    code: '代码',
    video: '视频',
    exercise: '习题'
  }
  return texts[type] || type
}

const formatFileSize = (size?: number) => {
  if (!size) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / 1024 / 1024).toFixed(1) + ' MB'
}

const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}

const handleCreate = () => {
  if (activeTab.value === 'courses') {
    resetCourseForm()
    showCourseModal.value = true
  } else {
    resetResourceForm()
    showResourceModal.value = true
  }
}

onMounted(() => {
  fetchCourses()
  fetchResources()
})
</script>

<style lang="less" scoped>
.content-view {
  padding: 0;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-tabs {
  display: flex;
  gap: 4px;
  background: rgba(37, 99, 235, 0.06);
  padding: 4px;
  border-radius: 10px;
}

.tab-btn {
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;

  &.active {
    background: transparent;
    color: #2563eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border: none;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.search-box {
  position: relative;
  flex: 1;
  max-width: 320px;

  .search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #94a3b8;
  }

  .search-input {
    width: 100%;
    padding: 8px 12px 8px 36px;
    border: 1px solid rgba(37, 99, 235, 0.1);
    border-radius: 8px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;

    &:focus {
      border-color: #2563eb;
    }
  }
}

.filter-group {
  display: flex;
  gap: 12px;
}

// 课程卡片
.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.course-card {
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(37, 99, 235, 0.2);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
  }
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.course-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.course-desc {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-chapters {
  margin-bottom: 12px;

  .chapter-count {
    font-size: 12px;
    color: #2563eb;
    background: rgba(37, 99, 235, 0.08);
    padding: 4px 10px;
    border-radius: 6px;
  }
}

.course-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(37, 99, 235, 0.06);
}

// 章节编辑器
.chapters-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

// 资源表格
.resources-table {
  background: transparent;
  border-radius: 12px;
  overflow: hidden;

  :deep(.ant-table) {
    background: transparent;

    .ant-table-thead > tr > th {
      background: rgba(37, 99, 235, 0.04);
      border-bottom: 1px solid rgba(37, 99, 235, 0.1);
    }

    .ant-table-tbody > tr > td {
      border-bottom: 1px solid rgba(37, 99, 235, 0.06);
    }
  }
}
</style>
