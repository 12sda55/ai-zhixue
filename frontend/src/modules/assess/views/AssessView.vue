<template>
  <div class="assess-view">
    <!-- 阶段0：模式选择 -->
    <div v-if="!mode" class="mode-selection">
      <div class="header-icon">📊</div>
      <div class="selection-title">选择测评模式</div>
      <div class="selection-desc">多维度检测学习效果 · AI智能出题 · 精准定位薄弱点</div>
      <div class="mode-cards">
        <div
          class="mode-card"
          :class="{ hovered: hoveredMode === 'practice' }"
          @click="selectMode('practice')"
          @mouseenter="hoveredMode = 'practice'"
          @mouseleave="hoveredMode = null"
        >
          <div class="card-icon">📝</div>
          <h3>练习模式</h3>
          <p>做完所有题后统一显示解析</p>
          <p class="card-hint">适合：自我检测</p>
        </div>
        <div
          class="mode-card"
          :class="{ hovered: hoveredMode === 'instant-feedback' }"
          @click="selectMode('instant-feedback')"
          @mouseenter="hoveredMode = 'instant-feedback'"
          @mouseleave="hoveredMode = null"
        >
          <div class="card-icon">⚡</div>
          <h3>即时反馈模式</h3>
          <p>每做一题立即显示对错+解析</p>
          <p class="card-hint">适合：边学边练</p>
        </div>
      </div>
      <div class="mode-info">
        {{ questionCount }} 道题 · 预计 {{ estimatedTime }} 分钟 · 覆盖 {{ knowledgePointCount }} 个知识点
      </div>
    </div>

    <!-- 阶段1：生成题目 -->
    <div v-else-if="isGenerating" class="generating-area">
      <a-spin size="large" />
      <p class="generating-text">正在生成个性化题目...</p>
    </div>

    <!-- 阶段2：做题 -->
    <div v-else-if="isTesting && currentQuestion" class="testing-area">
      <!-- 进度条 -->
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        <span class="progress-text">{{ currentIdx + 1 }} / {{ questions.length }}</span>
      </div>

      <!-- 题目卡片 -->
      <div class="question-card">
        <div class="question-header">
          <span class="difficulty-tag" :class="difficultyClass">{{ difficultyLabel }}</span>
          <span class="timer" :class="{ warning: elapsedSeconds > 45 }">⏱️ {{ elapsedSeconds }}s</span>
        </div>

        <div class="q-text">{{ currentQuestion.question }}</div>

        <!-- 选择题 -->
        <div v-if="currentQuestion.type === 'choice' && currentQuestion.options?.length" class="q-options">
          <div
            v-for="(opt, idx) in currentQuestion.options"
            :key="idx"
            class="q-option"
            :class="{
              selected: selectedAnswer === optionLetters[idx],
              correct: showResult && optionLetters[idx] === currentQuestion.answer,
              wrong: showResult && selectedAnswer === optionLetters[idx] && !currentIsCorrect
            }"
            @click="!showResult && (selectedAnswer = optionLetters[idx])"
          >
            <span class="opt-letter">{{ optionLetters[idx] }}</span>
            <span>{{ opt }}</span>
          </div>
        </div>

        <!-- 填空题 -->
        <div v-else-if="currentQuestion.type === 'fill'" class="fill-area">
          <a-input
            v-model:value="fillAnswer"
            placeholder="请输入答案"
            size="large"
            :disabled="showResult"
            @pressEnter="handleSubmit"
          />
          <div v-if="showResult" class="fill-result">
            <p v-if="currentIsCorrect" class="fill-correct">✓ 正确！答案：{{ currentQuestion.answer }}</p>
            <p v-else class="fill-wrong">✗ 错误。正确答案：{{ currentQuestion.answer }}</p>
          </div>
        </div>

        <!-- 解析（即时反馈模式） -->
        <div v-if="showResult && mode === 'instant-feedback'" class="q-explain">
          <div class="explain-badge">{{ currentIsCorrect ? '✅ 回答正确' : '❌ 回答错误' }}</div>
          <div class="explain-text">{{ currentQuestion.explanation }}</div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-bar">
          <a-button v-if="!showResult" class="submit-btn" :disabled="!canSubmit" @click="handleSubmit">提交答案</a-button>
          <a-button v-else class="next-btn" @click="handleNext">{{ isLastQuestion ? '查看结果' : '下一题' }}</a-button>
        </div>
      </div>

      <!-- 答疑弹窗 -->
      <transition name="fade-scale">
        <div v-if="showQA" class="qa-modal-overlay" @click.self="store.closeQA()">
          <div class="qa-modal">
            <div class="qa-header">
              <div class="qa-header-left">
                <span class="qa-avatar">🤖</span>
                <div class="qa-header-info">
                  <span class="qa-title">智能答疑助手</span>
                  <span class="qa-subtitle">随时为你解答疑惑</span>
                </div>
              </div>
              <a-button type="text" size="small" class="qa-close-btn" @click="store.closeQA()">✕</a-button>
            </div>
            <div class="qa-body">
              <!-- 左侧侧边栏：提示内容 -->
              <div class="qa-sidebar">
                <div class="sidebar-section">
                  <div class="sidebar-header">
                    <span class="sidebar-icon">💡</span>
                    <span class="sidebar-title">学习提示</span>
                    <span class="sidebar-badge">已思考 {{ elapsedSeconds }} 秒</span>
                  </div>
                </div>
                <div class="sidebar-section">
                  <div class="sidebar-info">
                    <span class="info-icon">📝</span>
                    <span class="info-text">这是一道 <strong>{{ currentQuestion?.difficulty === 'beginner' ? '基础题' : currentQuestion?.difficulty === 'intermediate' ? '中等题' : '进阶题' }}</strong></span>
                  </div>
                </div>
                <div class="sidebar-section">
                  <div class="sidebar-knowledge">
                    <span class="knowledge-icon">📚</span>
                    <span class="knowledge-label">考查知识点</span>
                    <span class="knowledge-points">{{ currentQuestion?.knowledgePoints?.join(' · ') || '相关知识点' }}</span>
                  </div>
                </div>
                <div class="sidebar-section">
                  <div class="sidebar-help-header">
                    <span class="help-icon">🤝</span>
                    <span class="help-title">我可以这样帮你</span>
                  </div>
                  <div class="sidebar-help-options">
                    <div class="help-option" @click="sendQuickQuestion('概念讲解')">
                      <span class="option-icon">📖</span>
                      <span class="option-text">讲解相关概念</span>
                    </div>
                    <div class="help-option" @click="sendQuickQuestion('思路分析')">
                      <span class="option-icon">🔍</span>
                      <span class="option-text">分析解题思路</span>
                    </div>
                    <div class="help-option" @click="sendQuickQuestion('具体问题')">
                      <span class="option-icon">💬</span>
                      <span class="option-text">回答具体问题</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- 中央区域：AI回答 -->
              <div class="qa-main">
                <div class="qa-messages">
                  <div v-for="(msg, idx) in qaMessages" :key="idx" :class="['qa-msg', msg.role]">
                    <div v-if="msg.role === 'user'" class="msg-user">
                      <span class="msg-text">{{ msg.content }}</span>
                    </div>
                    <div v-else class="msg-ai">
                      <MarkdownRenderer :content="msg.content" class="qa-markdown" />
                    </div>
                  </div>
                  <div v-if="qaMessages.length === 0" class="qa-empty">
                    <span class="empty-text">需要我帮你讲解吗？直接输入你的问题即可！</span>
                  </div>
                </div>
                <div class="qa-input">
                  <a-input v-model:value="qaInput" placeholder="输入你的问题..." @pressEnter="sendQA">
                    <template #prefix>
                      <span class="input-icon">✏️</span>
                    </template>
                  </a-input>
                  <a-button type="primary" class="send-btn" @click="sendQA">
                    <span class="send-icon">📨</span>
                    发送
                  </a-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 阶段3：结果 -->
    <div v-else-if="hasReport && report" class="report-area">
      <div class="report-summary">
        <div class="score-ring">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(37, 99, 235, 0.1)" stroke-width="8" />
            <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" stroke-width="8"
              stroke-linecap="round" :stroke-dasharray="scoreDash" transform="rotate(-90 60 60)" />
            <defs><linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#2563eb" />
              <stop offset="100%" stop-color="#06b6d4" />
            </linearGradient></defs>
          </svg>
          <div class="score-text">
            <span class="score-num">{{ report.overallScore }}</span>
            <span class="score-label">综合评分</span>
          </div>
        </div>
        <div class="summary-stats">
          <div class="stat"><span class="stat-val correct">{{ report.correctCount }}/{{ report.totalCount }}</span><span class="stat-lbl">正确题数</span></div>
          <div class="stat"><span class="stat-val time">{{ formatTime(report.timeUsed) }}</span><span class="stat-lbl">用时</span></div>
          <div class="stat"><span class="stat-val wrong">{{ Math.round(report.errorRate * 100) }}%</span><span class="stat-lbl">错误率</span></div>
        </div>
      </div>

      <!-- 降级提示 -->
      <div v-if="report.errorRate >= 0.5" class="downgrade-notice">
        ⚠️ 当前知识难度偏高<br />
        已为你自动生成基础巩固资源，建议先巩固基础再挑战进阶
        <a-button type="link" size="small" @click="goToResources">查看推荐资源 →</a-button>
      </div>

      <AssessChart :modules="report.modules" />
      <AssessReport :modules="report.modules" :weakPoints="weakModules" />

      <!-- 题目回顾 -->
      <div class="review-section">
        <h4 class="review-title">题目回顾</h4>
        <div v-for="(q, idx) in questions" :key="q.id" class="review-item" :class="{ correct: answers[idx]?.isCorrect, wrong: !answers[idx]?.isCorrect }">
          <div class="review-header">
            <span class="review-num">{{ idx + 1 }}</span>
            <span class="review-icon">{{ answers[idx]?.isCorrect ? '✓' : '✗' }}</span>
          </div>
          <div class="review-question">{{ q.question }}</div>
          <div class="review-answer">
            你的答案：{{ answers[idx]?.userAnswer || '未作答' }}
            <span v-if="!answers[idx]?.isCorrect"> | 正确答案：{{ q.answer }}</span>
          </div>
          <div class="review-explain">{{ q.explanation }}</div>
        </div>
      </div>

      <div class="action-bar">
        <a-button @click="handleReset">重新测评</a-button>
        <a-button type="primary" @click="goToLearn">继续学习</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import AssessChart from '../components/AssessChart.vue'
