<template>
  <a-layout class="app-layout">
    <ParticleBackground v-if="appStore.particleEnabled" />
    <!-- 侧边栏 -->
    <a-layout-sider
      v-model:collapsed="appStore.sidebarCollapsed"
      :width="260"
      :collapsedWidth="72"
      :trigger="null"
      class="app-sidebar"
    >
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-inner">
          <div class="logo-icon">
            <span>AI</span>
          </div>
          <transition name="fade">
            <span v-if="!appStore.sidebarCollapsed" class="logo-text">学习系统</span>
          </transition>
        </div>
      </div>

      <!-- 导航 -->
      <div class="sidebar-nav" data-guide="nav-overview">
        <div v-if="!appStore.sidebarCollapsed" class="nav-section">主菜单</div>
        <div
          v-for="item in menuItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :data-guide="item.guideId"
          @click="router.push(item.path)"
        >
          <span class="nav-icon"><SvgIcon :name="item.icon" /></span>
          <transition name="fade">
            <span v-if="!appStore.sidebarCollapsed" class="nav-label">{{ item.label }}</span>
          </transition>
        </div>
      </div>

      <!-- 底部 -->
      <div v-if="!appStore.sidebarCollapsed" class="sidebar-footer">
        <div class="course-card">
          <div class="course-label">知识掌握度</div>
          <div class="course-name">{{ profileStore.knowledgeMastery }}/100</div>
          <div class="course-progress">
            <div class="progress-bar" :style="{ width: profileStore.knowledgeMastery + '%' }"></div>
          </div>
          <div class="course-tips">
            <div class="tip-item">
              <span class="tip-icon">📚</span>
              <span>完成学习资源 +5分</span>
              <span class="tip-path">路径 → 学习资源</span>
            </div>
            <div class="tip-item">
              <span class="tip-icon">🎯</span>
              <span>完成学习阶段 +10分</span>
              <span class="tip-path">路径 → 完成阶段</span>
            </div>
            <div class="tip-item">
              <span class="tip-icon">📝</span>
              <span>完成测评评估 +8分</span>
              <span class="tip-path">评估 → 做测评</span>
            </div>
          </div>
        </div>
      </div>
    </a-layout-sider>

    <a-layout class="main-layout">
      <!-- 顶栏 -->
      <a-layout-header class="app-header">
        <div class="header-left">
          <button class="collapse-btn" @click="appStore.sidebarCollapsed = !appStore.sidebarCollapsed">
            <SvgIcon name="menu" size="18" />
          </button>
        </div>

        <div class="header-right">
          <!-- 管理员入口 -->
          <div v-if="authStore.isAdmin" class="admin-badge" @click="authStore.switchToAdmin()">
            <span>管理端</span>
          </div>

          <!-- 粒子开关 -->
          <button class="icon-btn particle-toggle" :class="{ active: appStore.particleEnabled }" @click="appStore.toggleParticle()" :title="appStore.particleEnabled ? '关闭粒子效果' : '开启粒子效果'">
            <SvgIcon name="sparkles" size="18" />
          </button>

          <!-- 通知图标 -->
          <button class="icon-btn">
            <SvgIcon name="bell" size="20" />
            <span v-if="profileStore.profileJustUpdated" class="badge-dot badge-blue"></span>
          </button>

          <!-- 用户 -->
          <a-dropdown placement="bottomRight">
            <div class="user-info">
              <div class="user-avatar">
                {{ authStore.user?.username?.[0]?.toUpperCase() || 'U' }}
              </div>
              <div class="user-detail">
                <div class="user-name">{{ authStore.user?.username || '用户' }}</div>
                <div class="user-role">{{ authStore.isAdmin ? '管理员' : '学员' }}</div>
              </div>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="logout" @click="handleLogout">
                  <span>退出登录</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <!-- 主内容 -->
      <a-layout-content class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </a-layout-content>
    </a-layout>

    <!-- 新用户产品引导 -->
    <ProductGuide />
  </a-layout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../modules/auth/stores/authStore'
import { useProfileStore } from '../../modules/profile/stores/profileStore'
import { useAppStore } from '../../stores/appStore'
import { useProductGuideStore } from '../stores/productGuideStore'
import ParticleBackground from './ParticleBackground.vue'
import SvgIcon from './SvgIcon.vue'
import ProductGuide from './ProductGuide.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const appStore = useAppStore()
const productGuideStore = useProductGuideStore()

