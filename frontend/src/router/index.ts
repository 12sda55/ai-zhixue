import { createRouter, createWebHistory } from 'vue-router'
import { safeGetItem, safeGetJSON } from '../shared/utils/storage'

const routes = [
  // 产品首页（液态玻璃风格）
  { path: '/landing', name: 'Landing', component: () => import('../modules/landing/views/LandingView.vue') },

  // 登录/注册（液态玻璃风格）
  { path: '/login', name: 'Login', component: () => import('../modules/auth/views/LoginView.vue') },
  { path: '/register', name: 'Register', component: () => import('../modules/auth/views/LoginView.vue') },

  // 学生端（AppLayout）
  {
    path: '/',
    component: () => import('../shared/components/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Home', component: () => import('../modules/home/views/HomeView.vue') },
      { path: 'profile', name: 'Profile', component: () => import('../modules/profile/views/ProfileView.vue') },
      { path: 'agent', name: 'Agent', component: () => import('../modules/agent/views/AgentView.vue') },
      { path: 'resource', name: 'Resource', component: () => import('../modules/resource/views/ResourceView.vue') },
      { path: 'community', name: 'Community', component: () => import('../modules/community/views/CommunityView.vue') },
      { path: 'history', name: 'History', component: () => import('../modules/resource/views/HistoryView.vue') },
      { path: 'path', name: 'Path', component: () => import('../modules/path/views/PathView.vue') },
      { path: 'workspace', name: 'Workspace', component: () => import('../modules/workspace/views/WorkspaceView.vue') },
      { path: 'qa', name: 'Qa', component: () => import('../modules/qa/views/QAView.vue') },
      { path: 'assess', name: 'Assess', component: () => import('../modules/assess/views/AssessView.vue') },
      { path: 'learning-effect', name: 'LearningEffect', component: () => import('../modules/assess/views/LearningEffectView.vue') },
      { path: 'gallery', name: 'Gallery', component: () => import('../modules/gallery/views/GalleryView.vue') },
      { path: 'gallery/:id', name: 'GalleryDetail', component: () => import('../modules/gallery/views/GalleryDetailView.vue') },
    ],
  },

  // 管理端（AdminLayout）
  {
    path: '/admin',
    component: () => import('../modules/admin/components/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', name: 'AdminDashboard', component: () => import('../modules/admin/views/DashboardView.vue') },
      { path: 'learning-stats', name: 'LearningStats', component: () => import('../modules/admin/views/LearningStatsView.vue') },
      { path: 'users', name: 'AdminUsers', component: () => import('../modules/admin/views/UsersView.vue') },
      { path: 'resources', name: 'AdminResources', component: () => import('../modules/admin/views/ResourcesManageView.vue') },
      { path: 'agents', name: 'AdminAgents', component: () => import('../modules/admin/views/AgentsView.vue') },
      { path: 'content', name: 'AdminContent', component: () => import('../modules/admin/views/ContentView.vue') },
      { path: 'settings', name: 'AdminSettings', component: () => import('../modules/admin/views/SettingsView.vue') },
      { path: 'screen', name: 'DataScreen', component: () => import('../modules/admin/views/DataScreenView.vue') },
      { path: 'audit-logs', name: 'AdminAuditLogs', component: () => import('../modules/admin/views/AuditLogsView.vue') },
    ],
  },

  // 数据大屏公开访问
  { path: '/data-screen', name: 'PublicDataScreen', component: () => import('../modules/admin/views/DataScreenView.vue') },

  // 404
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../shared/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = safeGetItem('token')
  const user = safeGetJSON<{ role?: string } | null>('user', null)

  // 安全访问 meta，防止 null/undefined
  const meta = to.meta || {}

  // 需要认证但未登录 → 跳转产品首页
  if (meta.requiresAuth && !token) {
    return next('/landing')
  }

  // 需要 admin 角色但不是 admin
  if (meta.requiresAdmin && user?.role !== 'admin') {
    return next('/')
  }

  // 已登录访问登录页/产品首页 → 跳转应用首页
  if ((to.path === '/login' || to.path === '/register' || to.path === '/landing') && token) {
    return next(user?.role === 'admin' ? '/admin/dashboard' : '/')
  }

  next()
})

// 路由错误处理：当懒加载模块失败时（如浏览器缓存了旧版本），自动刷新页面
router.onError((error) => {
  console.error('[Router] 导航错误:', error)
  const msg = error.message || ''
  if (
    msg.includes('Failed to fetch dynamically imported module') ||
    msg.includes('Importing a module script failed') ||
    msg.includes('error loading dynamically imported module') ||
    msg.includes('Loading chunk') ||
    msg.includes('Loading CSS chunk') ||
    msg.includes('error loading asynchronously imported module')
  ) {
    console.warn('[Router] 模块加载失败，正在刷新页面以恢复...')
    window.location.reload()
  }
})

export default router
