<template>
  <div class="agent-view page-container">
    <div class="page-header">
      <div class="page-header-icon">🤖</div>
      <div>
        <div class="page-header-title">多智能体协作面板</div>
        <div class="page-header-desc">7 个专职 Agent · 状态可视化 · 工作流监控</div>
      </div>
      <div class="header-right">
        <!-- 科目选择器 -->
        <div v-if="profileStore.profileData.subjectOverlays && profileStore.profileData.subjectOverlays.length > 1" class="subject-selector">
          <span class="subject-label">科目：</span>
          <select class="subject-select" :value="profileStore.profileData.currentSubject" @change="onSubjectChange">
            <option v-for="overlay in profileStore.profileData.subjectOverlays" :key="overlay.subject" :value="overlay.subject">
              {{ overlay.subject }}（{{ overlay.weak_points.length }}项薄弱）
            </option>
          </select>
        </div>
        <div class="legend-bar">
          <span class="legend-item"><span class="dot" style="background:#A8AAAE;"></span>空闲</span>
          <span class="legend-item"><span class="dot running"></span>执行中</span>
          <span class="legend-item"><span class="dot" style="background:#28C76F;box-shadow:0 0 4px rgba(40, 199, 111, 0.3);"></span>已完成</span>
        </div>
        <a-button
          type="primary"
          class="start-btn"
          :disabled="!profileReady || isRunning"
          @click="startTask"
        >{{ isRunning ? '运行中...' : '▶ 启动任务' }}</a-button>
      </div>
    </div>

    <!-- 画像未就绪提示 -->
    <div v-if="!profileReady" class="profile-notice">
      <div class="notice-icon">⚠️</div>
      <div class="notice-content">
        <div class="notice-title">画像尚未构建</div>
        <div class="notice-desc">请先完成画像采集对话，智能体将基于你的学习画像生成个性化资源</div>
        <a-button type="link" class="notice-link" @click="router.push('/profile')">前往画像采集 →</a-button>
      </div>
    </div>

    <!-- 画像已构建但未确认生效 -->
    <div v-else-if="profileStore.profileData.phase === 'initial' && profileReady" class="profile-notice" style="border-color: rgba(255, 159, 67, 0.3); background: rgba(255, 159, 67, 0.05);">
      <div class="notice-icon">💡</div>
      <div class="notice-content">
        <div class="notice-title">画像构建中，智能体已可运行</div>
        <div class="notice-desc">你可以在画像采集的同时启动智能体，它们将基于当前画像数据生成资源。确认画像后效果更精准。</div>
      </div>
    </div>

    <!-- 资源选择面板 -->
    <div v-if="profileReady && !isRunning" class="resource-selector">
      <div class="selector-header">
        <span class="selector-icon">📦</span>
        <span class="selector-title">选择需要生成的资源</span>
        <a-button type="link" size="small" @click="toggleSelectAll">{{ isAllSelected ? '取消全选' : '全选' }}</a-button>
      </div>
      <div class="selector-options">
        <label v-for="agent in selectableAgents" :key="agent.id" class="selector-item">
          <input type="checkbox" :checked="selectedAgents.includes(agent.index)" @change="toggleAgent(agent.index)" />
          <span class="agent-icon">{{ agent.icon }}</span>
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-role">{{ agent.role }}</span>
        </label>
      </div>
      <div class="selector-tip">
        已选择 {{ selectedAgents.length }} 个智能体，预计生成 {{ selectedAgents.length }} 类资源
      </div>
    </div>

    <div class="agent-main">
      <!-- 智能体错误状态提示 -->
      <div v-if="hasError" class="agent-error-notice">
        <div class="error-icon">❌</div>
        <div class="error-content">
          <div class="error-title">部分智能体执行失败</div>
          <!-- 显示具体错误详情 -->
          <div class="error-details" v-if="errorDetails.length > 0">
            <div v-for="(err, i) in errorDetails" :key="i" class="error-item">
              <div class="error-agent">{{ err.agentName }}</div>
              <div class="error-msg">{{ err.error }}</div>
              <div class="error-suggestion">💡 {{ err.suggestion }}</div>
            </div>
          </div>
          <div class="error-desc" v-else>请检查 API Key 配置或网络连接，然后重新启动任务</div>
        </div>
        <div class="error-actions">
          <a-button type="primary" size="small" @click="retryTask">重新启动</a-button>
          <a-button type="default" size="small" @click="clearErrors">清除错误</a-button>
        </div>
      </div>

      <div class="agent-grid">
        <AgentCard v-for="agent in agents" :key="agent.id" :agent="agent" />
      </div>
      <div class="right-panel">
        <!-- 进度时间提示 -->
        <div v-if="isRunning && estimatedRemainingTime > 0" class="time-estimate">
          <div class="time-icon">⏱️</div>
          <div class="time-content">
            <div class="time-label">预计剩余时间</div>
            <div class="time-value">{{ formatTime(estimatedRemainingTime) }}</div>
          </div>
          <div class="time-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${Math.min(100, Math.max(0, (1 - estimatedRemainingTime / totalEstimatedTime) * 100))}%` }"></div>
            </div>
          </div>
        </div>
        <WorkflowTimeline :stage="workflowStage" />
        <AgentLog :logs="logs" :isRunning="isRunning" @clear="store.clearLogs" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AgentCard from '../components/AgentCard.vue'
