<template>
  <div class="home-view">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <div class="banner-text">
          <div class="banner-greeting">{{ greeting }}，{{ username }} 👋</div>
          <div class="banner-title">欢迎回到 AI 学习系统</div>
          <div class="banner-desc">今天也要继续加油！系统已为你准备好个性化的学习内容</div>
          <div class="banner-actions">
            <button class="btn-primary" @click="router.push('/path')">继续学习 →</button>
            <button class="btn-secondary" @click="router.push('/profile')">查看画像</button>
            <button class="btn-report" @click="showReport = true">📄 导出报告</button>
          </div>
        </div>
        <div class="banner-illustration">
          <svg width="200" height="200" viewBox="0 0 200 200">
            <defs>
              <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:1" />
              </linearGradient>
            </defs>
            <circle cx="100" cy="100" r="80" fill="url(#grad)" opacity="0.15"/>
            <circle cx="100" cy="100" r="60" fill="url(#grad)" opacity="0.2"/>
            <circle cx="100" cy="100" r="40" fill="url(#grad)" opacity="0.9"/>
            <text x="100" y="108" text-anchor="middle" fill="#fff" font-size="28" font-weight="700">AI</text>
          </svg>
        </div>
      </div>
    </div>

    <!-- 核心区域：能力分布 + 学习概览 -->
    <div class="hero-section">
      <div class="hero-left">
        <!-- 能力分布雷达图（最显眼位置） -->
        <div class="card radar-hero-card" :class="{ 'just-updated': profileStore.profileJustUpdated }">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">🎯 能力分布</span>
              <span class="card-subtitle">你的8维学习画像实时概览</span>
            </div>
            <div class="header-right-group">
              <span v-if="profileStore.profileJustUpdated" class="updated-badge">✨ 画像已更新</span>
              <span class="live-badge"><span class="live-dot"></span>随学随新</span>
              <router-link to="/profile" class="card-link">详细画像 →</router-link>
            </div>
          </div>
          <div class="radar-hero-body">
            <RadarChart :data="profileStore.profileData" />
          </div>
        </div>
      </div>
      <div class="hero-right">
        <!-- 画像完成度环 -->
        <div class="card completion-hero-card">
          <div class="completion-body">
            <div class="ring-wrapper">
              <div class="ring-bg"></div>
              <svg width="140" height="140" viewBox="0 0 140 140">
                <circle cx="70" cy="70" r="58" fill="none" stroke="rgba(37, 99, 235, 0.1)" stroke-width="10"/>
                <circle
                  cx="70" cy="70" r="58"
                  fill="none"
                  stroke="url(#homeCompletionGrad)"
                  stroke-width="10"
                  stroke-linecap="round"
                  :stroke-dasharray="`${(completionRate / 100) * 364} 364`"
                  class="ring-progress"
                />
                <defs>
                  <linearGradient id="homeCompletionGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#2563eb"/>
                    <stop offset="100%" stop-color="#06b6d4"/>
                  </linearGradient>
                </defs>
              </svg>
              <div class="ring-center-text">
                <span class="ring-num">{{ completionRate }}</span>
                <span class="ring-percent">%</span>
              </div>
            </div>
            <div class="completion-label">画像完成度</div>
          </div>
        </div>

        <!-- 快速维度分数 -->
        <div class="card dim-quick-card">
          <div class="dim-quick-list">
            <div v-for="dim in radarDimensions.slice(0, 4)" :key="dim.key" class="dim-quick-item">
              <div class="dim-quick-icon" :style="{ background: getDimColor(dim.key) }">{{ getDimIcon(dim.key) }}</div>
              <div class="dim-quick-info">
                <span class="dim-quick-name">{{ dim.name }}</span>
                <div class="dim-quick-bar">
                  <div class="dim-quick-fill" :style="{ width: dim.value + '%', background: getDimColor(dim.key) }"></div>
                </div>
              </div>
              <span class="dim-quick-value">{{ dim.value }}</span>
            </div>
          </div>
          <router-link to="/profile" class="dim-quick-more">查看全部8维 →</router-link>
        </div>
      </div>
    </div>

    <!-- 数据统计卡片（真实数据） -->
    <div class="stats-grid">
      <div class="stat-card purple">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ radarDimensions.filter(d => d.value > 0).length }}</div>
          <div class="stat-label">画像维度</div>
        </div>
        <div class="stat-trend" :class="{ positive: recentLogCount > 0 }">{{ recentLogCount > 0 ? `+${recentLogCount} 近期` : '已完善' }}</div>
      </div>

      <div class="stat-card blue">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"></polyline>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ pathStore.totalProgress }}%</div>
          <div class="stat-label">学习进度</div>
        </div>
        <div class="stat-trend" :class="{ positive: pathStore.totalProgress > 0 }">{{ pathStore.totalProgress > 0 ? `${pathStore.totalProgress}% 进行中` : '未开始' }}</div>
      </div>

      <div class="stat-card green">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ resourceStore.resources.length }}</div>
          <div class="stat-label">学习资源</div>
        </div>
        <div class="stat-trend" :class="{ positive: resourceStore.resources.length > 0 }">{{ newResourceCount > 0 ? `+${newResourceCount} AI生成` : '待生成' }}</div>
      </div>

      <div class="stat-card orange">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ profileStore.profileData.streakDays || 0 }}</div>
          <div class="stat-label">连续学习天数</div>
        </div>
        <div class="stat-trend" :class="{ positive: (profileStore.profileData.streakDays || 0) > 0 }">{{ (profileStore.profileData.streakDays || 0) > 0 ? '坚持中' : '今天开始' }}</div>
      </div>
    </div>

    <!-- 学习数据仪表盘 -->
    <LearningDashboard />

    <!-- 主体内容 -->
    <div class="content-grid">
      <!-- 左列：学习路径 + 最近画像更新 -->
      <div class="left-col">
        <!-- 学习路径 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">学习路径</span>
              <span class="card-subtitle">继续你的学习之旅</span>
            </div>
            <router-link to="/path" class="card-link">查看全部 →</router-link>
          </div>
          <div class="card-body">
            <div class="path-list">
              <div v-for="(stage, idx) in pathStore.stages.slice(0, 4)" :key="stage.id" class="path-item">
                <div class="path-status" :class="stage.status">
                  <span v-if="stage.status === 'completed'">✓</span>
                  <span v-else-if="stage.status === 'active'">▶</span>
                  <span v-else>{{ idx + 1 }}</span>
                </div>
                <div class="path-info">
                  <div class="path-name">{{ stage.title }}</div>
                  <div class="path-bar">
                    <div class="path-progress" :style="{ width: stage.progress + '%' }"></div>
                  </div>
                </div>
                <div class="path-percent">{{ stage.progress }}%</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 最近画像更新 -->
        <div class="card" v-if="recentLogs.length > 0">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">画像更新</span>
              <span class="card-subtitle">学习行为实时驱动画像变化</span>
            </div>
            <router-link to="/profile" class="card-link">全部记录 →</router-link>
          </div>
          <div class="card-body">
            <div class="log-list">
              <div v-for="log in recentLogs" :key="log.id" class="log-item">
                <div class="log-badge" :class="log.source">{{ sourceLabel(log.source) }}</div>
                <div class="log-desc">{{ log.description }}</div>
                <div v-if="log.affectedCount > 0" class="log-changes">
                  <span v-for="(change, dimKey) in log.changes" :key="dimKey" class="change-chip" :class="change.after > change.before ? 'up' : 'down'">
                    {{ getDimName(dimKey as any) }} {{ change.after > change.before ? '↑' : '↓' }}{{ Math.abs(change.after - change.before) }}
                  </span>
                </div>
                <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右列：智能体状态 + 资源推荐 -->
      <div class="right-col">
        <!-- 智能体状态 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">智能体状态</span>
              <span class="card-subtitle">AI 正在为你工作</span>
            </div>
            <router-link to="/agent" class="card-link">控制面板 →</router-link>
          </div>
          <div class="card-body">
            <div class="agent-list">
              <div v-for="agent in agentStore.agents.slice(0, 5)" :key="agent.name" class="agent-item">
                <div class="agent-icon" :class="agent.status"></div>
                <div class="agent-info">
                  <div class="agent-name">{{ agent.name }}</div>
                  <div class="agent-desc">{{ agent.role }}</div>
                </div>
                <div class="agent-badge" :class="agent.status">
                  {{ agent.status === 'completed' ? '就绪' : agent.status === 'running' ? '运行中' : '空闲' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 推荐资源 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">推荐资源</span>
              <span class="card-subtitle">根据画像为你精选 · 点击查看完整内容</span>
            </div>
            <router-link to="/community" class="card-link">前往社区 →</router-link>
          </div>
          <div class="card-body">
            <div class="resource-list">
              <div v-for="res in resourceStore.resources.slice(0, 4)" :key="res.id" class="resource-item" @click="goToCommunity(res)">
                <div class="resource-type-badge" :class="res.type">{{ typeLabels[res.type] || res.type }}</div>
                <div class="resource-content">
                  <div class="resource-title">{{ res.title }}</div>
                  <div class="resource-desc">{{ getResourcePreview(res) }}</div>
                </div>
                <div class="resource-arrow">→</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 错题本 -->
        <div class="card" v-if="assessStore.wrongAnswers.length > 0">
          <div class="card-header">
            <div class="card-title-group">
              <span class="card-title">❌ 错题本</span>
              <span class="card-subtitle">最近做错的题目，重点复习</span>
            </div>
            <router-link to="/assess" class="card-link">重新测评 →</router-link>
          </div>
          <div class="card-body">
            <div class="wrong-list">
              <div v-for="w in assessStore.wrongAnswers.slice(-5).reverse()" :key="w.questionId + w.timestamp" class="wrong-item">
                <div class="wrong-icon">✗</div>
                <div class="wrong-content">
                  <div class="wrong-question">{{ w.question }}</div>
                  <div class="wrong-meta">
                    <span class="wrong-kp">{{ w.knowledgePoints.join('、') }}</span>
                    <span class="wrong-time">{{ formatTime(w.timestamp) }}</span>
                  </div>
                  <div class="wrong-detail">你的答案：{{ w.userAnswer }} | 正确答案：{{ w.correctAnswer }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 导出报告 -->
    <ReportExport :visible="showReport" @close="showReport = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../auth/stores/authStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { useAgentStore } from '../../agent/stores/agentStore'
import { useResourceStore } from '../../resource/stores/resourceStore'
import { usePathStore } from '../../path/stores/pathStore'
import { useAssessStore } from '../../assess/stores/assessStore'
import { DIMENSION_META } from '../../../shared/types'
import type { ProfileAllDimensionKey, ProfileUpdateSource } from '../../../shared/types'
import RadarChart from '../../profile/components/RadarChart.vue'
import LearningDashboard from '../components/LearningDashboard.vue'
import ReportExport from '../../report/components/ReportExport.vue'

const router = useRouter()
const showReport = ref(false)
const authStore = useAuthStore()
const profileStore = useProfileStore()
const agentStore = useAgentStore()
const resourceStore = useResourceStore()
const assessStore = useAssessStore()
const pathStore = usePathStore()

// 真实统计数据
const recentLogCount = computed(() => {
  const logs = profileStore.profileData.updateLogs || []
  const week = 7 * 24 * 60 * 60 * 1000
  return logs.filter(l => Date.now() - new Date(l.timestamp).getTime() < week).length
})

const newResourceCount = computed(() => {
  const resources = resourceStore.resources || []
  const week = 7 * 24 * 60 * 60 * 1000
  return resources.filter(r => r.aiGenerated && Date.now() - new Date(r.createdAt).getTime() < week).length
})

const username = computed(() => authStore.user?.username || '同学')

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

/** 只取雷达图上显示的维度 */
const radarDimensions = computed(() =>
  (profileStore.profileData.dimensions || []).filter(d => d.showOnRadar !== false)
)

const completionRate = computed(() => profileStore.completionRate)
const recentLogs = computed(() => profileStore.getRecentLogs(3))

const typeLabels: Record<string, string> = {
  video: '视频',
  document: '文档',
  exercise: '练习',
  mindmap: '思维导图',
  code: '代码',
  'knowledge-graph': '图谱',
  extension: '拓展',
  quiz: '测验',
  profile: '画像'
}

function getResourcePreview(res: { content?: string; description?: string; type?: string }): string {
  if (res.content) {
    const text = res.content
      .replace(/```[\s\S]*?```/g, '[代码]')
      .replace(/[#*`_~\-]/g, '')
      .replace(/\n+/g, ' ')
      .trim()
    return text.length > 60 ? text.substring(0, 60) + '...' : text
  }
  return res.description || '点击查看完整内容'
}

function goToCommunity(res?: { id?: string }) {
  if (res?.id) {
    router.push({ path: '/community', query: { rid: res.id } })
  } else {
    router.push('/community')
  }
}

function getDimIcon(key: string): string {
  return DIMENSION_META[key as ProfileAllDimensionKey]?.icon || '•'
}

function getDimColor(key: string): string {
  const colors: Record<string, string> = {
    'base_level': '#06b6d4',
    'weak_points': '#f59e0b',
    'study_goal': '#10b981',
    'learning_engagement': '#ec4899',
    'study_rhythm': '#8b5cf6',
    'interest_preference': '#f97316',
    'knowledge_mastery': '#6366f1',
    'exercise_completion': '#22c55e',
    'major': '#2563eb',
    'grade': '#6366f1',
    'cognitive_style': '#ec4899',
  }
  return colors[key] || '#2563eb'
}

function getDimName(key: ProfileAllDimensionKey): string {
  return DIMENSION_META[key]?.name || key
}

function sourceLabel(source: ProfileUpdateSource): string {
  const map: Record<ProfileUpdateSource, string> = {
    path_complete: '🛤️ 阶段',
    resource_complete: '📚 资源',
    assess_complete: '📝 测评',
    dialogue: '💬 对话',
    manual: '✋ 手动',
  }
  return map[source] || source
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style lang="less" scoped>
.home-view {
  padding: 24px;
  min-height: 100%;
  background: transparent;
}

// ============================================
// 欢迎横幅
// ============================================
.welcome-banner {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border-radius: 14px;
  padding: 32px;
  margin-bottom: 24px;
  color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.banner-text {
  flex: 1;
  max-width: 600px;
}

.banner-greeting {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
  font-weight: 500;
}

.banner-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  line-height: 1.3;
}

.banner-desc {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 24px;
  line-height: 1.6;
}

.banner-actions {
  display: flex;
  gap: 12px;
}

.btn-primary {
  padding: 10px 20px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border: none;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4);
  }
}

.btn-secondary {
  padding: 10px 20px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.25);
  }
}

.btn-report {
  padding: 10px 20px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border: none;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }
}

.banner-illustration {
  flex-shrink: 0;
  opacity: 0.9;
}

// ============================================
// 核心区域：雷达图 + 学习概览
// ============================================
.hero-section {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.hero-left {
  display: flex;
  flex-direction: column;
}

.hero-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.radar-hero-card {
  flex: 1;
  transition: box-shadow 0.5s ease, border-color 0.5s ease;

  &.just-updated {
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.4), 0 4px 20px rgba(37, 99, 235, 0.15);
  }

  .radar-hero-body {
    padding: 16px 20px;
    height: 360px;
  }
}

.updated-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  padding: 5px 12px;
  border-radius: 8px;
  animation: badge-pulse 1s ease-in-out 2;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);
}