import AssessReport from '../components/AssessReport.vue'
import MarkdownRenderer from '../../../shared/components/MarkdownRenderer.vue'
import { useAssessStore } from '../stores/assessStore'
import { storeToRefs } from 'pinia'

const router = useRouter()
const store = useAssessStore()
const {
  mode, questions, currentIdx, isGenerating, isTesting, hasReport, report,
  currentQuestion, progress, isLastQuestion, elapsedSeconds, showQA, qaMessages,
  answers,
} = storeToRefs(store)

// UI 状态
const hoveredMode = ref<string | null>(null)
const selectedAnswer = ref<string | null>(null)
const fillAnswer = ref('')
const showResult = ref(false)
const qaInput = ref('')
const optionLetters = ['A', 'B', 'C', 'D']

// 计时器
let timer: ReturnType<typeof setInterval> | null = null

// 计算属性
// 将 weakPoints (string[]) 转为 AssessModule 格式（兼容 AssessReport）
const weakModules = computed(() => {
  if (!report.value) return []
  return report.value.modules.filter(m => m.score < 70)
})

const questionCount = computed(() => 12)
const estimatedTime = computed(() => Math.round(questionCount.value * 1.5))
const knowledgePointCount = computed(() => {
  const kpSet = new Set<string>()
  questions.value.forEach(q => q.knowledgePoints?.forEach(kp => kpSet.add(kp)))
  return kpSet.size || 8
})

