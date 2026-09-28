<template>
  <div class="learning-stats-view">
    <!-- 核心指标卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon time">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ learningStats.totalStudyTime }}<span class="unit">小时</span></div>
          <div class="stat-label">总学习时长</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon rate">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ learningStats.completionRate }}<span class="unit">%</span></div>
          <div class="stat-label">学习完成率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon users">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ learningStats.activeUsersToday }}</div>
          <div class="stat-label">今日活跃用户</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon week">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ learningStats.activeUsersWeek }}</div>
          <div class="stat-label">本周活跃用户</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <!-- 每日学习趋势 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>每日学习趋势</h3>
          <span class="chart-subtitle">最近7天</span>
        </div>
        <div class="chart-body">
          <div class="trend-chart">
            <div class="trend-bars">
              <div v-for="(day, index) in learningStats.dailyTrend" :key="index" class="trend-bar-item">
                <div class="trend-bar" :style="{ height: getBarHeight(day.time) + '%' }">
                  <span class="bar-value">{{ day.time }}分</span>
                </div>
                <span class="bar-label">{{ formatDate(day.date) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 资源类型分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>资源类型访问量</h3>
        </div>
        <div class="chart-body">
          <div class="resource-type-list">
            <div v-for="(count, type) in learningStats.resourceViews" :key="type" class="type-item">
              <div class="type-icon" :class="type">
                <SvgIcon :name="getResourceIcon(type)" :size="20" />
              </div>
              <div class="type-info">
                <div class="type-name">{{ getResourceTypeName(type) }}</div>
                <div class="type-count">{{ count }} 次访问</div>
              </div>
              <div class="type-bar-wrap">
                <div class="type-bar" :style="{ width: getTypePercent(count) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 画像分析 -->
    <div class="profile-section">
      <div class="section-header">
        <h3>画像数据分析</h3>
      </div>
      <div class="profile-charts">
        <!-- 专业分布 -->
        <div class="profile-chart-card">
          <div class="profile-chart-title">专业方向分布</div>
          <div class="major-list">
            <div v-for="item in profileStats.majorDistribution" :key="item.name" class="major-item">
              <span class="major-name">{{ item.name }}</span>
              <span class="major-count">{{ item.count }}人</span>
              <div class="major-bar" :style="{ width: getMajorPercent(item.count) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- 薄弱知识点TOP -->
        <div class="profile-chart-card">
          <div class="profile-chart-title">薄弱知识点 TOP10</div>
          <div class="weakness-list">
            <div v-for="(item, index) in profileStats.weaknessTop" :key="item.name" class="weakness-item">
              <span class="weakness-rank">{{ index + 1 }}</span>
              <span class="weakness-name">{{ item.name }}</span>
              <span class="weakness-count">{{ item.count }}人</span>
            </div>
          </div>
        </div>

        <!-- 基础水平分布 -->
        <div class="profile-chart-card">
          <div class="profile-chart-title">基础水平分布</div>
          <div class="level-list">
            <div v-for="item in profileStats.levelDistribution" :key="item.name" class="level-item">
              <span class="level-name">{{ item.name }}</span>
              <span class="level-count">{{ item.count }}人</span>
            </div>
          </div>
        </div>

        <!-- 认知风格分布 -->
        <div class="profile-chart-card">
          <div class="profile-chart-title">认知风格分布</div>
          <div class="style-list">
            <div v-for="item in profileStats.styleDistribution" :key="item.name" class="style-item">
              <span class="style-name">{{ item.name }}</span>
              <span class="style-count">{{ item.count }}人</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 热门资源排行 -->
    <div class="top-resources-section">
      <div class="section-header">
        <h3>热门资源排行</h3>
        <span class="section-subtitle">TOP 10</span>
      </div>
      <div class="resources-table">
        <div class="table-header">
          <span class="col-rank">排名</span>
          <span class="col-name">资源名称</span>
          <span class="col-views">访问次数</span>
        </div>
        <div class="table-body">
          <div v-for="(item, index) in learningStats.topResources" :key="item.name" class="table-row">
            <span class="col-rank">
              <span class="rank-badge" :class="{ top: index < 3 }">{{ index + 1 }}</span>
            </span>
            <span class="col-name">{{ item.name }}</span>
            <span class="col-views">{{ item.views }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getLearningStats, getProfileStats } from '../api/adminApi'
import SvgIcon from '../../../shared/components/SvgIcon.vue'

const learningStats = ref({
  totalStudyTime: 0,
  avgStudyTime: 0,
  completionRate: 0,
  activeUsersToday: 0,
  activeUsersWeek: 0,
  resourceViews: {} as Record<string, number>,
  dailyTrend: [] as { date: string; records: number; time: number }[],
  topResources: [] as { name: string; views: number }[]
})

const profileStats = ref({
  majorDistribution: [] as { name: string; count: number }[],
  weaknessTop: [] as { name: string; count: number }[],
  levelDistribution: [] as { name: string; count: number }[],
  styleDistribution: [] as { name: string; count: number }[]
})

const maxTime = ref(100)

function getBarHeight(time: number) {
  return Math.max(10, (time / maxTime.value) * 100)
}

function formatDate(date: string) {
  const d = new Date(date)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function getResourceIcon(type: string) {
  const icons: Record<string, string> = {
    document: 'file-text',
    mindmap: 'git-branch',
    video: 'video',
    code: 'code',
    exercise: 'clipboard-list'
  }
  return icons[type] || 'file'
}

function getResourceTypeName(type: string) {
  const names: Record<string, string> = {
    document: '文档',
    mindmap: '思维导图',
    video: '视频',
    code: '代码',
    exercise: '练习题'
  }
  return names[type] || type
}

function getTypePercent(count: number) {
  const total = Object.values(learningStats.value.resourceViews).reduce((a, b) => a + b, 0)
  return total > 0 ? (count / total) * 100 : 0
}

function getMajorPercent(count: number) {
  const total = profileStats.value.majorDistribution.reduce((a, b) => a + b.count, 0)
  return total > 0 ? (count / total) * 100 : 0
}

onMounted(async () => {
  // 加载学习数据统计
  try {
    const learningData = await getLearningStats()
    if (learningData) {
      learningStats.value = learningData
      // 计算最大时间用于柱状图
      const times = (learningData.dailyTrend || []).map((d: any) => d.time)
      maxTime.value = Math.max(...times, 10)
    }
  } catch (e) {
    console.error('加载学习统计失败', e)
  }

  // 加载画像数据统计
  try {
    const profileData = await getProfileStats()
    if (profileData) {
      profileStats.value = profileData
    }
  } catch (e) {
    console.error('加载画像统计失败', e)
  }
})
</script>

<style lang="less" scoped>
.learning-stats-view {
  padding: 0;
}

/* 核心指标卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.15);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;

  &.time { background: linear-gradient(135deg, #2563eb, #3b82f6); }
  &.rate { background: linear-gradient(135deg, #10b981, #34d399); }
  &.users { background: linear-gradient(135deg, #f59e0b, #fbbf24); }
  &.week { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;

  .unit {
    font-size: 14px;
    color: #64748b;
    margin-left: 4px;
  }
}

.stat-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 图表区域 */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
  }

  .chart-subtitle {
    font-size: 12px;
    color: #94a3b8;
  }
}

.chart-body {
  min-height: 200px;
}

/* 每日学习趋势柱状图 */
.trend-chart {
  height: 200px;
}

.trend-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 160px;
  padding-top: 20px;
}