@keyframes badge-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.header-right-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #06b6d4;
  background: rgba(6, 182, 212, 0.1);
  padding: 5px 12px;
  border-radius: 8px;
}

.live-badge .live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #06b6d4;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; box-shadow: 0 0 4px rgba(6, 182, 212, 0.6); }
  50% { opacity: 0.4; box-shadow: none; }
}

// 完成度卡片
.completion-hero-card {
  .completion-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
}

.ring-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  margin-bottom: 12px;
}

.ring-bg {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
}

.ring-progress {
  transform: rotate(-90deg);
  transform-origin: center;
  transition: stroke-dasharray 0.8s ease;
}

.ring-center-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.ring-num {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.ring-percent {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
}

.completion-label {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

// 维度快速卡片
.dim-quick-card {
  flex: 1;
}

.dim-quick-list {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dim-quick-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dim-quick-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
}

.dim-quick-info {
  flex: 1;
  min-width: 0;
}

.dim-quick-name {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
  display: block;
  margin-bottom: 4px;
}

.dim-quick-bar {
  height: 5px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.dim-quick-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.dim-quick-value {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  min-width: 28px;
  text-align: right;
}

.dim-quick-more {
  display: block;
  padding: 12px 20px;
  text-align: center;
  font-size: 12px;
  color: #2563eb;
  font-weight: 500;
  text-decoration: none;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  transition: background 0.15s;

  &:hover {
    background: rgba(37, 99, 235, 0.05);
  }
}

// ============================================
// 统计卡片网格
// ============================================
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);
  border: 1px solid rgba(37, 99, 235, 0.1);
  position: relative;
  overflow: hidden;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
  }

  &.purple {
    border-top: 3px solid #2563eb;
    .stat-icon { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
    .stat-value { color: #1e293b; }
  }

  &.blue {
    border-top: 3px solid #06b6d4;
    .stat-icon { background: rgba(6, 182, 212, 0.12); color: #06b6d4; }
    .stat-value { color: #1e293b; }
  }

  &.green {
    border-top: 3px solid #10b981;
    .stat-icon { background: rgba(16, 185, 129, 0.12); color: #10b981; }
    .stat-value { color: #1e293b; }
  }

  &.orange {
    border-top: 3px solid #f59e0b;
    .stat-icon { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
    .stat-value { color: #1e293b; }
  }
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.stat-trend {
  position: absolute;
  top: 20px;
  right: 20px;
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;

  &.positive {
    color: #10b981;
  }
}

// ============================================
// 主体内容网格
// ============================================
.content-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 24px;
}

.left-col,
.right-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// ============================================
// 通用卡片样式
// ============================================
.card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);
  border: 1px solid rgba(37, 99, 235, 0.1);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
}

.card-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.card-subtitle {
  font-size: 13px;
  color: #94a3b8;
}

.card-link {
  font-size: 13px;
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.15s ease;

  &:hover {
    opacity: 0.7;
  }
}

.card-body {
  padding: 20px 24px;
}

// ============================================
// 学习路径
// ============================================
.path-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.path-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.05);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
  }
}

.path-status {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;

  &.completed {
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
  }

  &.active {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.4);
  }

  &.pending {
    background: rgba(37, 99, 235, 0.1);
    color: #94a3b8;
  }
}

.path-info {
  flex: 1;
}

.path-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 8px;
}

.path-bar {
  height: 6px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.path-progress {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.path-percent {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  flex-shrink: 0;
  min-width: 40px;
  text-align: right;
}

// ============================================
// 画像更新记录
// ============================================
.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.05);
  flex-wrap: wrap;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
  }
}

