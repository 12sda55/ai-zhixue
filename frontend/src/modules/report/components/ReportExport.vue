<template>
  <div v-if="visible" class="report-overlay" @click.self="close">
    <div class="report-panel">
      <div class="report-header">
        <h3>📄 导出学习报告</h3>
        <button class="close-btn" @click="close">✕</button>
      </div>

      <!-- 生成进度 -->
      <div v-if="isGenerating" class="progress-area">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div class="progress-text">{{ progressText }}</div>
      </div>

      <!-- 操作按钮 -->
      <div v-else class="action-area">
        <button v-if="!pdfBlob" class="gen-btn" @click="startGeneration">
          🚀 生成报告
        </button>
        <template v-else>
          <button class="download-btn" @click="downloadPdf">
            📥 下载 PDF
          </button>
          <button class="preview-btn" @click="showPreview = !showPreview">
            {{ showPreview ? '隐藏预览' : '👁 预览' }}
          </button>
          <button class="regen-btn" @click="resetAndRegenerate">
            🔄 重新生成
          </button>
        </template>
      </div>

      <!-- 预览区 -->
      <div v-if="showPreview && pdfBlob" class="preview-area">
        <iframe :src="previewUrl" class="preview-iframe" />
      </div>

      <!-- 隐藏的报告模板（使用绝对定位移到屏幕外，确保 html2canvas 能渲染） -->
      <div class="report-template-container" ref="reportTemplateRef">
        <ReportTemplate
          :profileSection="profileSection"
          :pathSection="pathSection"
          :resourceSection="resourceSection"
          :assessSection="assessSection"
          :updateHistory="updateHistory"
          :suggestions="suggestions"
          :radarImage="radarImage"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ReportTemplate from './ReportTemplate.vue'
import { useReportData } from '../composables/useReportData'
import { useAiSuggestions } from '../composables/useAiSuggestions'
import { exportRadarChart } from '../utils/chartExport'
import { generatePdf } from '../utils/generatePdf'
import { useProfileStore } from '../../profile/stores/profileStore'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const profileStore = useProfileStore()
const { profileSection, pathSection, resourceSection, assessSection, updateHistory } = useReportData()
const { suggestions, isGenerating: _isAiGenerating, generateSuggestions } = useAiSuggestions()

const reportTemplateRef = ref<HTMLElement | null>(null)
const isGenerating = ref(false)
const progress = ref(0)
const pdfBlob = ref<Blob | null>(null)
const showPreview = ref(false)
const radarImage = ref('')

const progressText = computed(() => {
  if (progress.value < 30) return '正在生成 AI 学习建议...'
  if (progress.value < 60) return '正在渲染图表...'
  if (progress.value < 90) return '正在组装 PDF...'
  return '即将完成！'
})

const previewUrl = computed(() => {
  if (!pdfBlob.value) return ''
  return URL.createObjectURL(pdfBlob.value)
})

function close() {
  emit('close')
}

function resetAndRegenerate() {
  pdfBlob.value = null
  showPreview.value = false
  startGeneration()
}

async function startGeneration() {
  if (!reportTemplateRef.value) return
  isGenerating.value = true
  progress.value = 5

  try {
    // Step 1: 生成 AI 建议
    progress.value = 10
    await generateSuggestions(profileStore.profileData)
    progress.value = 30

    // Step 2: 导出雷达图
    radarImage.value = exportRadarChart(profileStore.profileData)
    progress.value = 40

    // Step 3: 生成 PDF
    const blob = await generatePdf(reportTemplateRef.value, (pct: number) => {
      progress.value = 40 + Math.round(pct * 0.55)
    })
    pdfBlob.value = blob
    progress.value = 100
  } catch (err) {
    console.error('[Report] 生成报告失败', err)
  } finally {
    isGenerating.value = false
  }
}

function downloadPdf() {
  if (!pdfBlob.value) return
  const url = URL.createObjectURL(pdfBlob.value)
  const a = document.createElement('a')
  a.href = url
  a.download = `学习报告_${profileStore.profileData.major}_${new Date().toLocaleDateString('zh-CN')}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style lang="less" scoped>
.report-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.report-panel {
  width: 600px; max-height: 80vh;
  background: #FFFFFF; border-radius: 16px;
  overflow: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.report-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #F3F2F7;
}
.close-btn {
  background: none; border: none; font-size: 16px;
  color: #6E6B7B; cursor: pointer; padding: 4px 8px;
  &:hover { color: #2F2B3D; }
}
.progress-area { padding: 40px 24px; text-align: center; }
.progress-bar {
  height: 8px; background: #F3F2F7; border-radius: 4px; overflow: hidden;
  margin-bottom: 16px;
}
.progress-fill {
  height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, #7367F0, #00CFE8);
  transition: width 0.3s ease;
}
.progress-text { font-size: 13px; color: #6E6B7B; }
.action-area { padding: 24px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.gen-btn, .download-btn, .preview-btn, .regen-btn {
  padding: 10px 24px; border-radius: 8px; border: none;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.gen-btn {
  background: linear-gradient(135deg, #7367F0, #00CFE8);
  color: #fff;
  &:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(115,103,240,0.4); }
}
.download-btn {
  background: linear-gradient(135deg, #28C76F, #6FD194);
  color: #fff;
  &:hover { transform: translateY(-1px); }
}
.preview-btn {
  background: rgba(0,207,232,0.1); color: #00CFE8;
  border: 1px solid rgba(0,207,232,0.3);
  &:hover { background: rgba(0,207,232,0.2); }
}
.regen-btn {
  background: rgba(115,103,240,0.1); color: #7367F0;
  border: 1px solid rgba(115,103,240,0.3);
  &:hover { background: rgba(115,103,240,0.2); }
}
.preview-area { padding: 0 24px 24px; }
.preview-iframe { width: 100%; height: 500px; border: 1px solid #EBE9F1; border-radius: 8px; }

/* 报告模板容器：移到屏幕外，确保 html2canvas 能渲染 */
.report-template-container {
  position: fixed;
  left: -9999px;
  top: 0;
  width: 794px;
  background: transparent;
  z-index: -1;
  pointer-events: none;
}
</style>
