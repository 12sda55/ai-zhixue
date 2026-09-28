<template>
  <div class="assess-report">
    <!-- 薄弱点分析 -->
    <div class="report-section weakness">
      <div class="section-header">
        <span class="section-icon">⚡</span>
        <span class="section-title">薄弱点分析</span>
      </div>
      <div class="weak-grid">
        <div v-for="w in weakPoints" :key="w.name" class="weak-card">
          <div class="weak-name">{{ w.name }}</div>
          <div class="weak-bar">
            <div class="bar-fill" :style="{ width: w.score + '%', background: `linear-gradient(90deg, ${w.color}88, ${w.color})` }"></div>
          </div>
          <div class="weak-score" :style="{ color: w.color }">{{ w.score }}%</div>
          <div class="weak-gap">距目标差 <span :style="{ color: w.color }">{{ 80 - w.score }}%</span></div>
        </div>
      </div>
    </div>

    <!-- 优势模块 -->
    <div class="report-section strength">
      <div class="section-header">
        <span class="section-icon">✅</span>
        <span class="section-title">优势模块</span>
      </div>
      <div class="strength-list">
        <div v-for="m in strongModules" :key="m.name" class="strength-item">
          <span class="strength-dot" :style="{ background: m.color }"></span>
          <span>{{ m.name }}：{{ m.score }}%，掌握扎实</span>
        </div>
      </div>
    </div>

    <!-- 优化建议 -->
    <div class="report-section suggestion">
      <div class="section-header">
        <span class="section-icon">🔄</span>
        <span class="section-title">优化建议</span>
      </div>
      <div class="suggestion-list">
        <div v-for="(s, i) in suggestions" :key="i" class="suggestion-item">
          <span class="s-num">{{ i + 1 }}</span>
          <span>{{ s }}</span>
        </div>
      </div>
    </div>

    <div class="loop-hint">
      ↻ 评估数据已反馈至画像，学习路径已自动调整
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessModule } from '../../../shared/types'

const props = defineProps<{
  modules: AssessModule[]
  weakPoints: AssessModule[]
}>()

const strongModules = computed(() => props.modules.filter(m => m.score >= 70))

const suggestions = computed(() => {
  const list: string[] = []
  for (const w of props.weakPoints) {
    list.push(`优先补强「${w.name}」(${w.score}%)，配合专项练习`)
  }
  if (props.weakPoints.length > 1) {
    list.push('薄弱模块建议交替学习，避免疲劳')
  }
  list.push('每日学习时长建议提至 2.5h')
  return list
})
</script>

<style lang="less" scoped>
.assess-report {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-section {
  border-radius: 12px;
  padding: 14px 16px;
  backdrop-filter: blur(10px);

  &.weakness {
    background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.03));
    border: 1px solid rgba(245,158,11,0.12);
  }
  &.strength {
    background: linear-gradient(135deg, rgba(52,211,153,0.08), rgba(52,211,153,0.03));
    border: 1px solid rgba(52,211,153,0.12);
  }
  &.suggestion {
    background: linear-gradient(135deg, rgba(0,212,255,0.08), rgba(0,212,255,0.03));
    border: 1px solid rgba(0,212,255,0.12);
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.section-icon { font-size: 14px; }

.section-title {
  font-size: 12px;
  font-weight: 600;
  .weakness & { color: #f59e0b; }
  .strength & { color: #34d399; }
  .suggestion & { color: #00d4ff; }
}

.weak-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weak-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.06);
}

.weak-name {
  color: #e8f4fd;
  font-size: 11px;
  font-weight: 600;
  width: 40px;
}

.weak-bar {
  flex: 1;
  height: 4px;
  background: rgba(0, 212, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;
  box-shadow: 0 0 4px rgba(0, 212, 255, 0.2);
}

.weak-score { font-size: 12px; font-weight: 700; width: 36px; }

.weak-gap { color: #5a7a8a; font-size: 9px; }

.strength-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.strength-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #34d399;
  font-size: 11px;
}

.strength-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: #7eb8d0;
  font-size: 11px;
  line-height: 1.6;
}

.s-num {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 600;
  flex-shrink: 0;
}

.loop-hint {
  background: rgba(0,212,255,0.04);
  border-radius: 8px;
  padding: 8px 10px;
  border: 1px dashed rgba(0,212,255,0.15);
  color: #00d4ff;
  font-size: 9px;
  text-align: center;
}
</style>