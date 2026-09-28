<template>
  <div class="audit-logs-view">
    <!-- 头部 -->
    <div class="logs-header">
      <span class="page-title">审计日志</span>
      <div class="header-actions">
        <a-button @click="exportLogs">
          <DownloadOutlined /> 导出
        </a-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <a-range-picker v-model:value="dateRange" @change="fetchLogs" />
        <a-select v-model:value="actionTypeFilter" style="width: 160px" placeholder="操作类型" allowClear @change="fetchLogs">
          <a-select-option value="create_user">创建用户</a-select-option>
          <a-select-option value="update_user">更新用户</a-select-option>
          <a-select-option value="delete_user">删除用户</a-select-option>
          <a-select-option value="change_user_status">修改状态</a-select-option>
          <a-select-option value="create_course">创建课程</a-select-option>
          <a-select-option value="update_course">更新课程</a-select-option>
          <a-select-option value="delete_course">删除课程</a-select-option>
          <a-select-option value="create_resource">创建资源</a-select-option>
          <a-select-option value="update_settings">更新设置</a-select-option>
          <a-select-option value="start_agent">启动Agent</a-select-option>
          <a-select-option value="stop_agent">停止Agent</a-select-option>
        </a-select>
        <a-input v-model:value="keyword" placeholder="搜索目标名称..." style="width: 200px" @pressEnter="fetchLogs" />
        <a-button type="primary" @click="fetchLogs">查询</a-button>
      </div>
    </div>

    <!-- 日志表格 -->
    <div class="logs-table">
      <a-table
        :columns="columns"
        :data-source="logs"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action_type'">
            <a-tag :color="getActionColor(record.action_type)">
              {{ getActionText(record.action_type) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'target'">
            <span class="target-cell">
              <a-tag size="small">{{ record.target_type }}</a-tag>
              <span>{{ record.target_name || '-' }}</span>
            </span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-button type="link" size="small" @click="viewDetail(record)">详情</a-button>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:open="showDetailDrawer"
      title="日志详情"
      placement="right"
      :width="500"
    >
      <div v-if="selectedLog" class="log-detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">日志ID:</span>
              <span>{{ selectedLog.id }}</span>
            </div>
            <div class="info-item">
              <span class="label">操作人:</span>
              <span>{{ selectedLog.operator_name || selectedLog.operator_id }}</span>
            </div>
            <div class="info-item">
              <span class="label">操作类型:</span>
              <a-tag :color="getActionColor(selectedLog.action_type)">
                {{ getActionText(selectedLog.action_type) }}
              </a-tag>
            </div>
            <div class="info-item">
              <span class="label">目标类型:</span>
              <span>{{ selectedLog.target_type || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">目标名称:</span>
              <span>{{ selectedLog.target_name || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">IP地址:</span>
              <span>{{ selectedLog.ip_address || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">操作时间:</span>
              <span>{{ formatDate(selectedLog.created_at) }}</span>
            </div>
          </div>
        </div>

        <div v-if="selectedLog.detail" class="detail-section">
          <h4>变更详情</h4>
          <div class="detail-content">
            <div v-if="selectedLog.detail.before" class="detail-block">
              <span class="block-label">变更前:</span>
              <pre class="block-content">{{ JSON.stringify(selectedLog.detail.before, null, 2) }}</pre>
            </div>
            <div v-if="selectedLog.detail.after" class="detail-block">
              <span class="block-label">变更后:</span>
              <pre class="block-content">{{ JSON.stringify(selectedLog.detail.after, null, 2) }}</pre>
            </div>
            <div v-if="selectedLog.detail.extra" class="detail-block">
              <span class="block-label">额外信息:</span>
              <pre class="block-content">{{ JSON.stringify(selectedLog.detail.extra, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { DownloadOutlined } from '@ant-design/icons-vue'
import type { Dayjs } from 'dayjs'
import * as adminApi from '../api/adminApi'

interface AuditLogItem {
  id: number
  operator_id: number
  operator_name?: string
  action_type: string
  target_type?: string
  target_id?: number
  target_name?: string
  detail?: any
  ip_address?: string
  created_at?: string
}

const loading = ref(false)
const logs = ref<AuditLogItem[]>([])
const dateRange = ref<[Dayjs, Dayjs]>()
const actionTypeFilter = ref<string>()
const keyword = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const showDetailDrawer = ref(false)
const selectedLog = ref<AuditLogItem | null>(null)

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 100 },
  { title: '操作类型', key: 'action_type', width: 120 },
  { title: '目标', key: 'target', width: 200 },
  { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address', width: 120 },
  { title: '操作时间', key: 'created_at', width: 160 },
  { title: '操作', key: 'actions', width: 80 }
]

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize
    }
    if (dateRange.value) {
      params.start_date = dateRange.value[0].format('YYYY-MM-DD')
      params.end_date = dateRange.value[1].format('YYYY-MM-DD')
    }
    if (actionTypeFilter.value) {
      params.action_type = actionTypeFilter.value
    }
    if (keyword.value) {
      params.keyword = keyword.value
    }

    const res = await adminApi.getAuditLogs(params)
    logs.value = res?.items || []
    pagination.total = res?.total || 0
  } catch (e) {
    console.error('获取审计日志失败', e)
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: { current: number; pageSize: number }) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchLogs()
}

const viewDetail = (log: AuditLogItem) => {
  selectedLog.value = log
  showDetailDrawer.value = true
}

const exportLogs = async () => {
  try {
    message.loading({ content: '正在导出...', key: 'export' })

    const params: Record<string, string> = {}
    if (dateRange.value) {
      params.start_date = dateRange.value[0].format('YYYY-MM-DD')
      params.end_date = dateRange.value[1].format('YYYY-MM-DD')
    }
    if (actionTypeFilter.value) {
      params.action_type = actionTypeFilter.value
    }
    if (keyword.value) {
      params.keyword = keyword.value
    }

    const blob = await adminApi.exportAuditLogs(params)

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    message.success({ content: '导出成功', key: 'export' })
  } catch (e) {
    console.error('导出失败', e)
    message.error({ content: '导出失败', key: 'export' })
  }
}

const getActionColor = (type: string) => {
  const colors: Record<string, string> = {
    create_user: 'green',
    update_user: 'blue',
    delete_user: 'red',
    change_user_status: 'orange',
    create_course: 'green',
    update_course: 'blue',
    delete_course: 'red',
    create_resource: 'green',
    update_resource: 'blue',
    delete_resource: 'red',
    update_settings: 'purple',
    start_agent: 'cyan',
    stop_agent: 'orange',
    restart_agent: 'blue'
  }
  return colors[type] || 'default'
}

const getActionText = (type: string) => {
  const texts: Record<string, string> = {
    create_user: '创建用户',
    update_user: '更新用户',
    delete_user: '删除用户',
    change_user_status: '修改状态',
    batch_delete_users: '批量删除',
    batch_change_status: '批量改状态',
    create_course: '创建课程',
    update_course: '更新课程',
    delete_course: '删除课程',
    create_resource: '创建资源',
    update_resource: '更新资源',
    delete_resource: '删除资源',
    update_settings: '更新设置',
    start_agent: '启动Agent',
    stop_agent: '停止Agent',
    restart_agent: '重启Agent',
    generate_share_token: '生成分享链接',
    revoke_share_token: '撤销分享链接'
  }
  return texts[type] || type
}

const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchLogs()
})
</script>

<style lang="less" scoped>
.audit-logs-view {
  padding: 0;
}

.logs-header {
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

.filter-bar {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.logs-table {
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

.target-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

// 详情抽屉
.log-detail {
  .detail-section {
    margin-bottom: 24px;

    h4 {
      margin-bottom: 12px;
      font-size: 14px;
      font-weight: 600;
      color: #0f172a;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(37, 99, 235, 0.1);
    }
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .info-item {
    display: flex;
    gap: 8px;
    font-size: 13px;

    .label {
      color: #94a3b8;
      min-width: 70px;
    }
  }

  .detail-content {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .detail-block {
    .block-label {
      font-size: 12px;
      color: #475569;
      margin-bottom: 6px;
      display: block;
    }

    .block-content {
      font-size: 11px;
      background: rgba(37, 99, 235, 0.04);
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      margin: 0;
      font-family: 'Consolas', monospace;
    }
  }
}
</style>