import AgentLog from '../components/AgentLog.vue'
import WorkflowTimeline from '../components/WorkflowTimeline.vue'
import { useAgentStore } from '../stores/agentStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { AGENT_LIST } from '../../../shared/utils/constants'
import { isCSSubject } from '../../../shared/utils/subjectFilter'

const router = useRouter()
const store = useAgentStore()
const profileStore = useProfileStore()
const agents = computed(() => store.agents)
const logs = computed(() => store.logs)
const workflowStage = computed(() => store.workflowStage)
const isRunning = computed(() => store.isRunning)
const profileReady = computed(() => store.profileReady)
const hasError = computed(() => store.agents.some(a => a.status === 'error' as const))
const errorDetails = computed(() => store.errorDetails)
const estimatedRemainingTime = computed(() => store.estimatedRemainingTime)
const totalEstimatedTime = computed(() => store.totalEstimatedTime)
const formatTime = store.formatTime

// 资源选择面板（非CS科目过滤掉代码Agent）
const isCurrentCS = computed(() => {
  const subject = profileStore.profileData.currentSubject || ''
  return isCSSubject(subject)
})
const selectableAgents = computed(() => {
  const base = AGENT_LIST.filter(a => a.id !== 'profile' && a.id !== 'reviewer')
  const filtered = isCurrentCS.value ? base : base.filter(a => a.id !== 'code')
  return filtered.map((a) => ({
    ...a,
    index: AGENT_LIST.findIndex(x => x.id === a.id),
  }))
})

// 默认全选
const selectedAgents = ref<number[]>(selectableAgents.value.map(a => a.index))

const isAllSelected = computed(() => selectedAgents.value.length === selectableAgents.value.length)

function toggleAgent(index: number) {
  const idx = selectedAgents.value.indexOf(index)
  if (idx > -1) {
    selectedAgents.value.splice(idx, 1)
  } else {
    selectedAgents.value.push(index)
  }
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedAgents.value = []
  } else {
    selectedAgents.value = selectableAgents.value.map(a => a.index)
  }
}

function onSubjectChange(e: Event) {
  const target = e.target as HTMLSelectElement
  profileStore.switchSubject(target.value)
}

function startTask() {
  // 传递选中的 Agent 索引（如果没选中任何，提示用户）
  if (selectedAgents.value.length === 0) {
    alert('请至少选择一个智能体')
    return
  }
  store.startTask(selectedAgents.value)
}

function retryTask() {
  store.resetAgents()
  store.startTask(selectedAgents.value)
}

function clearErrors() {
  store.clearErrors()
}
</script>

<style lang="less" scoped>
.agent-view {
  height: 100%;
  padding: 24px;
  overflow-y: auto;
  background: transparent;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  margin-bottom: 20px;
}

.page-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
}

.page-header-title {
  color: #1e293b;
}

.page-header-desc {
  color: #475569;
}

.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.subject-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subject-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.subject-select {
  font-size: 12px;
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.06));
  color: #1e293b;
  font-weight: 500;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;

  &:hover {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(6, 182, 212, 0.1));
  }

  &:focus {
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
  }

  option {
    background: white;
    color: #1e293b;
  }
}

