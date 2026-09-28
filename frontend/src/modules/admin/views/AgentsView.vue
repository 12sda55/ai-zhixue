<template>
  <div class="agents-view">
    <!-- 头部 -->
    <div class="agents-header">
      <span class="page-title">Agent 监控</span>
      <div class="header-actions">
        <button class="refresh-btn" @click="fetchAgents">
          <ReloadOutlined /> 刷新
        </button>
      </div>
    </div>

    <!-- Agent 统计 -->
    <div class="stats-cards">
      <div class="stat-card">
        <span class="stat-value">{{ agentStats.total_calls }}</span>
        <span class="stat-label">总调用次数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ agentStats.success_rate }}%</span>
        <span class="stat-label">成功率</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ agentStats.avg_time }}ms</span>
        <span class="stat-label">平均耗时</span>
      </div>
    </div>

    <!-- Agent 卡片列表 -->
    <div class="agent-cards">
      <div v-for="a in agents" :key="a.agent_id" class="agent-card" :class="'status-' + getStatusClass(a.status)">
        <div class="card-header">
          <div class="agent-icon-wrap">
            <RobotOutlined class="agent-icon" />
          </div>
          <div class="agent-info">
            <span class="agent-name">{{ a.agent_name }}</span>
            <span class="agent-status" :class="getStatusClass(a.status)">
              <span v-if="a.status === 'running' || a.status === '运行中'" class="pulse-dot" />
              {{ statusText(a.status) }}
            </span>
          </div>
        </div>
        <div class="card-body">
          <div class="progress-row">
            <span class="progress-label">进度</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (a.progress || 0) + '%' }" />
            </div>
            <span class="progress-val">{{ a.progress || 0 }}%</span>
          </div>
          <div class="stats-row">
            <div class="mini-stat">
              <span class="mini-label">调用次数</span>
              <span class="mini-value">{{ a.call_count }}</span>
            </div>
            <div class="mini-stat">
              <span class="mini-label">平均耗时</span>
              <span class="mini-value">{{ a.avg_time || '-' }}</span>
            </div>
          </div>
        </div>
        <div class="card-actions">
          <a-button v-if="a.status === 'running' || a.status === '运行中'" type="primary" size="small" @click="stopAgent(a.agent_id)">
            停止
          </a-button>
          <a-button v-else type="primary" size="small" ghost @click="startAgent(a.agent_id)">
            启动
          </a-button>
          <a-button size="small" @click="restartAgent(a.agent_id)">
            重启
          </a-button>
          <a-button size="small" @click="viewAgentLogs(a.agent_id)">
            日志
          </a-button>
          <a-button size="small" @click="openConfigDrawer(a)">
            <SettingOutlined /> 配置
          </a-button>
        </div>
      </div>
    </div>

    <a-empty v-if="agents.length === 0" description="暂无 Agent 数据" />

    <!-- Agent 日志抽屉 -->
    <a-drawer
      v-model:open="showLogDrawer"
      title="Agent 执行日志"
      placement="right"
      :width="600"
    >
      <div class="log-filters">
        <span>Agent: {{ selectedAgentId }}</span>
      </div>
      <div class="log-list">
        <div v-for="log in agentLogs" :key="log.id" class="log-item" :class="log.status">
          <div class="log-header">
            <a-tag :color="getLogStatusColor(log.status)">{{ log.status }}</a-tag>
            <span class="log-time">{{ formatDate(log.started_at) }}</span>
          </div>
          <div class="log-body">
            <div class="log-row">
              <span class="log-key">耗时:</span>
              <span class="log-val">{{ log.time_used || '-' }} ms</span>
            </div>
            <div v-if="log.input_data" class="log-row">
              <span class="log-key">输入:</span>
              <pre class="log-data">{{ JSON.stringify(log.input_data, null, 2) }}</pre>
            </div>
            <div v-if="log.output_data" class="log-row">
              <span class="log-key">输出:</span>
              <pre class="log-data">{{ JSON.stringify(log.output_data, null, 2) }}</pre>
            </div>
            <div v-if="log.error_message" class="log-row error">
              <span class="log-key">错误:</span>
              <span class="log-val">{{ log.error_message }}</span>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-if="agentLogs.length === 0" description="暂无执行日志" />
    </a-drawer>

    <!-- Agent 配置抽屉 -->
    <a-drawer
      v-model:open="showConfigDrawer"
      title="Agent 配置"
      placement="right"
      :width="500"
    >
      <a-form v-if="selectedAgent" layout="vertical">
        <a-form-item label="名称">
          <a-input v-model:value="agentConfig.name" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="agentConfig.description" />
        </a-form-item>
        <a-form-item label="模型">
          <a-select v-model:value="agentConfig.model">
            <a-select-option value="deepseek-chat">DeepSeek Chat</a-select-option>
            <a-select-option value="deepseek-coder">DeepSeek Coder</a-select-option>
            <a-select-option value="gpt-4">GPT-4</a-select-option>
            <a-select-option value="gpt-3.5-turbo">GPT-3.5 Turbo</a-select-option>
            <a-select-option value="claude-3-opus">Claude 3 Opus</a-select-option>
            <a-select-option value="claude-3-sonnet">Claude 3 Sonnet</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Temperature">
          <a-slider v-model:value="agentConfig.temperature" :min="0" :max="2" :step="0.1" />
          <span class="slider-value">{{ agentConfig.temperature }}</span>
        </a-form-item>
        <a-form-item label="Max Tokens">
          <a-input-number v-model:value="agentConfig.max_tokens" :min="100" :max="8192" :step="100" />
        </a-form-item>
        <a-form-item label="系统提示词">
          <a-textarea v-model:value="agentConfig.system_prompt" :rows="6" placeholder="Agent的系统提示词..." />
        </a-form-item>
        <a-form-item label="启用状态">
          <a-switch v-model:checked="agentConfig.enabled" />
        </a-form-item>
      </a-form>
      <div class="drawer-footer">
        <a-button @click="showConfigDrawer = false">取消</a-button>
        <a-button type="primary" @click="saveAgentConfig" :loading="configSaving">保存</a-button>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { RobotOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons-vue'
import * as adminApi from '../api/adminApi'
import type { AgentStatsData, AgentLogItem, AgentLogListRes, AgentConfigData } from '../types'

interface AgentItem {
  agent_id: string
  agent_name: string
  status: string
  call_count: number
  avg_time?: number
  progress?: number
}

const agents = ref<AgentItem[]>([])
const agentStats = reactive<AgentStatsData>({
  total_calls: 0,
  success_rate: 0,
  avg_time: 0,
  by_agent: {}
})
const loading = ref(false)

// 日志
const showLogDrawer = ref(false)
const selectedAgentId = ref('')
const agentLogs = ref<AgentLogItem[]>([])
const logLoading = ref(false)

// 配置
const showConfigDrawer = ref(false)
const selectedAgent = ref<AgentItem | null>(null)
const configSaving = ref(false)
const agentConfig = reactive<AgentConfigData>({
  name: '',
  description: '',
  model: 'deepseek-chat',
  temperature: 0.7,
  max_tokens: 2048,
  system_prompt: '',
  enabled: true
})

const fetchAgents = async () => {
  loading.value = true
  try {
    const [agentRes, statsRes] = await Promise.all([
      adminApi.getAgentList(),
      adminApi.getAgentStats()
    ])
    agents.value = agentRes || []
    if (statsRes) {
      agentStats.total_calls = statsRes.total_calls || 0
      agentStats.success_rate = statsRes.success_rate || 0
      agentStats.avg_time = statsRes.avg_time || 0
      agentStats.by_agent = statsRes.by_agent || {}
    }
  } catch (e) {
    console.error('获取Agent列表失败', e)
  } finally {
    loading.value = false
  }
}

const startAgent = async (agentId: string) => {
  try {
    await adminApi.startAgent(agentId)
    message.success(`Agent ${agentId} 启动成功`)
    fetchAgents()
  } catch (e) {
    message.error('启动失败')
  }
}

const stopAgent = async (agentId: string) => {
  try {
    await adminApi.stopAgent(agentId)
    message.success(`Agent ${agentId} 已停止`)
    fetchAgents()
  } catch (e) {
    message.error('停止失败')
  }
}

const restartAgent = async (agentId: string) => {
  try {
    await adminApi.restartAgent(agentId)
    message.success(`Agent ${agentId} 重启成功`)
    fetchAgents()
  } catch (e) {
    message.error('重启失败')
  }
}

const viewAgentLogs = async (agentId: string) => {
  selectedAgentId.value = agentId
  showLogDrawer.value = true
  logLoading.value = true
  try {
    const res = await adminApi.getAgentLogs(agentId, { page: 1, page_size: 20 })
    agentLogs.value = res.items || []
  } catch (e) {
    console.error('获取日志失败', e)
  } finally {
    logLoading.value = false
  }
}

const openConfigDrawer = async (agent: AgentItem) => {
  selectedAgent.value = agent
  try {
    const res = await adminApi.getAgentConfig(agent.agent_id)
    agentConfig.name = res.name || agent.agent_name
    agentConfig.description = res.description || ''
    agentConfig.model = res.model || 'deepseek-chat'
    agentConfig.temperature = res.temperature ?? 0.7
    agentConfig.max_tokens = res.max_tokens || 2048
    agentConfig.system_prompt = res.system_prompt || ''
    agentConfig.enabled = res.enabled ?? true
  } catch (e) {
    console.error('获取配置失败', e)
    // 使用默认值
    agentConfig.name = agent.agent_name
    agentConfig.description = ''
    agentConfig.model = 'deepseek-chat'
    agentConfig.temperature = 0.7
    agentConfig.max_tokens = 2048
    agentConfig.system_prompt = ''
    agentConfig.enabled = true
  }
  showConfigDrawer.value = true
}

const saveAgentConfig = async () => {
  if (!selectedAgent.value) return
  configSaving.value = true
  try {
    await adminApi.updateAgentConfig(selectedAgent.value.agent_id, {
      name: agentConfig.name,
      description: agentConfig.description,
      model: agentConfig.model,
      temperature: agentConfig.temperature,
      max_tokens: agentConfig.max_tokens,
      system_prompt: agentConfig.system_prompt,
      enabled: agentConfig.enabled
    })
    message.success('配置保存成功')
    showConfigDrawer.value = false
    fetchAgents()
  } catch (e) {
    message.error('保存失败')
  } finally {
    configSaving.value = false
  }
}

const statusText = (s: string) => {
  if (s === 'completed' || s === '已完成') return '已完成'
  if (s === 'running' || s === '运行中') return '运行中'
  if (s === 'error' || s === '异常') return '异常'
  if (s === '已停用') return '已停用'
  return '空闲'
}

const getStatusClass = (s: string) => {
  if (s === 'completed' || s === '已完成') return 'completed'
  if (s === 'running' || s === '运行中') return 'running'
  if (s === 'error' || s === '异常') return 'error'
  return 'idle'
}

const getLogStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    completed: 'green',
    running: 'blue',
    error: 'red',
    timeout: 'orange'
  }
  return colors[status] || 'default'
}