.trend-bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 60px;
}

.trend-bar {
  width: 40px;
  background: linear-gradient(180deg, #2563eb, #3b82f6);
  border-radius: 6px 6px 0 0;
  position: relative;
  min-height: 20px;
  transition: height 0.5s;

  .bar-value {
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 11px;
    color: #64748b;
    white-space: nowrap;
  }
}

.bar-label {
  font-size: 12px;
  color: #94a3b8;
}

/* 资源类型分布 */
.resource-type-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.type-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.type-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);

  &.mindmap { color: #10b981; background: rgba(16, 185, 129, 0.1); }
  &.video { color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
  &.code { color: #8b5cf6; background: rgba(139, 92, 246, 0.1); }
  &.exercise { color: #ef4444; background: rgba(239, 68, 68, 0.1); }
}

.type-info {
  flex: 1;
}

.type-name {
  font-size: 14px;
  color: #1e293b;
  font-weight: 500;
}

.type-count {
  font-size: 12px;
  color: #94a3b8;
}

.type-bar-wrap {
  width: 100px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
}

.type-bar {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border-radius: 4px;
  transition: width 0.5s;
}

/* 画像分析 */
.profile-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
  }

  .section-subtitle {
    font-size: 12px;
    color: #94a3b8;
  }
}

.profile-charts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.profile-chart-card {
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.profile-chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.major-list, .weakness-list, .level-list, .style-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.major-item {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.major-name {
  font-size: 13px;
  color: #475569;
  width: 80px;
}

.major-count {
  font-size: 12px;
  color: #94a3b8;
  width: 40px;
}

.major-bar {
  height: 6px;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border-radius: 3px;
  flex: 1;
}

.weakness-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weakness-rank {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.weakness-name {
  font-size: 13px;
  color: #475569;
  flex: 1;
}

.weakness-count {
  font-size: 12px;
  color: #94a3b8;
}

.level-item, .style-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.level-name, .style-name {
  font-size: 13px;
  color: #475569;
}

.level-count, .style-count {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}

/* 热门资源排行 */
.top-resources-section {
  background: transparent;
  backdrop-filter: blur(16px);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.resources-table {
  margin-top: 16px;
}

.table-header {
  display: flex;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.table-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.table-row {
  display: flex;
  padding: 12px 16px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;

  &:hover {
    background: #f8fafc;
    border-color: #2563eb;
  }
}

.col-rank { width: 60px; }
.col-name { flex: 1; color: #1e293b; font-weight: 500; }
.col-views { width: 100px; color: #64748b; }

.rank-badge {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;

  &.top {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #fff;
  }
}
</style>