.legend-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 11px;
  color: #475569;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.running {
    background: #06b6d4;
    box-shadow: 0 0 6px rgba(6, 182, 212, 0.5);
    animation: pulse 1.5s infinite;
  }
}

.start-btn {
  background: linear-gradient(135deg, #2563eb, #06b6d4) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06), 0 4px 12px rgba(37, 99, 235, 0.25) !important;
  font-weight: 600;
  font-size: 13px;
  border-radius: 10px;
  height: 36px;
  padding: 0 18px;
  color: #fff !important;
}

/* ===== 画像未就绪提示 ===== */
.profile-notice {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  margin-bottom: 20px;
  border-radius: 12px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.notice-icon { font-size: 28px; }

.notice-content { flex: 1; }

.notice-title {
  font-size: 14px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 6px;
}

.notice-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.notice-link {
  color: #2563eb !important;
  font-size: 12px !important;
  padding: 0 !important;
  height: auto !important;
  margin-top: 6px;
}

.agent-error-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.error-icon { font-size: 20px; margin-top: 2px; }

.error-content { flex: 1; min-width: 0; }

.error-title {
  font-size: 13px;
  font-weight: 600;
  color: #ef4444;
}

.error-details {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-item {
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.1);
}

.error-agent {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}

.error-msg {
  font-size: 11px;
  color: #ef4444;
  margin-top: 2px;
}

.error-suggestion {
  font-size: 11px;
  color: #059669;
  margin-top: 4px;
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-desc {
  font-size: 12px;
  color: #475569;
  margin-top: 2px;
}

/* ===== 资源选择面板 ===== */
.resource-selector {
  margin-bottom: 20px;
  padding: 20px 24px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px) saturate(1.4);
  border: 1px solid rgba(37, 99, 235, 0.15);
  box-shadow: 0 4px 16px rgba(76, 78, 100, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
}

.selector-icon {
  font-size: 20px;
  filter: drop-shadow(0 2px 4px rgba(37, 99, 235, 0.2));
}

.selector-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0.02em;
}

.selector-options {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.selector-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.12);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 13px;
  position: relative;

  &:hover {
    background: rgba(37, 99, 235, 0.15);
    border-color: rgba(37, 99, 235, 0.25);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
  }

  &:has(input:checked) {
    background: rgba(37, 99, 235, 0.18);
    border-color: rgba(37, 99, 235, 0.3);
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.08);
  }

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    accent-color: #2563eb;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;

    &:checked {
      background: #2563eb;
    }
  }
}

.agent-icon {
  font-size: 16px;
  min-width: 24px;
  text-align: center;
}

.agent-name {
  color: #1e293b;
  font-weight: 600;
  font-size: 13.5px;
}

.agent-role {
  color: #64748b;
  font-size: 12px;
  margin-left: 4px;
}

.selector-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(37, 99, 235, 0.06);
  border-radius: 8px;
  font-size: 13px;
  color: #2563eb;
  font-weight: 600;

  &::before {
    content: '💡';
    font-size: 14px;
  }
}

.agent-main {
  display: flex;
  gap: 0;
  height: calc(100% - 100px);
}

.agent-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  padding-right: 16px;
  overflow: auto;
  align-content: start;
}

/* ===== 时间预估提示 ===== */
.time-estimate {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  margin: 8px 12px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.time-icon {
  font-size: 16px;
}

.time-content {
  flex: 1;
}

.time-label {
  font-size: 11px;
  color: #64748b;
}

.time-value {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.time-progress {
  width: 50px;
}

.progress-bar {
  height: 4px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border-radius: 2px;
  transition: width 1s linear;
}

.right-panel {
  width: 320px;
  border-left: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (max-width: 1200px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .agent-main {
    flex-direction: column;
    height: auto;
  }
  .agent-grid {
    grid-template-columns: 1fr;
    padding-right: 0;
  }
  .right-panel {
    width: 100%;
    border-left: none;
    border-top: 1px solid rgba(37, 99, 235, 0.1);
    max-height: 300px;
  }
  .page-header {
    flex-wrap: wrap;
  }
  .header-right {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
