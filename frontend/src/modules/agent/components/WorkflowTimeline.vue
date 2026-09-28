<template>
  <div class="workflow-timeline">
    <div class="timeline-title">⚡ 工作流</div>
    <div class="timeline-list">
      <div v-for="(step, i) in steps" :key="i" class="timeline-step">
        <div class="step-line">
          <div class="step-dot" :class="step.dotClass">
            <template v-if="step.status === 'completed'">✓</template>
            <template v-else-if="step.status === 'running'"><span class="inner-pulse"></span></template>
            <template v-else>{{ i + 1 }}</template>
          </div>
          <div v-if="i < steps.length - 1" class="step-connector" :class="step.connectorClass"></div>
        </div>
        <div class="step-content">
          <div class="step-title" :class="step.textClass">{{ step.title }}</div>
          <div class="step-desc">{{ step.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ stage: number }>()

const steps = computed(() => [
  {
    title: '画像构建',
    desc: props.stage >= 1 ? '2.3s · 8维画像已更新' : '等待启动',
    status: props.stage >= 1 ? 'completed' : 'pending',
    dotClass: props.stage >= 1 ? 'dot-completed' : 'dot-pending',
    connectorClass: props.stage >= 1 ? 'conn-active' : 'conn-pending',
    textClass: props.stage >= 1 ? 'text-completed' : 'text-pending',
  },
  {
    title: '资源并行生成',
    desc: props.stage >= 2 ? '文档·导图·题库 执行中...' : '等待画像完成',
    status: props.stage >= 2 ? 'running' : 'pending',
    dotClass: props.stage >= 2 ? 'dot-running' : 'dot-pending',
    connectorClass: props.stage >= 2 ? 'conn-running' : 'conn-pending',
    textClass: props.stage >= 2 ? 'text-running' : 'text-pending',
  },
  {
    title: '代码·视频生成',
    desc: props.stage >= 3 ? '执行中...' : '排队等待中',
    status: props.stage >= 3 ? 'running' : 'pending',
    dotClass: props.stage >= 3 ? 'dot-running' : 'dot-pending',
    connectorClass: props.stage >= 3 ? 'conn-running' : 'conn-pending',
    textClass: props.stage >= 3 ? 'text-running' : 'text-pending',
  },
  {
    title: '路径规划',
    desc: props.stage >= 4 ? '汇总资源...' : '等待资源汇总',
    status: props.stage >= 4 ? 'running' : 'pending',
    dotClass: props.stage >= 4 ? 'dot-running' : 'dot-pending',
    textClass: props.stage >= 4 ? 'text-running' : 'text-pending',
  },
])
</script>

<style lang="less" scoped>
.workflow-timeline {
  padding: 14px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.06);
}

.timeline-title {
  color: #e8f4fd;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
}

.timeline-step {
  display: flex;
  gap: 8px;
}

.step-line {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: bold;
  flex-shrink: 0;

  &.dot-completed {
    background: #34d399;
    box-shadow: 0 0 6px rgba(52, 211, 153, 0.4);
    color: #0a0e27;
  }
  &.dot-running {
    background: #00d4ff;
    box-shadow: 0 0 6px rgba(0, 212, 255, 0.4);
  }
  &.dot-pending {
    border: 1.5px dashed #64748b;
    color: #64748b;
  }
}

.inner-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0a0e27;
  animation: pulse 1s infinite;
}

.step-connector {
  width: 2px;
  flex: 1;
  min-height: 8px;

  &.conn-active { background: rgba(52, 211, 153, 0.3); }
  &.conn-running { background: rgba(0, 212, 255, 0.15); }
  &.conn-pending { background: rgba(0, 212, 255, 0.06); }
}

.step-content {
  padding-bottom: 8px;
}

.step-title {
  font-size: 10px;
  font-weight: 600;

  &.text-completed { color: #34d399; }
  &.text-running { color: #00d4ff; }
  &.text-pending { color: #64748b; }
}

.step-desc {
  color: #5a7a8a;
  font-size: 9px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>