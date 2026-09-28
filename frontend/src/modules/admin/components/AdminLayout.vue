<template>
  <div class="admin-layout">
    <!-- 粒子背景 -->
    <ParticleBackground v-if="appStore.particleEnabled" />
    <!-- 侧边栏 -->
    <div class="sidebar" :class="{ collapsed }">
      <div class="sidebar-logo">
        <div class="logo-icon">AM</div>
        <div v-if="!collapsed" class="logo-info">
          <div class="logo-title">管理端</div>
          <div class="logo-badge">ADMIN</div>
        </div>
      </div>

      <div class="sidebar-menu">
        <div
          v-for="item in menuItems"
          :key="item.path"
          class="menu-item"
          :class="{ active: isActive(item.path) }"
          @click="router.push(item.path)"
        >
          <span class="menu-icon"><component :is="item.iconComp" /></span>
          <span v-if="!collapsed" class="menu-label">{{ item.label }}</span>
          <span v-if="!collapsed && item.highlight" class="menu-highlight-badge">★</span>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="switch-btn" @click="authStore.switchToStudent()">
          <span v-if="!collapsed"><SvgIcon name="major" size="16" /> 学生端</span>
          <span v-else><SvgIcon name="major" size="16" /></span>
        </div>
        <div class="collapse-btn" @click="collapsed = !collapsed">
          {{ collapsed ? '→' : '←' }}
        </div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="main-area">
      <!-- 顶部栏 -->
      <div class="top-bar">
        <div class="top-left">
          <span class="breadcrumb">管理端</span>
          <span class="breadcrumb-sep">/</span>
          <span class="page-title">{{ currentPageTitle }}</span>
        </div>
        <div class="top-right">
          <!-- 实时时钟 -->
          <div class="header-clock">
            <span class="clock-time">{{ currentTime }}</span>
          </div>

          <!-- 粒子开关 -->
          <button class="icon-btn particle-toggle" :class="{ active: appStore.particleEnabled }" @click="appStore.toggleParticle()" :title="appStore.particleEnabled ? '关闭粒子效果' : '开启粒子效果'">
            <SvgIcon name="sparkles" size="18" />
          </button>

          <!-- 粒子设置按钮（仅粒子开启时显示） -->
          <div v-if="appStore.particleEnabled" class="particle-control-wrap">
            <button class="icon-btn particle-settings-btn" :class="{ active: appStore.particlePanelOpen }" @click="appStore.toggleParticlePanel()" title="粒子设置">
              <SvgIcon name="settings" size="16" />
            </button>
            <transition name="panel-fade">
              <div v-if="appStore.particlePanelOpen" class="particle-panel" @click.stop>
                <div class="panel-header">
                  <span>粒子设置</span>
                  <button class="panel-close" @click="appStore.particlePanelOpen = false">×</button>
                </div>
                <div class="panel-section">
                  <div class="section-label">移动速度</div>
                  <div class="segment-control">
                    <button v-for="s in speedOptions" :key="s.value" class="segment-btn" :class="{ active: appStore.particleSpeed === s.value }" @click="appStore.setParticleSpeed(s.value)">{{ s.label }}</button>
                  </div>
                </div>
                <div class="panel-section">
                  <div class="section-label">聚拢范围</div>
                  <div class="segment-control">
                    <button v-for="g in gatherOptions" :key="g.value" class="segment-btn" :class="{ active: appStore.particleGatherSize === g.value }" @click="appStore.setParticleGatherSize(g.value)">{{ g.label }}</button>
                  </div>
                </div>
                <div class="panel-hint">长按屏幕聚拢粒子，松开散开</div>
              </div>
            </transition>
          </div>
          <div class="search-box" :class="{ focused: showSearchResults }">
            <span class="search-icon"><SvgIcon name="search" size="16" /></span>
            <input v-model="searchQuery" type="text" placeholder="搜索菜单..." class="search-input" @focus="showSearchResults = true" @blur="handleSearchBlur" />
            <div v-if="showSearchResults && searchResults.length > 0" class="search-dropdown">
              <div v-for="item in searchResults" :key="item.path" class="search-result-item" @mousedown.prevent="navigateToSearchResult(item.path)">
                <component :is="item.iconComp" />
                <span>{{ item.label }}</span>
              </div>
            </div>
          </div>
          <div class="system-status">
            <span class="status-dot" />
            系统正常
          </div>
          <div class="notifications" @click="router.push('/admin/dashboard')">
            <span><SvgIcon name="bell" size="18" /></span>
            <span v-if="adminStore.unreadCount > 0" class="notification-badge">{{ adminStore.unreadCount }}</span>
          </div>
          <a-dropdown placement="bottomRight">
            <div class="admin-user-area">
              <div class="admin-avatar">A</div>
              <span class="admin-name">{{ authStore.user?.username || 'Admin' }}</span>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="student" @click="authStore.switchToStudent()">
                  <span><SvgIcon name="major" size="16" /> 切换到学生端</span>
                </a-menu-item>
                <a-menu-item key="logout" @click="handleLogout">
                  <LogoutOutlined />
                  <span style="margin-left: 8px">退出登录</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>

      <!-- 内容 -->
      <div class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../auth/stores/authStore'
