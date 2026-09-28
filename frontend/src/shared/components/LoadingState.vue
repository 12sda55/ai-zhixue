<template>
  <div class="loading-state" v-if="loading">
    <div class="loading-spinner"></div>
    <div class="loading-text">{{ text }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
  text?: string
}>()
</script>

<style lang="less" scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(0, 212, 255, 0.15);
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
}

.loading-text {
  color: #5a7a8a;
  font-size: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>