const difficultyClass = computed(() => {
  const d = currentQuestion.value?.difficulty
  return d === 'beginner' ? 'diff-beginner' : d === 'intermediate' ? 'diff-intermediate' : 'diff-advanced'
})

const difficultyLabel = computed(() => {
  const d = currentQuestion.value?.difficulty
  return d === 'beginner' ? '基础' : d === 'intermediate' ? '中等' : '进阶'
})

const canSubmit = computed(() => {
  if (currentQuestion.value?.type === 'choice') {
    return selectedAnswer.value !== null
  } else {
    return fillAnswer.value.trim().length > 0
  }
})

const currentIsCorrect = computed(() => {
  const ans = store.answers.find(a => a.questionId === currentQuestion.value?.id)
  return ans?.isCorrect ?? false
})

const scoreDash = computed(() => {
  if (!report.value) return '0 327'
  const pct = report.value.overallScore / 100
  return `${pct * 327} 327`
})

// 方法
function selectMode(m: 'practice' | 'instant-feedback') {
  store.selectMode(m)
  store.startAssess()
}

function handleSubmit() {
  const answer = currentQuestion.value?.type === 'choice'
    ? selectedAnswer.value!
    : fillAnswer.value

  store.submitAnswer(answer)
  showResult.value = true

  // 练习模式：自动进入下一题（非最后一题）
  if (mode.value === 'practice' && !isLastQuestion.value) {
    setTimeout(() => {
      handleNext()
    }, 500)
  }
}

