<template>
  <div class="users-view">
    <!-- 头部 -->
    <div class="users-header">
      <span class="page-title">用户管理</span>
      <div class="header-actions">
        <button class="create-btn" @click="showCreateModal = true">
          <PlusOutlined /> 创建用户
        </button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="search-box">
        <SearchOutlined class="search-icon" />
        <input v-model="keyword" placeholder="搜索用户名或邮箱..." class="search-input" @input="handleSearch" />
      </div>
      <div class="filter-group">
        <a-select v-model:value="roleFilter" style="width: 120px" placeholder="角色" @change="fetchUsers">
          <a-select-option value="">全部角色</a-select-option>
          <a-select-option value="student">学生</a-select-option>
          <a-select-option value="admin">管理员</a-select-option>
        </a-select>
        <a-select v-model:value="statusFilter" style="width: 120px" placeholder="状态" @change="fetchUsers">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option value="active">正常</a-select-option>
          <a-select-option value="disabled">禁用</a-select-option>
        </a-select>
      </div>
    </div>

    <!-- 批量操作 -->
    <div v-if="selectedUserIds.length > 0" class="batch-actions">
      <span class="selected-count">已选择 {{ selectedUserIds.length }} 个用户</span>
      <a-button type="primary" size="small" @click="handleBatchEnable">批量启用</a-button>
      <a-button size="small" @click="handleBatchDisable">批量禁用</a-button>
      <a-button danger size="small" @click="handleBatchDelete">批量删除</a-button>
    </div>

    <!-- 用户表格 -->
    <div class="users-table">
      <a-table
        :columns="columns"
        :data-source="users"
        :loading="loading"
        :pagination="pagination"
        :row-selection="rowSelection"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'user'">
            <div class="user-cell">
              <div class="user-avatar">{{ record.username?.[0]?.toUpperCase() }}</div>
              <div class="user-info">
                <span class="user-name">{{ record.username }}</span>
                <span class="user-email">{{ record.email || '-' }}</span>
              </div>
            </div>
          </template>
          <template v-else-if="column.key === 'role'">
            <a-tag :color="(record.role || 'student') === 'admin' ? 'orange' : 'blue'">
              {{ (record.role || 'student') === 'admin' ? '管理员' : '学生' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status || 'active')">{{ getStatusText(record.status || 'active') }}</a-tag>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <div class="action-cell">
              <a-button type="link" size="small" @click="viewUserDetail(record)">详情</a-button>
              <a-button type="link" size="small" @click="editUser(record)">编辑</a-button>
              <a-button type="link" size="small" @click="handleToggleStatus(record)">
                {{ record.status === 'active' ? '禁用' : '启用' }}
              </a-button>
              <a-popconfirm title="确定删除该用户吗？" @confirm="handleDeleteUser(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 创建/编辑用户弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingUser ? '编辑用户' : '创建用户'"
      @ok="handleSubmit"
      @cancel="resetForm"
    >
      <a-form :model="userForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="用户名" required>
          <a-input v-model:value="userForm.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item v-if="!editingUser" label="密码" required>
          <a-input-password v-model:value="userForm.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item v-if="editingUser" label="新密码">
          <a-input-password v-model:value="userForm.password" placeholder="留空则不修改密码" />
        </a-form-item>
        <a-form-item label="角色">
          <a-select v-model:value="userForm.role">
            <a-select-option value="student">学生</a-select-option>
            <a-select-option value="admin">管理员</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 用户详情弹窗 -->
    <a-modal v-model:open="showDetailModal" title="用户详情" :footer="null" width="900px">
      <div v-if="detailUser" class="user-detail">
        <!-- 基本信息卡片 -->
        <div class="detail-card">
          <div class="card-header">
            <span class="card-title"><UserOutlined /> 基本信息</span>
          </div>
          <div class="basic-info">
            <div class="avatar-large">{{ detailUser.user?.username?.[0]?.toUpperCase() }}</div>
            <div class="info-main">
              <div class="info-row">
                <span class="info-label">用户名</span>
                <span class="info-value">{{ detailUser.user?.username }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">邮箱</span>
                <span class="info-value">{{ detailUser.user?.email || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">角色</span>
                <a-tag :color="detailUser.user?.role === 'admin' ? 'orange' : 'blue'">
                  {{ detailUser.user?.role === 'admin' ? '管理员' : '学生' }}
                </a-tag>
              </div>
              <div class="info-row">
                <span class="info-label">状态</span>
                <a-tag :color="getStatusColor(detailUser.user?.status)">{{ getStatusText(detailUser.user?.status) }}</a-tag>
              </div>
              <div class="info-row">
                <span class="info-label">注册时间</span>
                <span class="info-value">{{ formatDate(detailUser.user?.created_at) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">最后登录</span>
                <span class="info-value">{{ formatDate(detailUser.user?.last_login_at) || '从未登录' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">登录次数</span>
                <span class="info-value">{{ detailUser.user?.login_count || 0 }} 次</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 用户画像雷达图 -->
        <div v-if="detailUser.profile" class="detail-card">
          <div class="card-header">
            <span class="card-title"><DashboardOutlined /> 用户画像</span>
            <span class="card-subtitle">8维能力评估</span>
          </div>
          <div class="radar-container">
            <div class="radar-chart" ref="radarChartRef"></div>
            <div class="radar-legend">
              <div v-for="(dim, idx) in detailUser.profile?.dimensions || []" :key="idx" class="legend-item">
                <span class="legend-dot" :style="{ background: dim.color || '#2563eb' }"></span>
                <span class="legend-label">{{ dim.name }}</span>
                <span class="legend-value">{{ dim.value }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 学习进度 -->
        <div class="detail-card">
          <div class="card-header">
            <span class="card-title"><BookOutlined /> 学习进度</span>
          </div>
          <div class="progress-stats">
            <div class="stat-item">
              <div class="stat-icon completed"><CheckCircleOutlined /></div>
              <div class="stat-content">
                <div class="stat-num">{{ detailUser.progress?.completed_resources || 0 }}</div>
                <div class="stat-text">已完成资源</div>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-icon stages"><FlagOutlined /></div>
              <div class="stat-content">
                <div class="stat-num">{{ detailUser.progress?.completed_stages || 0 }}</div>
                <div class="stat-text">完成阶段</div>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-icon assess"><SolutionOutlined /></div>
              <div class="stat-content">
                <div class="stat-num">{{ detailUser.progress?.completed_assessments || 0 }}</div>
                <div class="stat-text">评估次数</div>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-icon streak"><FireOutlined /></div>
              <div class="stat-content">
                <div class="stat-num">{{ detailUser.progress?.streak_days || 0 }}</div>
                <div class="stat-text">连续学习天数</div>
              </div>
            </div>
          </div>
          <!-- 当前学习路径 -->
          <div v-if="detailUser.paths?.length" class="current-path">
            <h5>当前学习路径</h5>
            <div class="path-stages">
              <div v-for="(stage, idx) in detailUser.paths.slice(0, 3)" :key="stage.id" class="stage-item" :class="stage.status">
                <div class="stage-num">{{ idx + 1 }}</div>
                <div class="stage-info">
                  <span class="stage-title">{{ stage.title }}</span>
                  <span class="stage-status">{{ stage.status === 'completed' ? '已完成' : stage.status === 'active' ? '进行中' : '待开始' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 评估记录 -->
        <div v-if="detailUser.assessments?.length" class="detail-card">
          <div class="card-header">
            <span class="card-title"><SolutionOutlined /> 评估记录</span>
            <span class="card-subtitle">最近10条</span>
          </div>
          <div class="assess-table">
            <div class="assess-header">
              <span>评估时间</span>
              <span>得分</span>
              <span>题目数</span>
              <span>正确率</span>
            </div>
            <div v-for="a in detailUser.assessments.slice(0, 10)" :key="a.id" class="assess-row">
              <span>{{ formatDate(a.created_at) }}</span>
              <span class="score" :class="{ high: a.score >= 80, mid: a.score >= 60 && a.score < 80, low: a.score < 60 }">{{ a.score }}分</span>
              <span>{{ a.total_questions || '-' }}</span>
              <span>{{ a.correct_rate ? `${a.correct_rate}%` : '-' }}</span>
            </div>
          </div>
        </div>

        <!-- 操作日志 -->
        <div class="detail-card">
          <div class="card-header">
            <span class="card-title"><HistoryOutlined /> 操作日志</span>
            <span class="card-subtitle">该用户相关操作</span>
          </div>
          <div class="log-table">
            <div v-for="log in userLogs.slice(0, 5)" :key="log.id" class="log-row">
              <a-tag :color="getActionColor(log.action_type)" size="small">{{ getActionText(log.action_type) }}</a-tag>
              <span class="log-time">{{ formatDate(log.created_at) }}</span>
              <span class="log-operator">{{ log.operator_name || '系统' }}</span>
            </div>
            <a-empty v-if="userLogs.length === 0" description="暂无操作日志" />
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined, SearchOutlined, UserOutlined, DashboardOutlined,
  BookOutlined, CheckCircleOutlined, FlagOutlined, SolutionOutlined,
  FireOutlined, HistoryOutlined
} from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import * as adminApi from '../api/adminApi'

interface UserItem {
  id: string
  username: string
  email?: string
  role: string
  status: string
  created_at?: string
  last_login_at?: string
  login_count?: number
}

// 状态
const loading = ref(false)
const users = ref<UserItem[]>([])
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 选择
const selectedUserIds = ref<string[]>([])
const rowSelection = computed(() => ({
  selectedRowKeys: selectedUserIds.value,
  onChange: (keys: string[]) => {
    selectedUserIds.value = keys
  }
}))

// 弹窗
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const editingUser = ref<UserItem | null>(null)
const detailUser = ref<any>(null)
const userLogs = ref<any[]>([])

// 雷达图
const radarChartRef = ref<HTMLElement>()
let radarChart: echarts.ECharts | null = null

// 表单
const userForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'student'
})

// 表格列
const columns = [
  { title: '用户', key: 'user', dataIndex: 'user' },
  { title: '角色', key: 'role', dataIndex: 'role', width: 100 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '注册时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 200 }
]

// 加载用户列表
const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await adminApi.getUserList({
      page: pagination.current,
      page_size: pagination.pageSize,
      keyword: keyword.value || undefined,
      role: roleFilter.value || undefined,
      status: statusFilter.value || undefined
    })
    const data = res
    if (data) {
      users.value = data.items || []
      pagination.total = data.total || 0
    }
  } catch (e) {
    console.error('获取用户列表失败', e)
  } finally {
    loading.value = false
  }
}

// 搜索防抖
let searchTimer: number
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.current = 1
    fetchUsers()
  }, 300) as unknown as number
}

// 表格分页变化
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchUsers()
}

// 状态颜色
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'green',
    disabled: 'orange',
    inactive: 'orange',
    banned: 'red',
    deleted: 'default'
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    active: '正常',
    disabled: '禁用',
    inactive: '禁用',
    banned: '封禁',
    deleted: '已删除'
  }
  return texts[status] || status
}

// 日期格式化
const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 重置表单
const resetForm = () => {
  userForm.username = ''
  userForm.email = ''
  userForm.password = ''
  userForm.role = 'student'
  editingUser.value = null
}

// 创建/编辑提交
const handleSubmit = async () => {
  try {
    if (editingUser.value) {
      const data: any = {
        username: userForm.username,
        email: userForm.email,
        role: userForm.role
      }
      if (userForm.password) {
        data.password = userForm.password
      }
      await adminApi.updateUser(editingUser.value.id, data)
      message.success('用户更新成功')
    } else {
      await adminApi.createUser({
        username: userForm.username,
        password: userForm.password,
        email: userForm.email || undefined,
        role: userForm.role
      })
      message.success('用户创建成功')
    }
    showCreateModal.value = false
    resetForm()
    fetchUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

// 编辑用户
const editUser = (user: UserItem) => {
  editingUser.value = user
  userForm.username = user.username
  userForm.email = user.email || ''
  userForm.role = user.role
  userForm.password = ''
  showCreateModal.value = true
}

// 渲染雷达图
const renderRadarChart = () => {
  if (!radarChartRef.value || !detailUser.value?.profile?.dimensions) return

  if (radarChart) {
    radarChart.dispose()
  }
  radarChart = echarts.init(radarChartRef.value)

  const dimensions = detailUser.value.profile.dimensions || []
  const indicators = dimensions.map((d: any) => ({
    name: d.name,
    max: 100
  }))
  const values = dimensions.map((d: any) => d.value || 0)

  radarChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'transparent',
      borderColor: 'rgba(37, 99, 235, 0.1)',
      textStyle: { color: '#0f172a' }
    },
    radar: {
      indicator: indicators,
      radius: '65%',
      axisName: {
        color: '#475569',
        fontSize: 11
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(37, 99, 235, 0.02)', 'rgba(37, 99, 235, 0.04)']
        }
      },
      axisLine: {
        lineStyle: { color: 'rgba(37, 99, 235, 0.1)' }
      },
      splitLine: {
        lineStyle: { color: 'rgba(37, 99, 235, 0.1)' }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '用户画像',
        areaStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.1)' }
          ])
        },
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' }
      }]
    }]
  })
}

