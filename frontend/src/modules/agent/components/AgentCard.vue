<template>
  <div class="agent-card" :class="[`status-${agent.status}`, `color-${agent.id}`]">
    <div class="status-badge">
      <template v-if="agent.status === 'completed'">
        <span class="badge-icon">✓</span> 完成
      </template>
      <template v-else-if="agent.status === 'running'">
        <span class="badge-pulse"></span> 运行中
      </template>
      <template v-else>
        空闲
      </template>
    </div>
    <div class="card-header">
      <div class="agent-avatar">{{ agent.icon }}</div>
      <div class="agent-info">
        <div class="agent-name">{{ agent.name }}</div>
        <div class="agent-role">{{ agent.role }}</div>
      </div>
    </div>
    <div class="agent-log-area">
      <template v-if="agent.status === 'completed'">
        <div class="log-success">✓ {{ agent.name }} 完成</div>
        <div class="log-time">{{ agent.duration || '' }}</div>
      </template>
      <template v-else-if="agent.status === 'running'">
        <div class="log-running">⟳ {{ agent.log[0] || '处理中...' }}</div>
        <div class="log-progress">进度 {{ agent.progress }}%</div>
      </template>
      <template v-else>
        <div class="log-idle">等待任务分配...</div>
      </template>
    </div>
    <div v-if="agent.status === 'running'" class="progress-bar">
      <div class="progress-fill" :style="{ width: agent.progress + '%' }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentInfo } from '../../../shared/types'

defineProps<{ agent: AgentInfo }>()
</script>

<style lang="less" scoped>
.agent-card {
  border-radius: 12px;
  padding: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;

  &.status-idle {
    background: transparent;
    border: 1px solid #EBE9F1;
    box-shadow: 0 2px 6px rgba(76, 78, 100, 0.06);

    .agent-avatar { background: transparent; opacity: 0.5; }
    .agent-name { color: #A8AAAE; }
    .agent-role { color: #D8D6DE; }
  }

  &.status-running {
    background: transparent;
    border: 1px solid rgba(0, 207, 232, 0.25);
    box-shadow: 0 2px 10px rgba(0, 207, 232, 0.1);

    &.color-document { border-color: rgba(0, 207, 232, 0.3); }
    &.color-mindmap { border-color: rgba(40, 199, 111, 0.3); }
    &.color-exercise { border-color: rgba(115, 103, 240, 0.3); }
  }

  &.status-completed {
    background: transparent;
    border: 1px solid rgba(40, 199, 111, 0.2);
    box-shadow: 0 2px 10px rgba(40, 199, 111, 0.08);
  }
}

.status-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px 10px;
  border-radius: 6px;

  .status-idle & { color: #A8AAAE; background: transparent; }
  .status-running & { color: #00CFE8; background: rgba(0, 207, 232, 0.1); }
  .status-completed & { color: #28C76F; background: rgba(40, 199, 111, 0.1); }
}

.badge-pulse {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #00CFE8;
  animation: pulse 1s infinite;
  box-shadow: 0 0 4px #00CFE8;
}

.badge-icon {
  font-size: 10px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;

  .status-running & { box-shadow: 0 0 10px rgba(0, 207, 232, 0.3); }
  .status-completed & { background: linear-gradient(135deg, #28C76F, #10B981); box-shadow: 0 0 8px rgba(40, 199, 111, 0.25); }

  .color-profile.status-running &,
  .color-profile.status-completed & { background: linear-gradient(135deg, #28C76F, #10B981); }
  .color-document.status-running & { background: linear-gradient(135deg, #00CFE8, #0891B2); }
  .color-mindmap.status-running & { background: linear-gradient(135deg, #28C76F, #10B981); }
  .color-exercise.status-running & { background: linear-gradient(135deg, #7367F0, #5F51E8); }
}

.agent-info {
  .agent-name {
    color: #2F2B3D;
    font-size: 13px;
    font-weight: 600;
  }
  .agent-role {
    color: #6E6B7B;
    font-size: 11px;
  }
}

.agent-log-area {
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 11px;
  font-family: 'Cascadia Code', Consolas, monospace;

  .status-idle & { border: 1px solid #EBE9F1; }
  .status-running & { border: 1px solid rgba(0, 207, 232, 0.15); }
  .status-completed & { border: 1px solid rgba(40, 199, 111, 0.15); }
}

.log-success { color: #28C76F; font-weight: 500; }
.log-time { color: #A8AAAE; }
.log-running { color: #00CFE8; font-weight: 500; }
.log-progress { color: #6E6B7B; }
.log-idle { color: #A8AAAE; }

.progress-bar {
  margin-top: 8px;
  height: 4px;
  background: rgba(37, 99, 235, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #00CFE8, #0891B2);
  box-shadow: 0 0 6px rgba(0, 207, 232, 0.3);
  transition: width 0.3s;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
