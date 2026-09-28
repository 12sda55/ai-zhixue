<template>
  <div class="profile-card">
    <!-- 薄弱知识点 -->
    <div class="card-section weak-section">
      <div class="section-header">
        <span class="section-bar" style="background: #FF9F43;"></span>
        <span class="section-title">⚡ 薄弱知识点</span>
        <span class="section-count">{{ data.weak_points.length }} 项</span>
      </div>
      <div class="weak-tags" v-if="data.weak_points.length">
        <span v-for="wp in data.weak_points" :key="wp" class="weak-tag">
          {{ wp }}
        </span>
      </div>
      <div v-else class="no-weak">暂无明显薄弱点</div>
    </div>

    <!-- 学习偏好 -->
    <div class="card-section pref-section">
      <div class="section-header">
        <span class="section-bar" style="background: #7367F0;"></span>
        <span class="section-title">🎯 学习偏好</span>
      </div>
      <div class="pref-list">
        <div class="pref-row">
          <span class="pref-icon">🎯</span>
          <span class="pref-label">学习目标</span>
          <span class="pref-value">{{ data.study_goal }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-icon">🧠</span>
          <span class="pref-label">认知风格</span>
          <span class="pref-value">{{ data.cognitive_style }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-icon">⏱️</span>
          <span class="pref-label">学习节奏</span>
          <span class="pref-value">{{ data.study_rhythm }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-icon">🎨</span>
          <span class="pref-label">内容偏好</span>
          <span class="pref-value">{{ data.interest_preference }}</span>
        </div>
      </div>
    </div>

    <!-- 基础水平 -->
    <div class="card-section level-section">
      <div class="section-header">
        <span class="section-bar" style="background: #00CFE8;"></span>
        <span class="section-title">💡 基础水平</span>
      </div>
      <div class="level-row">
        <span class="level-meta">{{ data.major }} · {{ data.grade }}</span>
      </div>
      <div class="level-track">
        <div class="level-fill" :style="{ width: baseLevelPercent + '%' }" />
        <div class="level-marker" :style="{ left: baseLevelPercent + '%' }">
          <div class="marker-dot" />
          <span class="marker-label">{{ data.base_level }}</span>
        </div>
      </div>
      <div class="level-labels">
        <span>入门</span><span>基础</span><span>中等</span><span>进阶</span><span>精通</span>
      </div>
    </div>

    <!-- 学习统计 -->
    <div class="card-section stats-section">
      <div class="section-header">
        <span class="section-bar" style="background: #28C76F;"></span>
        <span class="section-title">📊 学习统计</span>
      </div>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-num">{{ totalStudyDays }}</span>
          <span class="stat-label">学习天数</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ totalHours }}h</span>
          <span class="stat-label">累计学时</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ completedResources }}</span>
          <span class="stat-label">完成资源</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ streakDays }}🔥</span>
          <span class="stat-label">连续学习</span>
        </div>
      </div>
    </div>

    <!-- 能力标签 -->
    <div class="card-section tags-section">
      <div class="section-header">
        <span class="section-bar" style="background: #9E94FF;"></span>
        <span class="section-title">🏷️ 能力标签</span>
      </div>
      <div class="ability-tags">
        <span v-for="tag in abilityTags" :key="tag" class="ability-tag" :class="getTagClass(tag)">
          {{ tag }}
        </span>
      </div>
    </div>

    <!-- 学习建议 -->
    <div class="card-section advice-section">
      <div class="section-header">
        <span class="section-bar" style="background: #F59E0B;"></span>
        <span class="section-title">💡 智能建议</span>
      </div>
      <div class="advice-list">
        <div class="advice-item">
          <span class="advice-icon">🎯</span>
          <div class="advice-content">
            <span class="advice-title">重点提升</span>
            <span class="advice-text">建议优先学习{{ weakestDimension }}相关内容</span>
          </div>
        </div>
        <div class="advice-item">
          <span class="advice-icon">📚</span>
          <div class="advice-content">
            <span class="advice-title">推荐资源</span>
            <span class="advice-text">根据您的偏好，推荐{{ recommendedResource }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProfileData } from '../../../shared/types'

const props = defineProps<{
  data: ProfileData
}>()

const levelMap: Record<string, number> = {
  '入门': 10,
  '基础': 30,
  '中等': 55,
  '进阶': 75,
  '精通': 95,
}

const baseLevelPercent = computed(() => levelMap[props.data.base_level] ?? 50)

// 学习统计 — 使用画像持久化的真实数据
const totalStudyDays = computed(() => {
  return props.data.streakDays || Math.round((props.data.dimensions.find(d => d.key === 'study_rhythm')?.value || 30) * 1.2)
})

const totalHours = computed(() => {
  const minutes = props.data.totalStudyMinutes
  if (minutes > 0) return Math.round(minutes / 60 * 10) / 10
  return Math.round((props.data.dimensions.find(d => d.key === 'study_rhythm')?.value || 30) * 0.8)
})

const completedResources = computed(() => {
  return props.data.completedResourceCount || Math.round((props.data.dimensions.find(d => d.key === 'interest_preference')?.value || 30) * 0.5)
})