// 查看详情
const viewUserDetail = async (user: UserItem) => {
  try {
    const res = await adminApi.getUserDetail(user.id)
    detailUser.value = res

    // 获取用户相关日志
    const logsRes = await adminApi.getAuditLogs({
      page: 1,
      page_size: 10,
      keyword: user.username
    })
    userLogs.value = logsRes?.items || []

    showDetailModal.value = true

    // 等待DOM更新后渲染雷达图
    await nextTick()
    renderRadarChart()
  } catch (e) {
    message.error('获取用户详情失败')
  }
}

// 切换状态
const handleToggleStatus = async (user: UserItem) => {
  try {
    const newStatus = user.status === 'active' ? 'disabled' : 'active'
    await adminApi.changeUserStatus(user.id, newStatus)
    message.success('状态更新成功')
    fetchUsers()
  } catch (e) {
    message.error('状态更新失败')
  }
}

// 删除用户
const handleDeleteUser = async (userId: string) => {
  try {
    await adminApi.deleteUser(userId)
    message.success('用户已删除')
    fetchUsers()
  } catch (e) {
    message.error('删除失败')
  }
}

// 批量启用
const handleBatchEnable = async () => {
  try {
    await adminApi.batchChangeStatus(selectedUserIds.value, 'active')
    message.success('批量启用成功')
    selectedUserIds.value = []
    fetchUsers()
  } catch (e) {
    message.error('批量操作失败')
  }
}