const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 自动刷新
let refreshTimer: number
onMounted(() => {
  fetchAgents()
  refreshTimer = setInterval(fetchAgents, 30000) as unknown as number
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style lang="less" scoped>
.agents-view {
  padding: 0;
}

.agents-header {
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

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.2);
  background: transparent;
  color: #2563eb;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
  }
}

// 统计卡片
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  padding: 20px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  text-align: center;

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #2563eb;
    display: block;
  }

  .stat-label {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 6px;
  }
}

// Agent 卡片
.agent-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.agent-card {
  padding: 16px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 4px 16px rgba(76, 78, 100, 0.1);
    border-color: rgba(37, 99, 235, 0.15);
  }

  &.status-running {
    border-color: rgba(6, 182, 212, 0.3);
    box-shadow: 0 2px 12px rgba(6, 182, 212, 0.1);
  }

  &.status-completed {
    border-color: rgba(16, 185, 129, 0.25);
    box-shadow: 0 2px 12px rgba(16, 185, 129, 0.08);
  }

  &.status-error {
    border-color: rgba(239, 68, 68, 0.25);
    box-shadow: 0 2px 12px rgba(239, 68, 68, 0.08);
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.agent-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;

  .agent-icon {
    color: #fff;
  }
}

.agent-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.agent-status {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;

  &.completed { color: #10b981; }
  &.running { color: #06b6d4; }
  &.idle { color: #94a3b8; }
  &.error { color: #ef4444; }
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #06b6d4;
  box-shadow: 0 0 6px #06b6d4;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.card-body {
  margin-bottom: 12px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 12px;
  color: #94a3b8;
  width: 36px;
  font-weight: 500;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(37, 99, 235, 0.06);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  transition: width 0.4s;
}

.progress-val {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
  width: 36px;
  text-align: right;
}

.stats-row {
  display: flex;
  gap: 20px;
}

.mini-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mini-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.mini-value {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(37, 99, 235, 0.06);
}

// 日志抽屉
.log-filters {
  margin-bottom: 16px;
  font-size: 13px;
  color: #475569;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  padding: 12px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.04);
  border: 1px solid rgba(37, 99, 235, 0.08);

  &.error {
    background: rgba(239, 68, 68, 0.06);
    border-color: rgba(239, 68, 68, 0.1);
  }
}

.log-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.log-time {
  font-size: 12px;
  color: #94a3b8;
}

.log-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-row {
  display: flex;
  gap: 8px;
  font-size: 12px;

  .log-key {
    color: #94a3b8;
    min-width: 50px;
  }

  .log-val {
    color: #0f172a;
  }

  &.error .log-val {
    color: #ef4444;
  }
}

.log-data {
  flex: 1;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.04);
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0;
}

// 配置抽屉
.slider-value {
  margin-left: 12px;
  font-size: 13px;
  color: #2563eb;
  font-weight: 600;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  margin-top: 24px;
}
</style>