<template>
  <div class="gallery-detail-view">
    <!-- 返回按钮 -->
    <button class="btn-back" @click="goBack">
      <span class="back-arrow">←</span>
      返回展馆
    </button>

    <div v-if="snapshot" class="detail-content">
      <!-- 标题 + 操作 -->
      <div class="detail-header">
        <div class="detail-title-row">
          <h1 class="detail-title">
            <span v-if="snapshot.isPerfect" class="perfect-badge">⭐</span>
            {{ snapshot.title }}
          </h1>
          <button class="btn-delete" @click="handleDelete">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4h9.34z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            删除画作
          </button>
        </div>
        <p v-if="snapshot.description" class="detail-desc">{{ snapshot.description }}</p>
        <span class="detail-date">{{ formatDate(snapshot.createdAt) }}</span>
      </div>

      <!-- 用户画像摘要（专业、年级等） -->
      <div class="profile-summary">
        <div v-if="snapshot.subject" class="summary-item">
          <span class="summary-icon">📖</span>
          <span class="summary-label">科目</span>
          <span class="summary-value">{{ snapshot.subject }}</span>
        </div>
        <div v-if="snapshot.subject" class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-icon">🎓</span>
          <span class="summary-label">专业</span>
          <span class="summary-value">{{ snapshot.profileData.major || '未设置' }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-icon">📊</span>
          <span class="summary-label">年级</span>
          <span class="summary-value">{{ snapshot.profileData.grade || '未设置' }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-icon">💡</span>
          <span class="summary-label">基础水平</span>
          <span class="summary-value">{{ snapshot.profileData.base_level || '未评估' }}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-icon">🎯</span>
          <span class="summary-label">学习目标</span>
          <span class="summary-value">{{ snapshot.profileData.study_goal || '未设置' }}</span>
        </div>
      </div>

      <!-- 雷达图对比区 -->
      <div class="radar-compare">
        <!-- 初始画像 -->
        <div class="radar-panel">
          <h3 class="panel-label">初始画像</h3>
          <div class="radar-chart-wrapper">
            <MiniRadarChart
              v-if="initialDimensions.length > 0"
              :dimensions="initialDimensions"
              :size="280"
              :show-axis-name="true"
            />
            <div v-else class="radar-empty">暂无初始数据</div>
          </div>
          <div class="radar-score-label">
            <span class="score-value">{{ initialTotalScore }}</span>
            <span class="score-unit">总分（满分 800）</span>
          </div>
          <div class="radar-dims">
            <div
              v-for="dim in initialDimensions"
              :key="dim.key"
              class="dim-row"
            >
              <span class="dim-icon">{{ DIMENSION_META[dim.key as ProfileAllDimensionKey]?.icon || FALLBACK_DIM[dim.key]?.icon }}</span>
              <span class="dim-name">{{ dim.name }}</span>
              <div class="dim-bar-track">
                <div
                  class="dim-bar-fill"
                  :style="{ width: `${dim.value}%`, background: `linear-gradient(90deg, ${DIMENSION_META[dim.key as ProfileAllDimensionKey]?.color || FALLBACK_DIM[dim.key]?.icon ? '#2563eb' : '#2563eb'}, ${DIMENSION_META[dim.key as ProfileAllDimensionKey]?.color ?? '#06b6d4'}88)` }"
                ></div>
              </div>
              <span class="dim-value">{{ dim.value }}</span>
            </div>
          </div>
        </div>

        <!-- VS 分隔 -->
        <div class="vs-divider">
          <div class="vs-line"></div>
          <span class="vs-text">VS</span>
          <div class="vs-line"></div>
          <div class="vs-growth">
            <span class="vs-growth-icon">📈</span>
            <span class="vs-growth-value">+{{ snapshot.growthFromInitial }}</span>
          </div>
        </div>

        <!-- 保存时画像 -->
        <div class="radar-panel" :class="{ 'radar-panel--perfect': snapshot.isPerfect }">
          <h3 class="panel-label">保存时画像</h3>
          <div class="radar-chart-wrapper">
            <MiniRadarChart
              :dimensions="savedDimensions"
              :size="280"
              :show-axis-name="true"
            />
          </div>
          <div class="radar-score-label">
            <span class="score-value">{{ snapshot.totalScore }}</span>
            <span class="score-unit">总分（满分 800）</span>
          </div>
          <div class="radar-dims">
            <div
              v-for="dim in savedDimensions"
              :key="dim.key"
              class="dim-row"
              :class="{ 'dim-row--improved': getDimGrowth(dim.key) > 0 }"
            >
              <span class="dim-icon">{{ DIMENSION_META[dim.key as ProfileAllDimensionKey]?.icon || FALLBACK_DIM[dim.key]?.icon }}</span>
              <span class="dim-name">{{ dim.name }}</span>
              <div class="dim-bar-track">
                <div
                  class="dim-bar-fill"
                  :style="{ width: `${dim.value}%`, background: `linear-gradient(90deg, ${DIMENSION_META[dim.key as ProfileAllDimensionKey]?.color ?? '#2563eb'}, ${DIMENSION_META[dim.key as ProfileAllDimensionKey]?.color ?? '#06b6d4'}88)` }"
                ></div>
              </div>
              <span class="dim-value">{{ dim.value }}</span>
              <span v-if="getDimGrowth(dim.key) > 0" class="dim-growth">+{{ getDimGrowth(dim.key) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 成长数字 -->
      <div class="growth-stats">
        <div class="growth-stat-card">
          <span class="growth-stat-icon">📈</span>
          <span class="growth-stat-value">{{ snapshot.growthFromInitial }}</span>
          <span class="growth-stat-label">总提升分</span>
        </div>
        <div class="growth-stat-card">
          <span class="growth-stat-icon">⏱️</span>
          <span class="growth-stat-value">{{ formatMinutes(snapshot.summary.studyMinutes) }}</span>
          <span class="growth-stat-label">学习时长</span>
        </div>
        <div class="growth-stat-card">
          <span class="growth-stat-icon">✅</span>
          <span class="growth-stat-value">{{ snapshot.summary.completedStages }}</span>
          <span class="growth-stat-label">完成阶段</span>
        </div>
        <div class="growth-stat-card">
          <span class="growth-stat-icon">💡</span>
          <span class="growth-stat-value">{{ masteredWeakPoints }}</span>
          <span class="growth-stat-label">掌握薄弱点</span>
        </div>
      </div>

      <!-- 学习经历 -->
      <div class="learning-journey">
        <div class="journey-header">
          <h2 class="journey-title">📚 学习经历</h2>
          <span class="journey-count">共 {{ learningEvents.length }} 条记录</span>
        </div>
        <div v-if="learningEvents.length > 0" class="journey-timeline">
          <div
            v-for="(event, idx) in learningEvents"
            :key="idx"
            class="timeline-item"
          >
            <div class="timeline-dot" :class="eventDotClass(event.type)"></div>
            <div class="timeline-line" v-if="idx < learningEvents.length - 1"></div>
            <div class="timeline-content">
              <div class="timeline-badge" :class="eventBadgeClass(event.type)">
                {{ eventLabel(event.type) }}
              </div>
              <div class="timeline-desc">{{ event.description }}</div>
              <div v-if="event.knowledgePoints?.length" class="timeline-kps">
                <span v-for="kp in event.knowledgePoints.slice(0, 3)" :key="kp" class="kp-tag">{{ kp }}</span>
                <span v-if="event.knowledgePoints.length > 3" class="kp-more">+{{ event.knowledgePoints.length - 3 }}</span>
              </div>
              <span class="timeline-time">{{ formatDate(event.timestamp) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="journey-empty">
          <span class="empty-icon">📝</span>
          <p class="empty-text">暂无学习记录</p>
          <p class="empty-hint">开始学习后，你的学习经历将在此展示</p>
        </div>
      </div>
    </div>

    <!-- 快照未找到 -->
    <div v-else class="not-found">
      <div class="not-found-icon">🔍</div>
      <p class="not-found-text">画作未找到</p>
      <button class="btn-back-inline" @click="goBack">返回展馆</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGalleryStore } from '../stores/galleryStore'
import { message } from 'ant-design-vue'
import type { ProfileAllDimensionKey, LearningEvent } from '../../../shared/types'
import { DIMENSION_META } from '../../../shared/types'
import MiniRadarChart from '../components/MiniRadarChart.vue'

const route = useRoute()
const router = useRouter()
const galleryStore = useGalleryStore()

onMounted(() => {
  galleryStore.loadSnapshots()
  const id = route.params.id as string
  if (id) {
    galleryStore.setCurrentSnapshot(id)
  }
})

const snapshot = computed(() => galleryStore.currentSnapshot)

/** 雷达图维度（仅 showOnRadar） */
const savedDimensions = computed(() => {
  if (!snapshot.value) return []
  return snapshot.value.dimensions.filter(dim => {
    const meta = DIMENSION_META[dim.key as ProfileAllDimensionKey]
    return meta?.showOnRadar
  })
})

/** 维度 key → 图标+名称 硬编码兜底表 */
const FALLBACK_DIM: Record<string, { icon: string; name: string }> = {
  base_level: { icon: '💡', name: '基础水平' },
  weak_points: { icon: '⚡', name: '薄弱知识点' },
  study_goal: { icon: '🎯', name: '学习目标' },
  learning_engagement: { icon: '🔥', name: '学习投入度' },
  study_rhythm: { icon: '⏱️', name: '学习节奏' },
  interest_preference: { icon: '🎨', name: '内容偏好' },
  knowledge_mastery: { icon: '📚', name: '知识掌握度' },
  exercise_completion: { icon: '✅', name: '练习完成度' },
  major: { icon: '🎓', name: '专业方向' },
  grade: { icon: '📊', name: '年级水平' },
  cognitive_style: { icon: '🧠', name: '认知风格' },
}

/** 为初始快照维度补全 name/label（兼容旧数据只有 key+value 的情况） */
function enrichDim(dim: { key: string; name?: string; value: number; label?: string }) {
  const meta = DIMENSION_META[dim.key as ProfileAllDimensionKey]
  const fb = FALLBACK_DIM[dim.key]
  return {
    key: dim.key,
    name: meta?.name || fb?.name || dim.name || dim.key,
    value: dim.value,
    label: meta?.name || fb?.name || dim.label || dim.key,
  }
}

const initialDimensions = computed(() => {
  if (!snapshot.value?.initialSnapshot) return []
  return snapshot.value.initialSnapshot.dimensions
    .filter(dim => {
      const meta = DIMENSION_META[dim.key as ProfileAllDimensionKey]
      return meta?.showOnRadar
    })
    .map(enrichDim)
})

/** 初始画像总分（仅雷达维度，与保存时画像对齐） */
const initialTotalScore = computed(() => {
  if (initialDimensions.value.length === 0) return 0
  return initialDimensions.value.reduce((acc, d) => acc + d.value, 0)
})

/** 单个维度的成长值 */
function getDimGrowth(dimKey: string): number {
  const savedDim = savedDimensions.value.find(d => d.key === dimKey)
  const initDim = initialDimensions.value.find(d => d.key === dimKey)
  if (!savedDim || !initDim) return 0
  return Math.max(0, savedDim.value - initDim.value)
}

/** 已掌握的薄弱点数量 */
const masteredWeakPoints = computed(() => {
  if (!snapshot.value?.profileData) return 0
  return snapshot.value.profileData.masteredPoints?.length ?? 0
})

/** 学习事件（从 profileData.learningEvents 获取） */
const learningEvents = computed<LearningEvent[]>(() => {
  if (!snapshot.value?.profileData?.learningEvents) return []
  // 按时间倒序，最新的在上面
  return [...snapshot.value.profileData.learningEvents].reverse()
})

/** 事件类型标签 */
function eventLabel(type: string): string {
  const map: Record<string, string> = {
    stage_complete: '🛤️ 阶段完成',
    resource_complete: '📚 资源学习',
    assess_complete: '📝 测评完成',
  }
  return map[type] || type
}

/** 事件类型对应圆点样式 */
function eventDotClass(type: string): string {
  const map: Record<string, string> = {
    stage_complete: 'dot-blue',
    resource_complete: 'dot-cyan',
    assess_complete: 'dot-amber',
  }
  return map[type] || 'dot-gray'
}

/** 事件类型对应徽章样式 */
function eventBadgeClass(type: string): string {
  const map: Record<string, string> = {
    stage_complete: 'badge-blue',
    resource_complete: 'badge-cyan',
    assess_complete: 'badge-amber',
  }
  return map[type] || 'badge-gray'
}

function handleDelete() {
  if (!snapshot.value) return
  galleryStore.deleteSnapshot(snapshot.value.id)
  message.success('画作已删除')
  router.push('/gallery')
}

function goBack() {
  router.push('/gallery')
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}分`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}时${mins}分` : `${hours}时`
}
</script>

<style lang="less" scoped>
.gallery-detail-view {
  min-height: 100%;
  padding: 24px;
}

/* ===== 返回按钮 ===== */
.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.4);
  color: #475569;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 24px;

  .back-arrow { font-size: 16px; }

  &:hover {
    background: rgba(255, 255, 255, 0.6);
    border-color: rgba(37, 99, 235, 0.25);
    color: #2563eb;
  }
}

/* ===== 详情头部 ===== */
.detail-header {
  margin-bottom: 20px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.detail-title {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.perfect-badge { font-size: 22px; }

.detail-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 4px;
}

.detail-date {
  font-size: 12px;
  color: #94a3b8;
}

.btn-delete {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.06);
  color: #ef4444;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover {
    background: rgba(239, 68, 68, 0.12);
    border-color: rgba(239, 68, 68, 0.3);
  }
}

/* ===== 用户画像摘要 ===== */
.profile-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  margin-bottom: 24px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.4);
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .summary-icon {
    font-size: 16px;
  }

  .summary-label {
    font-size: 12px;
    color: #94a3b8;
    font-weight: 500;
  }

  .summary-value {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
  }
}