// 批量禁用
const handleBatchDisable = async () => {
  try {
    await adminApi.batchChangeStatus(selectedUserIds.value, 'disabled')
    message.success('批量禁用成功')
    selectedUserIds.value = []
    fetchUsers()
  } catch (e) {
    message.error('批量操作失败')
  }
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await adminApi.batchDeleteUsers(selectedUserIds.value)
    message.success('批量删除成功')
    selectedUserIds.value = []
    fetchUsers()
  } catch (e) {
    message.error('批量删除失败')
  }
}

// 操作类型颜色
const getActionColor = (type: string) => {
  const colors: Record<string, string> = {
    create_user: 'green',
    update_user: 'blue',
    delete_user: 'red',
    change_user_status: 'orange',
    login: 'cyan'
  }
  return colors[type] || 'default'
}

const getActionText = (type: string) => {
  const texts: Record<string, string> = {
    create_user: '创建用户',
    update_user: '更新用户',
    delete_user: '删除用户',
    change_user_status: '修改状态',
    login: '登录'
  }
  return texts[type] || type
}

onMounted(() => {
  fetchUsers()
})

// 监听弹窗关闭，销毁图表
watch(showDetailModal, (val) => {
  if (!val && radarChart) {
    radarChart.dispose()
    radarChart = null
  }
})
</script>

