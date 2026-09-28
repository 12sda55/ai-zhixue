<template>
  <div class="not-found">
    <div class="glitch-text">404</div>
    <div class="not-found-desc">页面未找到</div>
    <div class="not-found-sub">你访问的页面不存在或已被移除</div>
    <a-button type="primary" class="back-btn" @click="goHome">返回首页</a-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  const userJson = localStorage.getItem('user')
  const user = userJson ? JSON.parse(userJson) : null
  router.push(user?.role === 'admin' ? '/admin/dashboard' : '/')
}
</script>

<style lang="less" scoped>
.not-found {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0a0e27;
}

.glitch-text {
  font-size: 120px;
  font-weight: 900;
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.3), 2px 2px 0 #ef4444, -2px -2px 0 #6366f1;
  animation: glitch 2s infinite;
  line-height: 1;
}

.not-found-desc {
  color: #e8f4fd;
  font-size: 22px;
  font-weight: 600;
  margin-top: 16px;
}

.not-found-sub {
  color: #5a7a8a;
  font-size: 13px;
  margin-top: 8px;
}

.back-btn {
  margin-top: 24px;
  background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
  border: none !important;
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.3) !important;
  font-weight: 600;
  border-radius: 8px;
  height: 36px;
}

@keyframes glitch {
  0%, 90%, 100% { transform: translate(0); }
  92% { transform: translate(-2px, 1px); }
  94% { transform: translate(2px, -1px); }
  96% { transform: translate(-1px, 2px); }
  98% { transform: translate(1px, -2px); }
}
</style>