.summary-divider {
  width: 1px;
  height: 24px;
  background: rgba(37, 99, 235, 0.1);
}

/* ===== 雷达图对比 ===== */
.radar-compare {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: start;
  margin-bottom: 32px;
}

.radar-panel {
  padding: 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.4);

  &--perfect {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.04), rgba(255, 255, 255, 0.2));
    border-color: rgba(245, 158, 11, 0.18);
  }

  .panel-label {
    font-size: 14px;
    font-weight: 600;
    color: #475569;
    margin: 0 0 16px;
    text-align: center;
  }
}

.radar-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 8px;
}

.radar-empty {
  width: 280px;
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 13px;
}

.radar-score-label {
  text-align: center;
  margin-bottom: 16px;

  .score-value {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
  }

  .score-unit {
    display: block;
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
  }
}

.radar-panel--perfect .radar-score-label .score-value {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ===== 维度条形 ===== */
.radar-dims {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dim-row {
  display: grid;
  grid-template-columns: 20px 70px 1fr 36px;
  align-items: center;
  gap: 6px;

  .dim-icon { font-size: 13px; text-align: center; }
  .dim-name { font-size: 12px; color: #475569; white-space: nowrap; }

  .dim-bar-track {
    height: 6px;
    border-radius: 3px;
    background: rgba(226, 232, 240, 0.5);
    overflow: hidden;
  }

  .dim-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
  }

  .dim-value {
    font-size: 12px;
    font-weight: 600;
    color: #1e293b;
    text-align: right;
  }

  &--improved .dim-value {
    color: #10b981;
  }
}

.dim-growth {
  font-size: 11px;
  font-weight: 600;
  color: #10b981;
}

/* ===== VS 分隔 ===== */
.vs-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 80px;

  .vs-line {
    width: 1px;
    height: 40px;
    background: rgba(37, 99, 235, 0.15);
  }

  .vs-text {
    font-size: 14px;
    font-weight: 700;
    color: #94a3b8;
    padding: 8px;
  }
}

.vs-growth {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  margin-top: 8px;

  .vs-growth-icon { font-size: 20px; }

  .vs-growth-value {
    font-size: 16px;
    font-weight: 700;
    color: #10b981;
  }
}

/* ===== 成长数字 ===== */
.growth-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.growth-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 20px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.4);

  .growth-stat-icon { font-size: 24px; margin-bottom: 4px; }

  .growth-stat-value {
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .growth-stat-label { font-size: 12px; color: #94a3b8; }
}

/* ===== 学习经历 ===== */
.learning-journey {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.journey-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.journey-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.journey-count {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
}

.journey-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 16px;
  position: relative;
  padding-bottom: 20px;

  &:last-child {
    padding-bottom: 0;
  }
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
  position: relative;
  z-index: 1;

  &.dot-blue { background: #2563eb; box-shadow: 0 0 8px rgba(37, 99, 235, 0.4); }
  &.dot-cyan { background: #06b6d4; box-shadow: 0 0 8px rgba(6, 182, 212, 0.4); }
  &.dot-amber { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.4); }
  &.dot-gray { background: #94a3b8; }
}

.timeline-line {
  position: absolute;
  left: 5.5px;
  top: 18px;
  bottom: 0;
  width: 1px;
  background: rgba(37, 99, 235, 0.12);
}

.timeline-content {
  flex: 1;
  min-width: 0;
}

.timeline-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 6px;
  margin-bottom: 4px;

  &.badge-blue { background: rgba(37, 99, 235, 0.1); color: #2563eb; }
  &.badge-cyan { background: rgba(6, 182, 212, 0.1); color: #06b6d4; }
  &.badge-amber { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
  &.badge-gray { background: rgba(148, 163, 184, 0.1); color: #64748b; }
}

.timeline-desc {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 4px;
  line-height: 1.5;
}

.timeline-kps {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 6px;
}

.kp-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  font-weight: 500;
}

.kp-more {
  font-size: 11px;
  color: #94a3b8;
  padding: 1px 4px;
}

.timeline-time {
  font-size: 11px;
  color: #94a3b8;
}

.journey-empty {
  text-align: center;
  padding: 40px 20px;

  .empty-icon {
    font-size: 36px;
    margin-bottom: 8px;
    opacity: 0.5;
  }

  .empty-text {
    font-size: 14px;
    font-weight: 600;
    color: #475569;
    margin: 0 0 4px;
  }

  .empty-hint {
    font-size: 12px;
    color: #94a3b8;
    margin: 0;
  }
}

/* ===== 未找到 ===== */
.not-found {
  text-align: center;
  padding: 80px 20px;

  .not-found-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
  .not-found-text { font-size: 16px; font-weight: 600; color: #475569; margin: 0 0 16px; }
}

.btn-back-inline {
  padding: 8px 20px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: rgba(255, 255, 255, 0.4);
  color: #2563eb;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover { background: rgba(255, 255, 255, 0.6); }
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .radar-compare {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .vs-divider {
    flex-direction: row;
    padding-top: 0;
    padding: 8px 0;

    .vs-line { width: 40px; height: 1px; }
  }

  .growth-stats { grid-template-columns: repeat(2, 1fr); }

  .profile-summary {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .summary-divider {
    display: none;
  }
}

@media (max-width: 576px) {
  .gallery-detail-view { padding: 16px; }

  .detail-title-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .growth-stats {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .detail-title { font-size: 18px; }

  .radar-chart-wrapper {
    overflow-x: auto;
  }
}
</style>