const menuItems = [
  { path: '/', icon: 'home', label: '首页', guideId: 'nav-home' },
  { path: '/profile', icon: 'profile', label: '画像', guideId: 'nav-profile' },
  { path: '/agent', icon: 'robot', label: '智能体', guideId: 'nav-agent' },
  { path: '/resource', icon: 'book', label: '资源', guideId: 'nav-resource' },
  { path: '/community', icon: 'users', label: '社区', guideId: 'nav-community' },
  { path: '/history', icon: 'history', label: '历史', guideId: 'nav-history' },
  { path: '/path', icon: 'path', label: '路径', guideId: 'nav-path' },
  { path: '/workspace', icon: 'workspace', label: '工作台', guideId: 'nav-workspace' },
  { path: '/qa', icon: 'chat', label: '答疑', guideId: 'nav-qa' },
  { path: '/assess', icon: 'assess', label: '答题评估', guideId: 'nav-assess' },
  { path: '/learning-effect', icon: 'bar-chart', label: '学习效果', guideId: 'nav-learning-effect' },
  { path: '/gallery', icon: 'trophy', label: '展馆', guideId: 'nav-gallery' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 新用户首次登录引导
onMounted(() => {
  productGuideStore.loadState()
  // 延迟显示，确保页面完全渲染
  setTimeout(() => {
    if (productGuideStore.shouldShowGuide) {
      productGuideStore.showGuide()
    }
  }, 800)
})
</script>

<style lang="less" scoped>
.app-layout {
  height: 100vh;
  min-height: 100vh;
  background: transparent !important;
}

// ============================================
// 侧边栏
// ============================================
.app-sidebar {
  background: transparent !important;
  border-right: 1px solid rgba(37, 99, 235, 0.1) !important;
  box-shadow: 0 0 12px rgba(76, 78, 100, 0.04) !important;
  overflow: hidden;
  position: relative;
  z-index: 10;

  :deep(.ant-layout-sider-children) {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
}

.sidebar-logo {
  padding: 20px 20px 16px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.06);
}

.logo-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.5px;
}

// 导航
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-section {
  padding: 12px 12px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #475569;

  .nav-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    color: #475569;
    flex-shrink: 0;
  }

  .nav-label {
    font-size: 14px;
    font-weight: 500;
  }

  &:hover {
    background: rgba(37, 99, 235, 0.06);
    color: #2563eb;

    .nav-icon {
      color: #2563eb;
    }
  }

  &.active {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);

    .nav-icon {
      color: #FFFFFF;
    }
  }
}

// 底部卡片
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(37, 99, 235, 0.06);
}

.course-card {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border-radius: 10px;
  padding: 12px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.course-label {
  font-size: 11px;
  opacity: 0.85;
  margin-bottom: 2px;
}

.course-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}

.course-progress {
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.course-tips {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 10px;
  opacity: 0.85;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.tip-icon {
  font-size: 10px;
}

.tip-path {
  font-size: 9px;
  opacity: 0.7;
  background: rgba(255, 255, 255, 0.15);
  padding: 1px 3px;
  border-radius: 2px;
  margin-left: 2px;
}

// ============================================
// 主布局
// ============================================
.main-layout {
  background: transparent !important;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

// ============================================
// 顶栏
// ============================================
.app-header {
  background: rgba(232, 240, 249, 0.85) !important;
  backdrop-filter: blur(20px) saturate(1.3);
  height: 64px !important;
  line-height: 64px !important;
  padding: 0 24px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #475569;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
    color: #2563eb;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-badge {
  padding: 6px 14px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.12);
  font-size: 13px;
  font-weight: 500;
  color: #2563eb;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.2);
  }
}

.icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #475569;
  position: relative;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
    color: #2563eb;
  }

  .badge-dot {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 8px;
    height: 8px;
    background: #ef4444;
    border-radius: 50%;
    border: 2px solid #fff;

    &.badge-blue {
      background: #00d4ff;
    }
  }
}

// 粒子开关按钮
.particle-toggle {
  &.active {
    color: #06b6d4;

    &:hover {
      color: #06b6d4;
      background: rgba(6, 182, 212, 0.08);
    }
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
  }
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-detail {
  display: flex;
  flex-direction: column;
  line-height: 1.2;

  .user-name {
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 2px;
  }

  .user-role {
    font-size: 12px;
    color: #94a3b8;
  }
}

// ============================================
// 主内容
// ============================================
.app-content {
  background: transparent !important;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
}

.app-layout {
  :deep(.ant-layout) {
    background: transparent !important;
  }
  :deep(.ant-layout-content) {
    background: transparent !important;
  }
  :deep(.ant-layout-sider) {
    background: transparent !important;
  }
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// ============================================
// 响应式
// ============================================
@media (max-width: 768px) {
  .app-sidebar {
    position: fixed !important;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100 !important;
  }

  .user-detail {
    display: none !important;
  }

  .app-header {
    padding: 0 16px !important;
  }
}

@media (max-width: 576px) {
  .admin-badge {
    display: none !important;
  }
}
</style>