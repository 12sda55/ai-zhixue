import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  css: {
    preprocessorOptions: {
      less: {
        javascriptEnabled: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // 将大型依赖拆分为独立 chunk，优化首屏加载
          if (id.includes('echarts')) return 'echarts'
          if (id.includes('markdown-it') || id.includes('highlight.js')) return 'markdown'
          if (id.includes('ant-design-vue') || id.includes('@ant-design/icons-vue')) return 'ant-design'
          if (id.includes('markmap-lib') || id.includes('markmap-view')) return 'markmap'
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      // 视频静态文件 → ai_tutor（端口8001）
      '/static/videos': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // 视频生成API → ai_tutor（端口8001，去掉 /v1 前缀匹配 /api/video/...）
      '/api/v1/video': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
      },
      // API v1 → 后端8000（后端路由前缀即为 /api/v1，无需 rewrite）
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 离线降级：直连 DeepSeek（后端不可用时）
      '/api/glm': {
        target: 'https://api.deepseek.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/glm/, ''),
      },
    },
  },
})