const streakDays = computed(() => {
  return props.data.streakDays || Math.max(1, Math.round((props.data.dimensions.find(d => d.key === 'study_rhythm')?.value || 30) * 0.3))
})

// 能力标签
const abilityTags = computed(() => {
  const tags: string[] = []
  if (props.data.cognitive_style === '实践型') tags.push('动手能力强')
  if (props.data.study_goal === '全面掌握') tags.push('追求卓越')
  if (props.data.study_rhythm === '适中节奏') tags.push('稳扎稳打')
  if (props.data.interest_preference === '代码实操') tags.push('编程达人')
  if (props.data.base_level === '中等' || props.data.base_level === '进阶') tags.push('基础扎实')
  return tags.length ? tags : ['潜力无限', '勤奋好学', '积极进取']
})

function getTagClass(tag: string): string {
  const map: Record<string, string> = {
    '动手能力强': 'tag-blue',
    '追求卓越': 'tag-purple',
    '稳扎稳打': 'tag-green',
    '编程达人': 'tag-cyan',
    '基础扎实': 'tag-green',
    '潜力无限': 'tag-purple',
    '勤奋好学': 'tag-orange',
    '积极进取': 'tag-cyan',
  }
  return map[tag] || 'tag-default'
}

// 智能建议（只看雷达图上的维度）
const weakestDimension = computed(() => {
  const dims = props.data.dimensions.filter(d => d.value > 0 && d.showOnRadar !== false)
  if (!dims.length) return props.data.currentSubject || props.data.major || '综合学习'
  const minDim = dims.reduce((min, d) => d.value < min.value ? d : min)
  return minDim.name
})

const recommendedResource = computed(() => {
  const pref = props.data.interest_preference
  const map: Record<string, string> = {
    '代码实操': '实践项目练习',
    '理论知识': '深度解析文档',
    '视频教程': '精品视频课程',
    '思维导图': '知识图谱资源',
  }
  return map[pref] || '相关学习资源'
})
</script>

<style lang="less" scoped>
.profile-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-section {
  padding: 14px 16px;
  background: #F8F7FA;
  border-radius: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.section-bar {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  flex-shrink: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #2F2B3D;
}

.section-count {
  margin-left: auto;
  font-size: 11px;
  color: #FF9F43;
  background: rgba(255, 159, 67, 0.12);
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 500;
}

/* ===== 薄弱知识点 ===== */
.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #FF9F43;
  background: rgba(255, 159, 67, 0.12);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 159, 67, 0.2);
  }
}

.no-weak {
  font-size: 12px;
  color: #28C76F;
  font-weight: 500;
}

/* ===== 学习偏好 ===== */
.pref-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pref-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 8px;
  background: transparent;
}

.pref-icon { font-size: 14px; }
.pref-label { font-size: 12px; color: #6E6B7B; min-width: 60px; font-weight: 500; }
.pref-value { font-size: 13px; color: #2F2B3D; font-weight: 600; }

/* ===== 基础水平 ===== */
.level-row {
  margin-bottom: 8px;
}

.level-meta {
  font-size: 12px;
  color: #5E5873;
  font-weight: 500;
}

.level-track {
  position: relative;
  height: 8px;
  background: #EBE9F1;
  border-radius: 4px;
  overflow: visible;
}

.level-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #00CFE8, #7367F0);
  transition: width 0.5s ease;
}

.level-marker {
  position: absolute;
  top: -8px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: left 0.5s ease;
}

.marker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #7367F0;
  border: 2px solid #FFFFFF;
  box-shadow: 0 2px 4px rgba(115, 103, 240, 0.3);
}

.marker-label {
  font-size: 10px;
  color: #7367F0;
  font-weight: 600;
  background: rgba(115, 103, 240, 0.12);
  padding: 2px 8px;
  border-radius: 6px;
}

.level-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  span { font-size: 11px; color: #A8AAAE; font-weight: 500; }
}

/* ===== 学习统计 ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background: transparent;
  border-radius: 8px;
}

.stat-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #2F2B3D;
}

.stat-label {
  font-size: 11px;
  color: #A8AAAE;
  margin-top: 2px;
  display: block;
}

/* ===== 能力标签 ===== */
.ability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ability-tag {
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  
  &.tag-default {
    background: rgba(115, 103, 240, 0.12);
    color: #7367F0;
  }
  
  &.tag-blue {
    background: rgba(59, 130, 246, 0.12);
    color: #3B82F6;
  }
  
  &.tag-purple {
    background: rgba(115, 103, 240, 0.12);
    color: #7367F0;
  }
  
  &.tag-green {
    background: rgba(40, 199, 111, 0.12);
    color: #28C76F;
  }
  
  &.tag-cyan {
    background: rgba(0, 207, 232, 0.12);
    color: #00CFE8;
  }
  
  &.tag-orange {
    background: rgba(255, 159, 67, 0.12);
    color: #FF9F43;
  }
}

/* ===== 智能建议 ===== */
.advice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  background: transparent;
  border-radius: 8px;
}

.advice-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.advice-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.advice-title {
  font-size: 12px;
  font-weight: 600;
  color: #2F2B3D;
}

.advice-text {
  font-size: 12px;
  color: #6E6B7B;
  line-height: 1.4;
}
</style>
