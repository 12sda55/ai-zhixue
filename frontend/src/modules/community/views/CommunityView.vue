<template>
  <div class="community-view">
    <!-- 社区头部 -->
    <div class="community-header">
      <div class="header-left">
        <div class="header-icon">🌐</div>
        <div>
          <div class="header-title">学习资源共享社区</div>
          <div class="header-desc">跨用户优质资源 · 画像精准匹配 · 质量多维评估</div>
        </div>
      </div>
      <div class="header-stats" v-if="!loading">
        <div class="stat-pill">
          <span class="stat-num">{{ stats.totalUsers }}</span>
          <span class="stat-label">活跃用户</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num">{{ pool.length }}</span>
          <span class="stat-label">优质资源</span>
        </div>
        <div class="stat-pill highlight">
          <span class="stat-num">{{ sharedCount }}</span>
          <span class="stat-label">来自他人</span>
        </div>
        <div class="stat-pill">
          <span class="stat-num">{{ ownCount }}</span>
          <span class="stat-label">我的贡献</span>
        </div>
      </div>
    </div>

    <!-- 质量门槛说明 -->
    <div v-if="!loading && pool.length > 0" class="quality-gate-notice">
      <span class="gate-icon">✓</span>
      <span class="gate-text">质量筛选已启用：空内容、未完成视频、无标题资源自动过滤，仅收录质量分 ≥ 25 的资源</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <div class="loading-text">正在加载跨用户资源池...</div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="pool.length === 0" class="empty-state">
      <div class="empty-icon">🗂️</div>
      <div class="empty-title">社区暂无共享资源</div>
      <div class="empty-desc">完成画像采集并启动智能体生成资源后，社区将汇聚所有用户的优质学习资源</div>
      <button class="empty-btn" @click="router.push('/agent')">前往智能体面板 →</button>
    </div>

    <template v-else>
      <!-- 推荐案例验证区：展示画像维度 + 匹配过程 -->
      <section v-if="profileDimensions.length > 0" class="community-section case-section">
        <div class="section-header">
          <h2 class="section-title"><span class="section-icon">🔍</span> 推荐案例验证</h2>
          <span class="section-subtitle">画像 {{ profileDimensions.length }} 维度 → 精准匹配过程可视化</span>
        </div>
        <div class="case-validation">
          <div class="profile-dimensions">
            <div class="case-label">当前画像维度</div>
            <div class="dimension-chips">
              <span v-for="dim in profileDimensions" :key="dim.key" class="dim-chip">
                <span class="dim-label">{{ dim.label }}</span>
                <span class="dim-value">{{ dim.value }}</span>
              </span>
            </div>
          </div>
          <div class="case-arrow">→</div>
          <div class="match-result">
            <div class="case-label">匹配结果</div>
            <div class="match-summary">
              <span class="match-stat">画像精选 <strong>{{ recommendedList.length }}</strong></span>
              <span class="match-stat">薄弱点覆盖 <strong>{{ weakPointList.length }}</strong></span>
              <span class="match-stat">优质资源 <strong>{{ qualityResourceList.length }}</strong></span>
            </div>
          </div>
        </div>
      </section>

      <!-- 画像未完善提示 -->
      <div v-if="profileDimensions.length === 0" class="profile-hint">
        <span class="hint-icon">💡</span>
        <span class="hint-text">完善学习画像可获得更精准的个性化推荐</span>
        <button class="hint-btn" @click="router.push('/profile')">完善画像 →</button>
      </div>

      <!-- 画像精选推荐区：基于画像匹配度 -->
      <section v-if="recommendedList.length > 0" class="community-section">
        <div class="section-header">
          <h2 class="section-title"><span class="section-icon">🎯</span> 画像精选推荐</h2>
          <span class="section-subtitle">根据你的画像维度从跨用户资源池智能匹配</span>
        </div>
        <div class="recommend-grid">
          <div
            v-for="item in recommendedList"
            :key="item.resource.id"
            class="recommend-card"
            @click="openDetail(item.resource)"
          >
            <div class="card-rank-badge" :class="`rank-${item.rank}`">#{{ item.rank }}</div>
            <div class="card-top">
              <span class="card-type-badge" :style="{ background: typeColors[item.resource.type] }">
                {{ typeIcons[item.resource.type] }} {{ typeLabels[item.resource.type] }}
              </span>
              <span v-if="item.resource.subject" class="card-subject-tag">{{ item.resource.subject }}</span>
              <QualityBadge v-if="item.quality" :quality="item.quality" />
            </div>
            <div class="card-title">{{ item.resource.title }}</div>
            <div class="card-preview">{{ getContentPreview(item.resource.content) }}</div>
            <div class="card-author">
              <span class="author-tag" :class="{ own: item.isOwn }">
                {{ item.isOwn ? '👤 我的资源' : `👥 来自 ${item.author}` }}
              </span>
            </div>
            <div class="card-reasons">
              <span v-for="reason in item.reasons" :key="reason" class="reason-tag">{{ reason }}</span>
            </div>
            <div class="card-match-score">
              <div class="match-bar">
                <div class="match-fill" :style="{ width: item.matchPercent + '%' }"></div>
              </div>
              <span class="match-text">匹配度 {{ item.matchPercent }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 薄弱点突破区 -->
      <section v-if="weakPointList.length > 0" class="community-section">
        <div class="section-header">
          <h2 class="section-title"><span class="section-icon">⚡</span> 薄弱点突破</h2>
          <span class="section-subtitle">针对你的薄弱知识点，从跨用户资源池专项匹配</span>
        </div>
        <div class="weak-grid">
          <div
            v-for="item in weakPointList"
            :key="item.resource.id"
            class="weak-card"
            @click="openDetail(item.resource)"
          >
            <div class="weak-point-tag">⚡ {{ item.weakPoint }}</div>
            <span class="card-type-badge small" :style="{ background: typeColors[item.resource.type] }">
              {{ typeIcons[item.resource.type] }} {{ typeLabels[item.resource.type] }}
            </span>
            <QualityBadge v-if="item.quality" :quality="item.quality" />
            <div class="card-title">{{ item.resource.title }}</div>
            <div class="card-preview">{{ getContentPreview(item.resource.content) }}</div>
            <div class="card-author">
              <span class="author-tag" :class="{ own: item.isOwn }">
                {{ item.isOwn ? '👤 我的资源' : `👥 来自 ${item.author}` }}
              </span>
            </div>
            <div class="card-bottom">
              <span class="card-click-hint">点击查看 →</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 优质资源区 -->
      <section v-if="qualityResourceList.length > 0" class="community-section">
        <div class="section-header">
          <h2 class="section-title"><span class="section-icon">💎</span> 优质资源</h2>
          <span class="section-subtitle">质量评分 ≥75 的高质量学习资源</span>
        </div>
        <div class="quality-grid">
          <div
            v-for="item in qualityResourceList"
            :key="item.resource.id"
            class="quality-card"
            @click="openDetail(item.resource)"
          >
            <div class="card-top">
              <span class="card-type-badge" :style="{ background: typeColors[item.resource.type] }">
                {{ typeIcons[item.resource.type] }} {{ typeLabels[item.resource.type] }}
              </span>
              <QualityBadge :quality="item.quality" />
            </div>
            <div class="card-title">{{ item.resource.title }}</div>
            <div class="card-preview">{{ getContentPreview(item.resource.content) }}</div>
            <div class="quality-dimensions">
              <span v-for="dim in item.quality.dimensions.slice(0, 3)" :key="dim" class="dim-badge">{{ dim }}</span>
            </div>
            <div class="card-author">
              <span class="author-tag" :class="{ own: item.isOwn }">
                {{ item.isOwn ? '👤 我的资源' : `👥 来自 ${item.author}` }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- 热门资源区 -->
      <section v-if="popularList.length > 0" class="community-section">
        <div class="section-header">
          <h2 class="section-title"><span class="section-icon">🔥</span> 热门资源</h2>
          <span class="section-subtitle">按收藏和评分排序的受欢迎资源</span>
        </div>
        <div class="popular-list">
          <div
            v-for="item in popularList"
            :key="item.resource.id"
            class="popular-item"
            @click="openDetail(item.resource)"
          >
            <div class="popular-rank">{{ item.rank }}</div>
            <span class="card-type-badge small" :style="{ background: typeColors[item.resource.type] }">
              {{ typeIcons[item.resource.type] }}
            </span>
            <div class="popular-info">
              <div class="card-title small">{{ item.resource.title }}</div>
              <div class="popular-meta">
                <span v-if="item.favCount > 0" class="meta-tag">★ {{ item.favCount }} 收藏</span>
                <span v-if="item.rating > 0" class="meta-tag">⭐ {{ item.rating }} 评分</span>
                <span v-if="item.resource.aiGenerated" class="meta-tag ai">AI 生成</span>
                <span class="meta-tag author-meta" :class="{ own: item.isOwn }">
                  {{ item.isOwn ? '我的' : item.author }}
                </span>
              </div>
            </div>
            <div class="popular-arrow">→</div>
          </div>
        </div>
      </section>

      <!-- 全部资源（折叠区） -->
      <section class="community-section">
        <div class="section-header collapsible" @click="showAllResources = !showAllResources">
          <h2 class="section-title"><span class="section-icon">📚</span> 全部资源</h2>
          <span class="section-subtitle">{{ pool.length }} 个资源 · 支持类型/科目/质量筛选</span>
          <span class="collapse-arrow" :class="{ expanded: showAllResources }">▼</span>
        </div>
        <div v-if="showAllResources" class="all-resources-content">
          <div class="filter-row">
            <div class="search-box">
              <span class="search-icon">🔍</span>
              <input v-model="searchKeyword" placeholder="搜索资源标题/内容..." class="search-input" />
            </div>
            <div class="type-filter-chips">
              <button class="filter-chip" :class="{ active: activeType === 'all' }" @click="activeType = 'all'">全部</button>
              <button
                v-for="t in typeStats"
                :key="t.key"
                class="filter-chip"
                :class="{ active: activeType === t.key }"
                @click="activeType = t.key"
              >{{ t.icon }} {{ t.label }} {{ t.count }}</button>
            </div>
            <div class="quality-filter-chips">
              <button
                v-for="ql in ['优质', '良好', '基础', '待完善']"
                :key="ql"
                class="filter-chip quality-chip"
                :class="[`ql-${ql}`, { active: activeQuality === ql }]"
                @click="toggleQuality(ql)"
              >{{ ql }}</button>
            </div>
          </div>
          <div class="resource-grid" v-if="filteredPool.length > 0">
            <div
              v-for="item in filteredPool"
              :key="item.resource.id"
              class="community-card"
              @click="openDetail(item.resource)"
            >
              <div class="card-top">
                <span class="card-type-badge" :style="{ background: typeColors[item.resource.type] }">
                  {{ typeIcons[item.resource.type] }} {{ typeLabels[item.resource.type] }}
                </span>
                <QualityBadge v-if="item.quality" :quality="item.quality" />
                <span v-if="item.resource.aiGenerated" class="ai-badge">AI</span>
              </div>
              <div class="card-title">{{ item.resource.title }}</div>
              <div class="card-preview">{{ getContentPreview(item.resource.content) }}</div>
              <div class="card-author">
                <span class="author-tag" :class="{ own: item.isOwn }">
                  {{ item.isOwn ? '👤 我的资源' : `👥 来自 ${item.author}` }}
                </span>
              </div>
              <div class="card-bottom">
                <span class="card-date">{{ formatDate(item.resource.createdAt) }}</span>
                <span class="card-click-hint">点击查看 →</span>
              </div>
            </div>
          </div>
          <div v-else class="no-result">
            <div>没有找到匹配的资源</div>
            <button class="clear-btn" @click="clearFilters">清除筛选</button>
          </div>
        </div>
      </section>
    </template>

    <!-- 资源详情弹窗 -->
    <Teleport to="body">
      <div v-if="selectedResource" class="detail-overlay" @click.self="closeDetail">
        <div class="detail-panel">
          <div class="detail-header-bar">
            <span class="detail-type-badge" :style="{ background: typeColors[selectedResource.type] }">
              {{ typeIcons[selectedResource.type] }} {{ typeLabels[selectedResource.type] }}
            </span>
            <span v-if="selectedResource.subject" class="detail-subject">{{ selectedResource.subject }}</span>
            <span v-if="selectedAuthor" class="detail-author" :class="{ own: selectedIsOwn }">
              {{ selectedIsOwn ? '👤 我的资源' : `👥 来自 ${selectedAuthor}` }}
            </span>
            <button class="detail-close" @click="closeDetail">✕</button>
          </div>
          <div class="detail-body-wrapper">
            <ResourceDetail :resource="selectedResource" @update:resource="onResourceUpdate" />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ResourceDetail from '../../resource/components/ResourceDetail.vue'
import QualityBadge from '../components/QualityBadge.vue'
import { useProfileStore } from '../../profile/stores/profileStore'
import { recommend } from '../../resource/services/recommender'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'
import request from '../../../shared/utils/request'
import type { ResourceItem } from '../../../shared/types'

interface QualityInfo {
  score: number
  level: string
  dimensions: string[]
}

interface PoolItem {
  resource: ResourceItem
  author: string
  authorId: number
  isOwn: boolean
  quality: QualityInfo
}

const router = useRouter()
const route = useRoute()
const profileStore = useProfileStore()

const loading = ref(true)
const pool = ref<PoolItem[]>([])
const stats = ref({ totalUsers: 0, totalResources: 0 })
const profileDimensions = ref<{ key: string; label: string; value: string }[]>([])
const searchKeyword = ref('')
const activeType = ref('all')
const activeQuality = ref<string | null>(null)
const showAllResources = ref(false)
const selectedResource = ref<ResourceItem | null>(null)
const selectedAuthor = ref('')
const selectedIsOwn = ref(false)

const typeLabels: Record<string, string> = {
  video: '视频', document: '文档', exercise: '练习', code: '代码',
  mindmap: '思维导图', 'knowledge-graph': '知识图谱', extension: '拓展', quiz: '测验',
}
const typeIcons: Record<string, string> = {
  video: '🎬', document: '📄', exercise: '✏️', code: '💻',
  mindmap: '🧠', 'knowledge-graph': '🕸️', extension: '📖', quiz: '📝',
}
const typeColors: Record<string, string> = {
  video: 'rgba(239, 68, 68, 0.8)', document: 'rgba(6, 182, 212, 0.8)',
  exercise: 'rgba(245, 158, 11, 0.8)', code: 'rgba(37, 99, 235, 0.8)',
  mindmap: 'rgba(16, 185, 129, 0.8)', 'knowledge-graph': 'rgba(139, 92, 246, 0.8)',
  extension: 'rgba(99, 102, 241, 0.8)', quiz: 'rgba(236, 72, 153, 0.8)',
}

// ===== 统计 =====
const ownCount = computed(() => pool.value.filter(r => r.isOwn).length)
const sharedCount = computed(() => pool.value.length - ownCount.value)

// ===== 精选推荐：基于画像匹配度（质量门槛 >= 50） =====
const recommendedList = computed(() => {
  const profile = profileStore.profileData
  // 只从质量分 >= 50 的资源中推荐
  const qualifiedPool = pool.value.filter(p => p.quality.score >= 50)
  const resourcePool = qualifiedPool.map(p => p.resource)
  if (resourcePool.length === 0) return []

  const ranked = recommend({
    profile,
    stageContext: { title: '' },
    pool: resourcePool,
  })

  const maxScore = ranked.length > 0 ? ranked[0].score : 1
  return ranked.slice(0, 6).map((r, i) => {
    const poolItem = qualifiedPool.find(p => p.resource.id === r.resource.id)
    return {
      resource: r.resource,
      reasons: r.reasons,
      score: r.score,
      rank: i + 1,
      matchPercent: Math.min(100, Math.round((r.score / maxScore) * 100)),
      author: poolItem?.author || '',
      isOwn: poolItem?.isOwn || false,
      quality: poolItem?.quality,
    }
  })
})

// ===== 薄弱点突破：匹配薄弱点（质量门槛 >= 25） =====
const weakPointList = computed(() => {
  const profile = profileStore.profileData
  const subject = profile.currentSubject || profile.major || ''
  const weakPoints = filterRelevantWeakPoints(profile.weak_points || [], subject)
  if (weakPoints.length === 0) return []

  // 只从质量分 >= 25 的资源中匹配
  const qualifiedPool = pool.value.filter(p => p.quality.score >= 25)
  const result: { resource: ResourceItem; weakPoint: string; author: string; isOwn: boolean; quality?: QualityInfo }[] = []

  for (const wp of weakPoints) {
    if (wp.length < 2) continue
    const wpLower = wp.toLowerCase()
    const matched = qualifiedPool.find(p => {
      const r = p.resource
      const title = (r.title || '').toLowerCase()
      const module = (r.module || '').toLowerCase()
      const content = (r.content || '').toLowerCase()
      return title.includes(wpLower) || module.includes(wpLower) || content.includes(wpLower)
    })
    if (matched && !result.find(x => x.resource.id === matched.resource.id)) {
      result.push({
        resource: matched.resource,
        weakPoint: wp,
        author: matched.author,
        isOwn: matched.isOwn,
        quality: matched.quality,
      })
    }
    if (result.length >= 4) break
  }

  return result
})

// ===== 优质资源：质量评分 >= 75 =====
const qualityResourceList = computed(() => {
  return pool.value
    .filter(p => p.quality.score >= 75)
    .slice(0, 6)
})

// ===== 热门资源：按收藏/评分排序（质量门槛 >= 25） =====
const popularList = computed(() => {
  return pool.value
    .filter(p => p.quality.score >= 25)
    .map(p => ({
      resource: p.resource,
      author: p.author,
      isOwn: p.isOwn,
      favCount: (p.resource as any).favorited ? 1 : 0,
      rating: (p.resource as any).rating || 0,
      score: ((p.resource as any).rating || 0) * 2 + ((p.resource as any).favorited ? 5 : 0) + ((p.resource as any).mastered ? 3 : 0) + (p.resource.aiGenerated ? 1 : 0),
    }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map((x, i) => ({ ...x, rank: i + 1 }))
})

// ===== 全部资源：筛选 =====
const typeStats = computed(() => {
  const counts: Record<string, number> = {}
  pool.value.forEach(p => { counts[p.resource.type] = (counts[p.resource.type] || 0) + 1 })
  return Object.entries(counts).map(([key, count]) => ({
    key, label: typeLabels[key] || key, icon: typeIcons[key] || '📄', count,
  })).sort((a, b) => b.count - a.count)
})

const filteredPool = computed(() => {
  let list = [...pool.value]
  if (activeType.value !== 'all') list = list.filter(p => p.resource.type === activeType.value)
  if (activeQuality.value) list = list.filter(p => p.quality.level === activeQuality.value)
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.toLowerCase().trim()
    list = list.filter(p => {
      const r = p.resource
      return r.title?.toLowerCase().includes(kw) ||
             r.content?.toLowerCase().includes(kw) ||
             r.module?.toLowerCase().includes(kw)
    })
  }
  return list.sort((a, b) => new Date(b.resource.createdAt).getTime() - new Date(a.resource.createdAt).getTime())
})

function toggleQuality(ql: string) {
  activeQuality.value = activeQuality.value === ql ? null : ql
}

function clearFilters() {
  searchKeyword.value = ''
  activeType.value = 'all'
  activeQuality.value = null
}

function getContentPreview(content?: string): string {
  if (!content) return '暂无内容预览'
  const text = content
    .replace(/```[\s\S]*?```/g, '[代码块]')
    .replace(/!\[.*?\]\(.*?\)/g, '[图片]')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[#*`_~\-]/g, '')
    .replace(/\n+/g, ' ')
    .trim()
  return text.length > 100 ? text.substring(0, 100) + '...' : text
}

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function openDetail(resource: ResourceItem) {
  selectedResource.value = resource
  const poolItem = pool.value.find(p => p.resource.id === resource.id)
  if (poolItem) {
    selectedAuthor.value = poolItem.author
    selectedIsOwn.value = poolItem.isOwn
  } else {
    selectedAuthor.value = ''
    selectedIsOwn.value = true
  }
}
function closeDetail() {
  selectedResource.value = null
  selectedAuthor.value = ''
  selectedIsOwn.value = false
}

function onResourceUpdate(updated: ResourceItem) {
  if (selectedResource.value) selectedResource.value = updated
}

// ===== 数据加载 =====
async function loadCommunityData() {
  loading.value = true
  try {
    const [resourcesRes, statsRes, profileRes] = await Promise.all([
      request.get('/community/resources'),
      request.get('/community/stats'),
      request.get('/community/profile/summary'),
    ])

    if (resourcesRes.success && Array.isArray(resourcesRes.resources)) {
      pool.value = resourcesRes.resources.map((r: any) => ({
        resource: r as ResourceItem,
        author: r._author || '未知',
        authorId: r._authorId || 0,
        isOwn: r._isOwn || false,
        quality: r._quality || { score: 0, level: '待完善', dimensions: [] },
      }))
    }

    if (statsRes.success) {
      stats.value = {
        totalUsers: statsRes.totalUsers || 0,
        totalResources: statsRes.totalResources || 0,
      }
    }

    if (profileRes.success && Array.isArray(profileRes.dimensions)) {
      profileDimensions.value = profileRes.dimensions
    }
  } catch (e) {
    console.error('加载社区数据失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCommunityData()
  const rid = route.query.rid as string
  if (rid) {
    const target = pool.value.find(p => p.resource.id === rid)
    if (target) {
      selectedResource.value = target.resource
      selectedAuthor.value = target.author
      selectedIsOwn.value = target.isOwn
    }
  }
})
</script>

<style lang="less" scoped>
.community-view {
  padding: 24px;
  min-height: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

// 质量门槛提示
.quality-gate-notice {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px; border-radius: 8px;
  background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.15);
  margin-bottom: 20px;
}
.gate-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: #059669; color: #fff; font-size: 11px; font-weight: 700;
}
.gate-text { font-size: 12px; color: #047857; }

// 头部
.community-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 32px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.08));
  border: 1px solid rgba(37, 99, 235, 0.12);
  margin-bottom: 24px;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.header-icon { font-size: 36px; }
.header-title { font-size: 24px; font-weight: 700; color: #0f172a; }
.header-desc { font-size: 13px; color: #64748b; margin-top: 4px; }
.header-stats { display: flex; gap: 12px; }
.stat-pill {
  display: flex; flex-direction: column; align-items: center;
  padding: 12px 18px; border-radius: 10px;
  background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px);
  border: 1px solid rgba(37, 99, 235, 0.1); min-width: 72px;
  &.highlight { border-color: rgba(16, 185, 129, 0.3); background: rgba(16, 185, 129, 0.06); }
}
.stat-num { font-size: 24px; font-weight: 700; color: #2563eb; line-height: 1; }
.stat-pill.highlight .stat-num { color: #059669; }
.stat-label { font-size: 11px; color: #94a3b8; margin-top: 4px; font-weight: 500; }

// 加载状态
.loading-state { text-align: center; padding: 80px 20px; }
.loading-spinner {
  width: 40px; height: 40px; margin: 0 auto 16px;
  border: 3px solid #e2e8f0; border-top-color: #2563eb;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 14px; color: #64748b; }

// 空状态
.empty-state { text-align: center; padding: 60px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-title { font-size: 18px; font-weight: 600; color: #0f172a; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #64748b; margin-bottom: 20px; max-width: 400px; margin-left: auto; margin-right: auto; }
.empty-btn {
  padding: 10px 24px; border-radius: 8px; border: none;
  background: #2563eb; color: #fff; font-size: 14px; cursor: pointer;
  transition: background 0.2s;
  &:hover { background: #1d4ed8; }
}

// 画像提示
.profile-hint {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; border-radius: 10px;
  background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2);
  margin-bottom: 24px;
}
.hint-icon { font-size: 20px; }
.hint-text { flex: 1; font-size: 14px; color: #92400e; }
.hint-btn {
  padding: 6px 16px; border-radius: 6px; border: none;
  background: #f59e0b; color: #fff; font-size: 13px; cursor: pointer;
  &:hover { background: #d97706; }
}

// 推荐案例验证
.case-section {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(139, 92, 246, 0.04));
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 24px;
}
.case-validation {
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
}
.profile-dimensions, .match-result { flex: 1; min-width: 280px; }
.case-label { font-size: 12px; color: #6366f1; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
.dimension-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.dim-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 6px;
  background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.15);
}
.dim-label { font-size: 11px; color: #6366f1; font-weight: 500; }
.dim-value { font-size: 12px; color: #0f172a; font-weight: 600; }
.case-arrow { font-size: 24px; color: #6366f1; font-weight: 700; }
.match-summary { display: flex; gap: 20px; flex-wrap: wrap; }
.match-stat { font-size: 13px; color: #475569; }
.match-stat strong { color: #6366f1; font-size: 18px; }

// 区块
.community-section { margin-bottom: 32px; }
.section-header {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
  &.collapsible { cursor: pointer; user-select: none; }
}
.section-title {
  font-size: 18px; font-weight: 700; color: #0f172a; margin: 0;
  display: flex; align-items: center; gap: 8px;
}
.section-icon { font-size: 20px; }
.section-subtitle { font-size: 13px; color: #64748b; }
.collapse-arrow {
  font-size: 12px; color: #94a3b8; transition: transform 0.2s; margin-left: auto;
  &.expanded { transform: rotate(180deg); }
}

// 精选推荐卡片
.recommend-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;
}
.recommend-card {
  position: relative; padding: 20px; border-radius: 12px;
  background: #fff; border: 1px solid #e2e8f0; cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #3b82f6; box-shadow: 0 4px 16px rgba(59, 130, 246, 0.12); transform: translateY(-2px); }
}
.card-rank-badge {
  position: absolute; top: 12px; right: 12px;
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff;
  &.rank-1 { background: #f59e0b; }
  &.rank-2 { background: #94a3b8; }
  &.rank-3 { background: #b45309; }
  &[class*="rank-4"], &[class*="rank-5"], &[class*="rank-6"] { background: #cbd5e1; color: #475569; }
}

.card-top { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.card-type-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 6px; color: #fff; font-size: 12px; font-weight: 500;
  &.small { padding: 2px 8px; font-size: 11px; }
}
.card-subject-tag {
  padding: 2px 8px; border-radius: 4px; background: #f1f5f9;
  color: #475569; font-size: 12px;
}
.ai-badge {
  padding: 2px 6px; border-radius: 4px; background: rgba(168, 85, 247, 0.1);
  color: #a855f7; font-size: 11px; font-weight: 600;
}
.card-title {
  font-size: 15px; font-weight: 600; color: #0f172a; margin-bottom: 8px;
  line-height: 1.4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  &.small { font-size: 14px; }
}
.card-preview {
  font-size: 13px; color: #64748b; line-height: 1.5; margin-bottom: 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-author { margin-bottom: 10px; }
.author-tag {
  font-size: 11px; color: #64748b; padding: 2px 8px; border-radius: 4px;
  background: #f1f5f9;
  &.own { color: #059669; background: rgba(16, 185, 129, 0.08); }
}
.card-reasons { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.reason-tag {
  padding: 3px 8px; border-radius: 4px; background: rgba(37, 99, 235, 0.08);
  color: #2563eb; font-size: 11px; font-weight: 500;
}
.card-match-score { display: flex; align-items: center; gap: 8px; }
.match-bar {
  flex: 1; height: 6px; border-radius: 3px; background: #e2e8f0; overflow: hidden;
}
.match-fill {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  transition: width 0.3s;
}
.match-text { font-size: 12px; color: #2563eb; font-weight: 600; white-space: nowrap; }

// 薄弱点突破
.weak-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;
}
.weak-card {
  padding: 20px; border-radius: 12px; background: #fff;
  border: 1px solid rgba(245, 158, 11, 0.2); cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #f59e0b; box-shadow: 0 4px 16px rgba(245, 158, 11, 0.12); transform: translateY(-2px); }
}
.weak-point-tag {
  display: inline-block; padding: 4px 10px; border-radius: 6px;
  background: rgba(245, 158, 11, 0.1); color: #92400e;
  font-size: 12px; font-weight: 600; margin-bottom: 12px;
}

// 优质资源
.quality-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
}
.quality-card {
  padding: 20px; border-radius: 12px; background: #fff;
  border: 1px solid rgba(16, 185, 129, 0.2); cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: #059669; box-shadow: 0 4px 16px rgba(16, 185, 129, 0.12); transform: translateY(-2px); }
}
.quality-dimensions { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.dim-badge {
  padding: 2px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.08);
  color: #059669; font-size: 11px; font-weight: 500;
}

// 热门资源
.popular-list { display: flex; flex-direction: column; gap: 8px; }
.popular-item {
  display: flex; align-items: center; gap: 12px; padding: 14px 16px;
  border-radius: 10px; background: #fff; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all 0.2s;
  &:hover { border-color: #3b82f6; background: #f8fafc; }
}
.popular-rank {
  width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff; background: #3b82f6;
}
.popular-info { flex: 1; min-width: 0; }
.popular-meta { display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.meta-tag {
  font-size: 11px; color: #64748b; padding: 1px 6px; border-radius: 4px; background: #f1f5f9;
  &.ai { color: #a855f7; background: rgba(168, 85, 247, 0.08); }
  &.author-meta.own { color: #059669; background: rgba(16, 185, 129, 0.08); }
}
.popular-arrow { color: #cbd5e1; font-size: 18px; }

// 全部资源
.all-resources-content { margin-top: 16px; }
.filter-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.search-box {
  display: flex; align-items: center; gap: 8px; flex: 1; min-width: 200px;
  padding: 8px 12px; border-radius: 8px; border: 1px solid #e2e8f0; background: #fff;
}
.search-icon { color: #94a3b8; }
.search-input { flex: 1; border: none; outline: none; font-size: 14px; background: transparent; }
.type-filter-chips, .quality-filter-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-chip {
  padding: 6px 12px; border-radius: 6px; border: 1px solid #e2e8f0;
  background: #fff; color: #475569; font-size: 12px; cursor: pointer;
  transition: all 0.2s;
  &.active { background: #2563eb; color: #fff; border-color: #2563eb; }
  &.quality-chip.active {
    background: #059669; border-color: #059669;
    &.ql-优质 { background: #059669; }
    &.ql-良好 { background: #2563eb; }
    &.ql-基础 { background: #f59e0b; }
    &.ql-待完善 { background: #94a3b8; }
  }
}
.resource-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;
}
.community-card {
  padding: 16px; border-radius: 10px; background: #fff;
  border: 1px solid #e2e8f0; cursor: pointer; transition: all 0.2s;
  &:hover { border-color: #3b82f6; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
}
.card-bottom {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 8px; font-size: 12px; color: #94a3b8;
}
.card-date { font-size: 12px; }
.card-click-hint { font-size: 12px; color: #3b82f6; font-weight: 500; }
.no-result { text-align: center; padding: 40px; color: #64748b; }
.clear-btn {
  margin-top: 12px; padding: 6px 16px; border-radius: 6px;
  border: 1px solid #e2e8f0; background: #fff; color: #475569; cursor: pointer;
  &:hover { border-color: #3b82f6; color: #3b82f6; }
}

// 详情弹窗
.detail-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.detail-panel {
  background: #fff; border-radius: 14px; max-width: 800px; width: 100%;
  max-height: 85vh; display: flex; flex-direction: column; overflow: hidden;
}
.detail-header-bar {
  display: flex; align-items: center; gap: 12px; padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0; flex-wrap: wrap;
}
.detail-subject { font-size: 13px; color: #64748b; }
.detail-author {
  font-size: 12px; color: #64748b; padding: 2px 8px; border-radius: 4px; background: #f1f5f9;
  margin-left: auto;
  &.own { color: #059669; background: rgba(16, 185, 129, 0.08); }
}
.detail-close {
  width: 32px; height: 32px; border-radius: 8px;
  border: none; background: #f1f5f9; color: #475569; cursor: pointer; font-size: 16px;
  &:hover { background: #e2e8f0; }
}
.detail-body-wrapper { flex: 1; overflow-y: auto; padding: 20px; }
</style>