<style lang="less" scoped>
.users-view {
  padding: 0;
}

.users-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
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

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: rgba(37, 99, 235, 0.06);
  border-radius: 8px;
}

.selected-count {
  font-size: 13px;
  color: #2563eb;
  font-weight: 500;
}

.users-table {
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

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
}

.user-email {
  font-size: 11px;
  color: #94a3b8;
}

.action-cell {
  display: flex;
  gap: 4px;
}

// 用户详情弹窗样式
.user-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-card {
  padding: 16px;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.02);
  border: 1px solid rgba(37, 99, 235, 0.08);

  .card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    .card-title {
      font-size: 14px;
      font-weight: 600;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .card-subtitle {
      font-size: 12px;
      color: #94a3b8;
    }
  }
}

.basic-info {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.avatar-large {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  flex-shrink: 0;
}

.info-main {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .info-label {
    color: #94a3b8;
    min-width: 70px;
  }

  .info-value {
    color: #0f172a;
  }
}

// 雷达图容器
.radar-container {
  display: flex;
  gap: 20px;
  align-items: center;
}

.radar-chart {
  width: 280px;
  height: 280px;
  flex-shrink: 0;
}

.radar-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }

  .legend-label {
    color: #475569;
    flex: 1;
  }

  .legend-value {
    color: #0f172a;
    font-weight: 600;
  }
}

// 学习进度统计
.progress-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: transparent;

  .stat-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;

    &.completed { background: rgba(16, 185, 129, 0.12); color: #10b981; }
    &.stages { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
    &.assess { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
    &.streak { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
  }

  .stat-num {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
  }

  .stat-text {
    font-size: 11px;
    color: #94a3b8;
  }
}

.current-path {
  h5 {
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 12px;
  }
}

.path-stages {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: transparent;

  .stage-num {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(37, 99, 235, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    color: #2563eb;
  }

  &.completed .stage-num {
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
  }

  &.active .stage-num {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #fff;
  }

  .stage-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .stage-title {
    font-size: 13px;
    font-weight: 500;
    color: #0f172a;
  }

  .stage-status {
    font-size: 11px;
    color: #94a3b8;
  }
}

// 评估表格
.assess-table {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.assess-header, .assess-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 12px;
  padding: 10px 12px;
  font-size: 12px;
}

.assess-header {
  background: rgba(37, 99, 235, 0.06);
  border-radius: 6px;
  color: #94a3b8;
  font-weight: 500;
}

.assess-row {
  background: transparent;
  border-radius: 6px;
  color: #475569;

  .score {
    font-weight: 600;

    &.high { color: #10b981; }
    &.mid { color: #f59e0b; }
    &.low { color: #ef4444; }
  }
}

// 日志表格
.log-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: transparent;
  font-size: 12px;

  .log-time {
    color: #94a3b8;
  }

  .log-operator {
    color: #475569;
    margin-left: auto;
  }
}
</style>