import { useAppStore } from '../../../stores/appStore'
import { useAdminStore } from '../stores/adminStore'
import ParticleBackground from '../../../shared/components/ParticleBackground.vue'
import SvgIcon from '../../../shared/components/SvgIcon.vue'
import { DashboardOutlined, TeamOutlined, RobotOutlined, BookOutlined, SettingOutlined, FundProjectionScreenOutlined, LogoutOutlined, FileTextOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()
const adminStore = useAdminStore()
const collapsed = ref(false)

// 搜索功能
const searchQuery = ref('')
const showSearchResults = ref(false)
const searchResults = computed(() => {
  if (!searchQuery.value.trim()) return []
  const q = searchQuery.value.toLowerCase()
  return menuItems.filter(item =>
    item.label.toLowerCase().includes(q)
  )
})

function navigateToSearchResult(path: string) {
  searchQuery.value = ''
  showSearchResults.value = false
  router.push(path)
}

function handleSearchBlur() {
  setTimeout(() => { showSearchResults.value = false }, 200)
}

// 实时时钟
let clockTimer: number | null = null
const currentTime = ref('')
function updateClock() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  const ss = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${y}/${m}/${d} ${hh}:${mm}:${ss}`
}
updateClock()
clockTimer = window.setInterval(updateClock, 1000)

// 通知刷新定时器
let notificationTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  adminStore.loadNotifications()
  // 每 60 秒刷新通知
  notificationTimer = setInterval(() => adminStore.loadNotifications(), 60000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (notificationTimer) clearInterval(notificationTimer)
})

// 粒子控制选项
const speedOptions = [
  { value: 'slow' as const, label: '慢速' },
  { value: 'normal' as const, label: '正常' },
  { value: 'fast' as const, label: '快速' },
]
const gatherOptions = [
  { value: 'small' as const, label: '小' },
  { value: 'medium' as const, label: '中' },
  { value: 'large' as const, label: '大' },
]

const menuItems = [
  { path: '/admin/dashboard', label: '数据看板', iconComp: DashboardOutlined },
  { path: '/admin/users', label: '用户管理', iconComp: TeamOutlined },
  { path: '/admin/agents', label: 'Agent监控', iconComp: RobotOutlined },
  { path: '/admin/content', label: '内容管理', iconComp: BookOutlined },
  { path: '/admin/settings', label: '系统设置', iconComp: SettingOutlined },
  { path: '/admin/audit-logs', label: '审计日志', iconComp: FileTextOutlined },
  { path: '/admin/screen', label: '数据大屏', iconComp: FundProjectionScreenOutlined, highlight: true },
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(m => route.path.startsWith(m.path))
  return item?.label || '管理端'
})

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style lang="less" scoped>
.admin-layout {
  display: flex;
  height: 100%;
  background: transparent;
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 220px;
  background: transparent;
  border-right: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
  box-shadow: 2px 0 8px rgba(76, 78, 100, 0.06);

  &.collapsed { width: 64px; }
}

.sidebar-logo {
  padding: 18px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: #FFFFFF;
  flex-shrink: 0;
}

.logo-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-title {
  font-size: 14px;
  font-weight: 700;
  color: #FFFFFF;
}

.logo-badge {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.2);
  padding: 1px 6px;
  border-radius: 3px;
  display: inline-block;
}

.sidebar-menu {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { background: transparent; color: #0f172a; }

  &.active {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }
}

.menu-icon { flex-shrink: 0; }
.menu-label { flex: 1; font-weight: 500; }

.menu-badge {
  font-size: 10px;
  background: rgba(37, 99, 235, 0.15);
  color: #2563eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.menu-highlight-badge {
  margin-left: auto;
  color: #00d4ff;
  font-size: 12px;
  animation: star-pulse 2s ease-in-out infinite;
}

@keyframes star-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.sidebar-footer {
  padding: 12px 10px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.switch-btn {
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(37, 99, 235, 0.3);
  color: #2563eb;
  font-size: 12px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  span { display: inline-flex; align-items: center; gap: 4px; }

  &:hover { background: rgba(37, 99, 235, 0.15); }
}

.collapse-btn {
  padding: 6px;
  border-radius: 6px;
  background: rgba(37, 99, 235, 0.06);
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  text-align: center;

  &:hover { color: #475569; background: rgba(37, 99, 235, 0.1); }
}

/* ===== 主体 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  box-shadow: 0 2px 4px rgba(76, 78, 100, 0.04);
}

.top-left { display: flex; align-items: center; gap: 8px; }

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.breadcrumb {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 400;
}

.breadcrumb-sep {
  font-size: 13px;
  color: rgba(37, 99, 235, 0.15);
  margin: 0 2px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: transparent;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  width: 200px;
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  z-index: 200;
  overflow: hidden;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: #0f172a;
  cursor: pointer;

  &:hover { background: rgba(37, 99, 235, 0.06); }
}

.search-icon { color: #94a3b8; display: flex; align-items: center; justify-content: center; }

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 12px;
  color: #0f172a;

  &::placeholder { color: #94a3b8; }
}

.system-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #10b981;
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.6);
}

.notifications {
  position: relative;
  padding: 6px;
  cursor: pointer;

  span:first-child { display: flex; align-items: center; justify-content: center; }
}

.notification-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  font-size: 9px;
  background: #ef4444;
  color: #FFFFFF;
  padding: 1px 4px;
  border-radius: 4px;
  font-weight: 600;
}

.admin-user-area {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.admin-avatar {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: bold;
  color: #FFFFFF;
}

.admin-name {
  font-size: 13px;
  color: #0f172a;
  font-weight: 500;
}

// 粒子开关按钮
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
}

.particle-toggle {
  &.active {
    color: #06b6d4;

    &:hover {
      color: #06b6d4;
      background: rgba(6, 182, 212, 0.08);
    }
  }
}

// 实时时钟
.header-clock {
  display: flex;
  align-items: center;
  padding: 0 10px;
  height: 30px;
  border-radius: 7px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 182, 212, 0.06));
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.clock-time {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.3px;
  white-space: nowrap;
}

// 粒子设置按钮
.particle-settings-btn {
  width: 34px !important;
  height: 34px !important;
  border-radius: 8px !important;

  &.active {
    color: #06b6d4;
    background: rgba(6, 182, 212, 0.1);
  }
}

// 粒子控制面板
.particle-control-wrap {
  position: relative;
}

.particle-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 210px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(37, 99, 235, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 0;
  z-index: 100;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
  border-bottom: 1px solid rgba(37, 99, 235, 0.06);
}

.panel-close {
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  line-height: 1;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
    color: #475569;
  }
}

.panel-section {
  padding: 8px 12px;
}

.section-label {
  font-size: 10px;
  font-weight: 500;
  color: #94a3b8;
  margin-bottom: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.segment-control {
  display: flex;
  gap: 3px;
  background: rgba(37, 99, 235, 0.04);
  border-radius: 7px;
  padding: 3px;
}

.segment-btn {
  flex: 1;
  padding: 4px 0;
  border: none;
  background: transparent;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    color: #2563eb;
    background: rgba(37, 99, 235, 0.06);
  }

  &.active {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: #fff;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
  }
}

.panel-hint {
  padding: 6px 12px 8px;
  font-size: 10px;
  color: #94a3b8;
  text-align: center;
  border-top: 1px solid rgba(37, 99, 235, 0.04);
}

// 面板过渡动画
.panel-fade-enter-active,
.panel-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.panel-fade-enter-from,
.panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>

<style lang="less">
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>