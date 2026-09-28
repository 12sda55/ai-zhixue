<template>
  <div class="settings-view">
    <!-- 头部 -->
    <div class="settings-header">
      <span class="page-title">系统设置</span>
      <div class="header-actions">
        <a-button @click="clearCache">
          <DeleteOutlined /> 清理缓存
        </a-button>
        <a-button type="primary" @click="saveSettings">
          <SaveOutlined /> 保存设置
        </a-button>
      </div>
    </div>

    <div class="settings-grid">
      <!-- API 配置 -->
      <div class="settings-card">
        <div class="card-title"><ApiOutlined /> API 配置</div>
        <div class="form-group">
          <label>API 地址</label>
          <a-input v-model:value="settings.api_base_url" placeholder="输入 API 地址" />
        </div>
        <div class="form-group">
          <label>模型名称</label>
          <a-input v-model:value="settings.model_name" placeholder="如: deepseek-chat" />
        </div>
        <div class="form-group">
          <label>最大 Token</label>
          <a-input-number v-model:value="settings.max_tokens" :min="1" :max="128000" style="width: 100%" />
        </div>
        <div class="form-group">
          <label>Temperature</label>
          <a-slider v-model:value="settings.temperature" :min="0" :max="1" :step="0.1" />
          <span class="slider-value">{{ settings.temperature }}</span>
        </div>
      </div>

      <!-- 功能开关 -->
      <div class="settings-card">
        <div class="card-title"><SettingOutlined /> 功能开关</div>
        <div class="toggle-list">
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">SSE 流式输出</span>
              <span class="toggle-desc">启用后聊天内容将流式返回</span>
            </div>
            <a-switch v-model:checked="settings.sse_enabled" />
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">自动画像更新</span>
              <span class="toggle-desc">学习后自动更新用户画像</span>
            </div>
            <a-switch v-model:checked="settings.auto_profile_update" />
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">自动路径调整</span>
              <span class="toggle-desc">根据画像自动调整学习路径</span>
            </div>
            <a-switch v-model:checked="settings.auto_path_adjustment" />
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">调试模式</span>
              <span class="toggle-desc">开启详细日志输出</span>
            </div>
            <a-switch v-model:checked="settings.debug_mode" />
          </div>
        </div>
      </div>

      <!-- 通知设置 -->
      <div class="settings-card">
        <div class="card-title"><BellOutlined /> 通知设置</div>
        <div class="toggle-list">
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">新用户注册通知</span>
              <span class="toggle-desc">有新用户注册时发送通知</span>
            </div>
            <a-switch v-model:checked="notifications.new_user" />
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">Agent 异常通知</span>
              <span class="toggle-desc">Agent 运行出错时发送通知</span>
            </div>
            <a-switch v-model:checked="notifications.agent_error" />
          </div>
          <div class="toggle-row">
            <div class="toggle-info">
              <span class="toggle-label">系统告警通知</span>
              <span class="toggle-desc">系统资源不足时发送通知</span>
            </div>
            <a-switch v-model:checked="notifications.system_alert" />
          </div>
        </div>
      </div>

      <!-- 数据大屏分享 -->
      <div class="settings-card">
        <div class="card-title"><ShareAltOutlined /> 数据大屏分享</div>
        <div class="share-section">
          <a-button type="primary" ghost @click="createShareToken">
            <LinkOutlined /> 生成分享链接
          </a-button>
          <a-input-group compact style="margin-top: 12px" v-if="shareUrl">
            <a-input :value="shareUrl" readonly style="width: calc(100% - 80px)" />
            <a-button type="primary" @click="copyShareUrl">复制</a-button>
          </a-input-group>
        </div>
        <div class="share-tokens" v-if="shareTokens.length > 0">
          <div class="tokens-header">
            <span>已有分享链接</span>
          </div>
          <div class="token-list">
            <div v-for="t in shareTokens" :key="t.id" class="token-item">
              <div class="token-info">
                <span class="token-status" :class="{ active: t.is_active }">
                  {{ t.is_active ? '有效' : '已撤销' }}
                </span>
                <span class="token-expire">
                  {{ new Date(t.expires_at) > new Date() ? '过期: ' + formatDate(t.expires_at) : '已过期' }}
                </span>
              </div>
              <a-button v-if="t.is_active" type="link" danger size="small" @click="revokeToken(t.id)">
                撤销
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  SaveOutlined, DeleteOutlined, ApiOutlined, SettingOutlined,
  BellOutlined, ShareAltOutlined, LinkOutlined
} from '@ant-design/icons-vue'
import * as adminApi from '../api/adminApi'

