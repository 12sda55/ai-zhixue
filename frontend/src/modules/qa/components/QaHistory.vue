<template>
  <div class="qa-history">
    <div class="history-header">
      <span>历史记录</span>
      <button class="clear-btn" @click="store.clearChat()">🗑️</button>
    </div>
    <div class="history-list">
      <div
        v-for="(item, idx) in store.history"
        :key="idx"
        class="history-item"
        @click="store.sendMessage(item.question)"
      >
        <div class="item-question">{{ item.question }}</div>
        <div class="item-meta">
          <span class="item-type">{{ item.type }}</span>
          <span class="item-time">{{ item.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useQaStore } from '../stores/qaStore'

const store = useQaStore()
</script>

<style lang="less" scoped>
.qa-history {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #EBE9F1;
  color: #2F2B3D;
  font-size: 12px;
  font-weight: 600;
}

.clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  opacity: 0.5;
  transition: opacity 0.2s;
  &:hover { opacity: 1; }
}

.history-list {
  flex: 1;
  overflow: auto;
  padding: 8px;
}

.history-item {
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 4px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: transparent;
  }
}

.item-question {
  color: #5E5873;
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 9px;
}

.item-type {
  background: rgba(0, 207, 232, 0.1);
  border-radius: 3px;
  padding: 1px 5px;
  color: #00CFE8;
}

.item-time { color: #A8AAAE; }
</style>