.log-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;

  &.path_complete { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
  &.resource_complete { background: rgba(6, 182, 212, 0.12); color: #06b6d4; }
  &.assess_complete { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
  &.dialogue { background: rgba(99, 102, 241, 0.12); color: #6366f1; }
  &.manual { background: rgba(71, 85, 105, 0.12); color: #475569; }
}

.log-desc {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-changes {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.change-chip {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;

  &.up { background: rgba(16, 185, 129, 0.12); color: #10b981; }
  &.down { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
}

.log-time {
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}

// ============================================
// 智能体
// ============================================
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.05);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
  }
}

.agent-icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;

  &.completed { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
  &.active { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.4); animation: pulse 2s ease-in-out infinite; }
  &.pending { background: #94a3b8; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 2px;
}

.agent-desc {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;

  &.completed {
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
  }

  &.active {
    background: rgba(245, 158, 11, 0.12);
    color: #f59e0b;
  }

  &.pending {
    background: rgba(37, 99, 235, 0.1);
    color: #94a3b8;
  }
}

// ============================================
// 推荐资源
// ============================================
.resource-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.05);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
    transform: translateX(4px);
  }
}

.resource-type-badge {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;

  &.video { background: rgba(239, 68, 68, 0.12); color: #ef4444; }
  &.document { background: rgba(6, 182, 212, 0.12); color: #06b6d4; }
  &.exercise { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
  &.mindmap { background: rgba(16, 185, 129, 0.12); color: #10b981; }
  &.code { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
}

.resource-content {
  flex: 1;
  min-width: 0;
}

.resource-title {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 2px;
}

.resource-desc {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-arrow {
  color: #94a3b8;
  font-size: 14px;
  flex-shrink: 0;
  transition: transform 0.15s ease;
}

.resource-item:hover .resource-arrow {
  color: #2563eb;
  transform: translateX(4px);
}

/* ===== 错题本 ===== */
.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wrong-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.04);
  border-left: 3px solid #ef4444;
}

.wrong-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  font-weight: 700;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.wrong-content {
  flex: 1;
  min-width: 0;
}

.wrong-question {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wrong-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.wrong-kp {
  font-size: 11px;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

.wrong-time {
  font-size: 11px;
  color: #94a3b8;
}

.wrong-detail {
  font-size: 12px;
  color: #475569;
  margin-top: 4px;
}

// ============================================
// 响应式
// ============================================
@media (max-width: 1200px) {
  .hero-section {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .banner-content {
    flex-direction: column;
    text-align: center;
  }

  .banner-actions {
    justify-content: center;
  }
}
</style>