function handleNext() {
  showResult.value = false
  selectedAnswer.value = null
  fillAnswer.value = ''
  store.nextQuestion()
}

function sendQA() {
  if (!qaInput.value.trim()) return
  store.sendQAMessage(qaInput.value)
  qaInput.value = ''
}

function sendQuickQuestion(type: string) {
  const question = currentQuestion.value
  const knowledgePoints = question?.knowledgePoints?.join('、') || '相关知识点'
  
  let quickMessage = ''
  if (type === '概念讲解') {
    quickMessage = `请帮我讲解这道题涉及的 ${knowledgePoints} 的概念和原理。`
  } else if (type === '思路分析') {
    quickMessage = `请帮我分析这道题的解题思路和方法。`
  } else if (type === '具体问题') {
    quickMessage = `我有一个具体问题想问：`
  }
  
  store.sendQAMessage(quickMessage)
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

function goToResources() {
  router.push('/resource')
}

function goToLearn() {
  router.push('/path')
}

function handleReset() {
  store.reset()
  showResult.value = false
  selectedAnswer.value = null
  fillAnswer.value = ''
}

// 计时器：每秒更新 elapsedSeconds
watch(isTesting, (testing) => {
  if (testing) {
    timer = setInterval(() => {
      elapsedSeconds.value = Math.floor((Date.now() - store.questionStartTime) / 1000)
      // 60秒答疑触发
      if (elapsedSeconds.value >= 60 && !store.questionTimeoutTriggered) {
        store.triggerQA()
      }
    }, 1000)
  } else if (timer) {
    clearInterval(timer)
    timer = null
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style lang="less" scoped>
.assess-view {
  padding: 16px;
  height: 100%;
  overflow: auto;
  background: transparent;
}

/* ===== 模式选择 ===== */
.mode-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}

.header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
  font-size: 20px;
  margin-bottom: 16px;
}

.selection-title {
  color: #1e293b;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
}

.selection-desc {
  color: #475569;
  font-size: 13px;
  margin-bottom: 32px;
}

.mode-cards {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.mode-card {
  width: 240px;
  padding: 28px 20px;
  border-radius: 12px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);

  &:hover, &.hovered {
    border-color: rgba(37, 99, 235, 0.3);
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.15);
  }
}

.card-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.mode-card h3 {
  color: #1e293b;
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 8px;
}

.mode-card p {
  color: #475569;
  font-size: 13px;
}

.card-hint {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 8px;
}

.mode-info {
  color: #94a3b8;
  font-size: 12px;
}

/* ===== 生成题目 ===== */
.generating-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.generating-text {
  color: #475569;
  font-size: 14px;
  margin-top: 16px;
}

/* ===== 做题 ===== */
.testing-area {
  position: relative;
}

.progress-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.progress-bar > div:first-child {
  flex: 1;
  height: 4px;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 2px;
  position: relative;
}

.progress-fill {
  height: 4px;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border-radius: 2px;
  transition: width 0.4s ease;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
  position: absolute;
  left: 0;
  top: 0;
}

.progress-text {
  font-size: 13px;
  color: #475569;
  white-space: nowrap;
}

.question-card {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.difficulty-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;

  &.diff-beginner { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
  &.diff-intermediate { background: rgba(6, 182, 212, 0.1); color: #06b6d4; }
  &.diff-advanced { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
}

.timer {
  font-size: 13px;
  color: #475569;

  &.warning { color: #f59e0b; }
}

.q-text {
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  margin-bottom: 16px;
}

.q-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.q-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { background: rgba(37, 99, 235, 0.05); border-color: rgba(37, 99, 235, 0.2); }
  &.selected { background: rgba(37, 99, 235, 0.1); border-color: rgba(37, 99, 235, 0.3); color: #1e293b; }
  &.correct { background: rgba(34, 197, 94, 0.1); border-color: rgba(34, 197, 94, 0.3); color: #22c55e; }
  &.wrong { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }
}

.opt-letter {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 11px;
  flex-shrink: 0;
}

.fill-area {
  margin-bottom: 16px;
}

.fill-result {
  margin-top: 12px;
}

.fill-correct { color: #22c55e; font-size: 13px; font-weight: 600; }
.fill-wrong { color: #ef4444; font-size: 13px; font-weight: 600; }

.q-explain {
  margin-top: 14px;
  padding: 12px;
  border-radius: 10px;
  background: transparent;
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.explain-badge { font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.explain-text { color: #475569; font-size: 13px; line-height: 1.6; }

.action-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 14px;
}

.submit-btn {
  background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(76,78,100,.06) !important;
  border-radius: 10px !important;
  font-size: 13px !important;
  height: 36px !important;
}

.next-btn {
  background: linear-gradient(135deg, #06b6d4, #0891b2) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(76,78,100,.06) !important;
  color: #fff !important;
  border-radius: 10px !important;
  font-size: 13px !important;
  height: 36px !important;
}

/* ===== 答疑弹窗 ===== */
.qa-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.qa-modal {
  width: 720px;
  max-width: 92vw;
  max-height: 85vh;
  background: #FFFFFF;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-pop 0.3s ease;
}

@keyframes modal-pop {
  0% {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.3s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
}

.fade-scale-enter-from .qa-modal,
.fade-scale-leave-to .qa-modal {
  transform: scale(0.9) translateY(20px);
}

.qa-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border-radius: 20px 20px 0 0;
}

.qa-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.qa-avatar {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.qa-header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qa-title {
  color: #FFFFFF;
  font-size: 17px;
  font-weight: 700;
}

.qa-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
}

.qa-close-btn {
  color: #FFFFFF !important;
  font-size: 18px;
  opacity: 0.85;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.15) !important;
  
  &:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.25) !important;
  }
}

.qa-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧侧边栏 */
.qa-sidebar {
  width: 200px;
  background: transparent;
  border-right: 1px solid rgba(37, 99, 235, 0.1);
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(37, 99, 235, 0.2);
}

.sidebar-icon {
  font-size: 20px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.sidebar-badge {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  font-weight: 600;
}

.sidebar-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.sidebar-info .info-icon {
  font-size: 16px;
}

.sidebar-info .info-text {
  font-size: 13px;
  color: #1e293b;
  
  strong {
    color: #2563eb;
    font-weight: 700;
  }
}

.sidebar-knowledge {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(37, 99, 235, 0.08);
  border-radius: 10px;
}

.sidebar-knowledge .knowledge-icon {
  font-size: 16px;
}

.sidebar-knowledge .knowledge-label {
  font-size: 12px;
  color: #2563eb;
  font-weight: 700;
}

.sidebar-knowledge .knowledge-points {
  font-size: 13px;
  color: #1e293b;
  font-weight: 600;
  line-height: 1.5;
}

.sidebar-help-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 10px;
  margin-top: 6px;
  border-top: 1px dashed rgba(37, 99, 235, 0.2);
}

.sidebar-help-header .help-icon {
  font-size: 18px;
}

.sidebar-help-header .help-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.sidebar-help-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
}

.sidebar-help-options .help-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(6, 182, 212, 0.08));
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(6, 182, 212, 0.15));
    border-color: #2563eb;
    transform: translateX(4px);
  }
}

.sidebar-help-options .option-icon {
  font-size: 16px;
}

.sidebar-help-options .option-text {
  font-size: 12px;
  color: #1e293b;
  font-weight: 600;
}

/* 中央区域 */
.qa-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.qa-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  background: transparent;
}

.qa-msg {
  margin-bottom: 14px;
}

.msg-user {
  display: flex;
  justify-content: flex-end;
}

.msg-user .msg-text {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  padding: 10px 16px;
  border-radius: 14px 14px 4px 14px;
  font-size: 14px;
  max-width: 80%;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
}

.msg-ai {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 14px;
  padding: 14px 18px;
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.qa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.empty-text {
  font-size: 15px;
  color: #475569;
  font-weight: 500;
  text-align: center;
}

.qa-input {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
}

.input-icon {
  font-size: 14px;
  color: #2563eb;
}

.send-btn {
  background: linear-gradient(135deg, #2563eb, #06b6d4) !important;
  border: none !important;
  border-radius: 10px !important;
  font-size: 13px !important;
  height: 36px !important;
  padding: 0 16px !important;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(76,78,100,.06) !important;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
  }
}

.send-icon {
  font-size: 14px;
}

.qa-markdown {
  :deep(.markdown-renderer) {
    color: #1e293b;
    font-size: 15px;
    line-height: 2;
    font-weight: 500;
    
    h1, h2, h3, h4 {
      color: #1e293b;
      margin: 12px 0 8px;
      font-weight: 700;
    }
    
    h1 { font-size: 18px; }
    h2 { font-size: 16px; }
    h3 { font-size: 15px; }
    
    p {
      margin: 8px 0;
      color: #1e293b;
      font-size: 15px;
      line-height: 2;
    }
    
    strong {
      color: #1e293b;
      font-weight: 700;
      font-size: 15px;
      background: rgba(37, 99, 235, 0.15);
      padding: 2px 6px;
      border-radius: 4px;
    }
    
    em {
      color: #1e293b;
      font-style: italic;
      font-weight: 600;
      background: rgba(6, 182, 212, 0.12);
      padding: 2px 6px;
      border-radius: 4px;
    }
    
    code {
      background: rgba(37, 99, 235, 0.1);
      color: #1e293b;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      border: 1px solid rgba(37, 99, 235, 0.1);
    }
    
    pre {
      background: transparent;
      border: 1px solid rgba(37, 99, 235, 0.1);
      border-radius: 10px;
      padding: 14px 16px;
      margin: 10px 0;
      
      code {
        background: none;
        color: #1e293b;
        font-weight: 500;
        border: none;
        padding: 0;
      }
    }
    
    ul, ol {
      padding-left: 24px;
      margin: 10px 0;
    }
    
    li {
      color: #1e293b;
      margin: 6px 0;
      font-size: 15px;
      line-height: 2;
      font-weight: 500;
      
      &::marker {
        color: #1e293b;
        font-weight: 700;
      }
    }
    
    blockquote {
      border-left: 4px solid #2563eb;
      background: transparent;
      padding: 10px 16px;
      margin: 10px 0;
      border-radius: 0 10px 10px 0;
      color: #1e293b;
      font-size: 15px;
      line-height: 2;
    }
    
    a {
      color: #2563eb;
      font-weight: 600;
      text-decoration: underline;
    }
    
    table {
      border-collapse: collapse;
      margin: 10px 0;
      font-size: 14px;
      
      th, td {
        border: 1px solid rgba(37, 99, 235, 0.1);
        padding: 10px 14px;
        color: #1e293b;
      }
      
      th {
        background: rgba(37, 99, 235, 0.1);
        color: #1e293b;
        font-weight: 700;
      }
      
      td {
        font-weight: 500;
      }
    }
    
    hr {
      border: none;
      border-top: 2px dashed rgba(37, 99, 235, 0.2);
      margin: 12px 0;
    }
  }
}

.qa-input {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
}

.input-icon {
  font-size: 16px;
  color: #2563eb;
}

.send-btn {
  background: linear-gradient(135deg, #2563eb, #06b6d4) !important;
  border: none !important;
  border-radius: 12px !important;
  font-size: 14px !important;
  height: 40px !important;
  padding: 0 20px !important;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(76,78,100,.06) !important;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
  }
}

.send-icon {
  font-size: 16px;
}

/* ===== 结果页 ===== */
.report-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-summary {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
}

.score-ring {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.score-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-num {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.score-label { color: #94a3b8; font-size: 12px; }

.summary-stats {
  display: flex;
  gap: 24px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-val {
  font-size: 18px;
  font-weight: 700;
  &.correct { color: #22c55e; }
  &.wrong { color: #ef4444; }
  &.time { color: #2563eb; }
}

.stat-lbl { color: #94a3b8; font-size: 12px; }

.downgrade-notice {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 10px;
  padding: 14px;
  color: #1e293b;
  font-size: 13px;
  line-height: 1.6;
}

.review-section {
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(76,78,100,.06);
}

.review-title {
  color: #1e293b;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 12px;
}

.review-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  border-left: 4px solid rgba(37, 99, 235, 0.1);

  &.correct {
    border-left-color: #22c55e;
    background: rgba(34, 197, 94, 0.05);
  }
  &.wrong {
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.05);
  }
}

.review-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.review-num {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-weight: 600;
}

.review-icon {
  font-weight: 700;
  font-size: 14px;
}

.review-question {
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.review-answer {
  color: #475569;
  font-size: 12px;
}

.review-explain {
  color: #475569;
  font-size: 12px;
  margin-top: 6px;
  line-height: 1.5;
}

/* ===== 动画 ===== */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}

@media (max-width: 768px) {
  .mode-cards {
    flex-direction: column;
  }
  .mode-card {
    width: 100%;
  }
  .stats {
    flex-direction: column;
    gap: 16px;
  }
}
</style>