// 系统设置
const settings = reactive({
  api_base_url: '',
  model_name: 'deepseek-chat',
  max_tokens: 4096,
  temperature: 0.7,
  sse_enabled: true,
  auto_profile_update: true,
  auto_path_adjustment: true,
  debug_mode: false
})

// 通知设置
const notifications = reactive({
  new_user: true,
  agent_error: true,
  system_alert: true
})

// 分享链接
const shareUrl = ref('')
const shareTokens = ref<any[]>([])

// 加载设置
const loadSettings = async () => {
  try {
    const res = await adminApi.getSettings()
    if (res) {
      Object.assign(settings, res)
    }
  } catch (e) {
    console.error('加载设置失败', e)
  }
}

// 加载通知设置
const loadNotificationSettings = async () => {
  try {
    const res = await adminApi.getNotificationSettings()
    if (res && Array.isArray(res)) {
      res.forEach((n: any) => {
        if (n && n.type === 'new_user') notifications.new_user = n.enabled
        if (n && n.type === 'agent_error') notifications.agent_error = n.enabled
        if (n && n.type === 'system_alert') notifications.system_alert = n.enabled
      })
    }
  } catch (e) {
    console.error('加载通知设置失败', e)
  }
}

// 保存设置
const saveSettings = async () => {
  try {
    await adminApi.updateSettings(settings)
    // 保存通知设置
    await Promise.all([
      adminApi.updateNotificationSetting('new_user', { enabled: notifications.new_user }),
      adminApi.updateNotificationSetting('agent_error', { enabled: notifications.agent_error }),
      adminApi.updateNotificationSetting('system_alert', { enabled: notifications.system_alert })
    ])
    message.success('设置保存成功')
  } catch (e) {
    message.error('保存失败')
  }
}

// 清理缓存
const clearCache = async () => {
  try {
    await adminApi.clearCache()
    message.success('缓存清理成功')
  } catch (e) {
    message.error('清理失败')
  }
}

// 创建分享链接
const createShareToken = async () => {
  try {
    const res = await adminApi.createShareToken(24)
    if (res) {
      shareUrl.value = `${window.location.origin}/data-screen?token=${res.token}`
      message.success('分享链接已生成')
      loadShareTokens()
    }
  } catch (e) {
    message.error('生成失败')
  }
}

// 加载分享链接列表
const loadShareTokens = async () => {
  try {
    const res = await adminApi.getShareTokens()
    shareTokens.value = res || []
  } catch (e) {
    console.error('加载分享链接失败', e)
  }
}

// 撤销分享链接
const revokeToken = async (tokenId: number) => {
  try {
    await adminApi.revokeShareToken(tokenId)
    message.success('已撤销')
    loadShareTokens()
  } catch (e) {
    message.error('撤销失败')
  }
}

// 复制分享链接
const copyShareUrl = () => {
  navigator.clipboard.writeText(shareUrl.value)
  message.success('已复制到剪贴板')
}

// 日期格式化
const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSettings()
  loadNotificationSettings()
  loadShareTokens()
})
</script>

<style lang="less" scoped>
.settings-view {
  padding: 0;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.settings-card {
  padding: 20px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
}

.card-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.form-group {
  margin-bottom: 16px;

  label {
    display: block;
    color: #475569;
    font-size: 12px;
    margin-bottom: 6px;
    font-weight: 500;
  }
}

.slider-value {
  font-size: 12px;
  color: #2563eb;
  margin-left: 8px;
}

.toggle-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(37, 99, 235, 0.04);
  border-radius: 8px;
}

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-label {
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
}

.toggle-desc {
  font-size: 11px;
  color: #94a3b8;
}

.share-section {
  margin-bottom: 16px;
}

.share-tokens {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(37, 99, 235, 0.06);
}

.tokens-header {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
}

.token-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.token-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: rgba(37, 99, 235, 0.04);
  border-radius: 8px;
}

.token-info {
  display: flex;
  gap: 12px;
  align-items: center;
}

.token-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;

  &.active {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }
}

.token-expire {
  font-size: 11px;
  color: #94a3b8;
}

@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>