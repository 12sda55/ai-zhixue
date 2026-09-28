<template>
  <div class="report-template">
    <!-- 封面 -->
    <div class="report-cover">
      <div class="cover-header">
        <div class="cover-logo">AI 学习系统</div>
        <div class="cover-line"></div>
      </div>
      <div class="cover-body">
        <div class="cover-title">个人学习报告</div>
        <div class="cover-subtitle">{{ profileSection.major || '专业学习' }} · {{ profileSection.grade || '本学期' }}</div>
        <div class="cover-meta">
          <div class="meta-item">
            <span class="meta-label">报告日期</span>
            <span class="meta-value">{{ new Date().toLocaleDateString('zh-CN') }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">学习周期</span>
            <span class="meta-value">累计 {{ Math.round(profileSection.totalStudyMinutes / 60) }} 小时</span>
          </div>
        </div>
      </div>
      <div class="cover-footer">
        <div class="footer-text">AI智能学习系统 自动生成</div>
      </div>
    </div>

    <!-- 目录页 -->
    <div class="report-page toc-page">
      <div class="page-header">
        <span class="page-title">目录</span>
      </div>
      <div class="toc-list">
        <div class="toc-item"><span class="toc-num">一</span><span class="toc-title">学习概况总结</span><span class="toc-page">1</span></div>
        <div class="toc-item"><span class="toc-num">二</span><span class="toc-title">画像维度分析</span><span class="toc-page">2</span></div>
        <div class="toc-item"><span class="toc-num">三</span><span class="toc-title">学习路径进展</span><span class="toc-page">3</span></div>
        <div class="toc-item"><span class="toc-num">四</span><span class="toc-title">测评表现分析</span><span class="toc-page">4</span></div>
        <div class="toc-item"><span class="toc-num">五</span><span class="toc-title">答疑互动情况</span><span class="toc-page">5</span></div>
        <div class="toc-item"><span class="toc-num">六</span><span class="toc-title">资源利用情况</span><span class="toc-page">6</span></div>
        <div class="toc-item"><span class="toc-num">七</span><span class="toc-title">综合评价与建议</span><span class="toc-page">7</span></div>
      </div>
    </div>

    <!-- 正文内容 -->
    <div class="report-page content-page">
      <!-- 雷达图区域 -->
      <div class="radar-section">
        <div class="section-title">学习画像雷达图</div>
        <div class="radar-chart-area">
          <img v-if="radarImage" :src="radarImage" class="chart-img" />
          <div v-else class="chart-placeholder">暂无雷达图数据</div>
        </div>
      </div>

      <!-- AI生成的报告内容 -->
      <div class="report-content" v-html="renderMarkdown(suggestions)" />
    </div>

    <!-- 附录：详细数据 -->
    <div class="report-page appendix-page">
      <div class="section-title">附录：详细学习数据</div>
      
      <!-- 画像维度表格 -->
      <div class="data-section">
        <div class="data-title">A. 画像维度得分明细</div>
        <table class="data-table">
          <thead>
            <tr><th>维度</th><th>得分</th><th>等级</th><th>说明</th></tr>
          </thead>
          <tbody>
            <tr v-for="dim in profileSection.dimensions" :key="dim.key">
              <td>{{ DIMENSION_META[dim.key as ProfileAllDimensionKey]?.icon }} {{ dim.name }}</td>
              <td class="score-cell">{{ dim.value }}</td>
              <td>{{ dim.label }}</td>
              <td class="desc-cell">{{ getDimensionDesc(dim.key, dim.label) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 学习统计表格 -->
      <div class="data-section">
        <div class="data-title">B. 学习统计数据</div>
        <table class="data-table">
          <thead>
            <tr><th>指标</th><th>数值</th><th>评价</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>累计学习时长</td>
              <td class="score-cell">{{ Math.round(profileSection.totalStudyMinutes / 60 * 10) / 10 }} 小时</td>
              <td>{{ profileSection.totalStudyMinutes >= 600 ? '优秀' : profileSection.totalStudyMinutes >= 300 ? '良好' : '待提升' }}</td>
            </tr>
            <tr>
              <td>连续学习天数</td>
              <td class="score-cell">{{ profileSection.streakDays }} 天</td>
              <td>{{ profileSection.streakDays >= 7 ? '优秀' : profileSection.streakDays >= 3 ? '良好' : '需坚持' }}</td>
            </tr>
            <tr>
              <td>完成资源数</td>
              <td class="score-cell">{{ profileSection.completedResourceCount }}</td>
              <td>{{ profileSection.completedResourceCount >= 10 ? '优秀' : profileSection.completedResourceCount >= 5 ? '良好' : '待提升' }}</td>
            </tr>
            <tr>
              <td>完成阶段数</td>
              <td class="score-cell">{{ profileSection.completedStageCount }}</td>
              <td>{{ profileSection.completedStageCount >= 3 ? '优秀' : profileSection.completedStageCount >= 1 ? '良好' : '待开始' }}</td>
            </tr>
            <tr>
              <td>完成测评数</td>
              <td class="score-cell">{{ profileSection.completedAssessCount }}</td>
              <td>{{ profileSection.completedAssessCount >= 5 ? '优秀' : profileSection.completedAssessCount >= 2 ? '良好' : '待提升' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 错题本 -->
      <div v-if="assessSection.wrongAnswers.length" class="data-section">
        <div class="data-title">C. 错题记录（最近20题）</div>
        <div class="wrong-list">
          <div v-for="(wa, idx) in assessSection.wrongAnswers.slice(0, 20)" :key="wa.id" class="wrong-item">
            <div class="wrong-num">{{ idx + 1 }}</div>
            <div class="wrong-content">
              <div class="wrong-q">{{ wa.question }}</div>
              <div class="wrong-a">
                <span class="user-answer">你的答案：{{ wa.userAnswer }}</span>
                <span class="correct-answer">正确答案：{{ wa.correctAnswer }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { DIMENSION_META } from '../../../shared/types'
import type { ProfileAllDimensionKey } from '../../../shared/types'

const md = new MarkdownIt({ html: false, linkify: true })

defineProps<{
  profileSection: any
  pathSection: any
  resourceSection: any
  assessSection: any
  updateHistory: any
  suggestions: string
  radarImage: string
}>()

function renderMarkdown(text: string): string {
  return md.render(text || '报告内容生成中...')
}

function getDimensionDesc(key: string, label: string): string {
  const descMap: Record<string, Record<string, string>> = {
    base_level: {
      '入门': '刚开始接触该领域',
      '基础': '了解基本概念',
      '中等': '有一定实践经验',
      '进阶': '掌握核心技能',
      '精通': '深入理解并能创新',
    },
    weak_points: {
      '无明显薄弱': '知识点掌握均衡',
    },
    study_goal: {
      '考试通关': '以考试成绩为目标',
      '竞赛提升': '以竞赛获奖为目标',
      '项目实战': '以实际项目为目标',
      '全面掌握': '以系统学习为目标',
    },
  }
  return descMap[key]?.[label] || ''
}
</script>

<style scoped>
/* ========== 报告整体样式 ========== */
.report-template {
  font-family: 'SimSun', 'Microsoft YaHei', serif;
  color: #333;
  background: transparent;
  width: 794px; /* A4宽度 */
  line-height: 1.6;
}

/* ========== 封面样式 ========== */
.report-cover {
  padding: 60px 50px;
  text-align: center;
  border-bottom: 3px solid #2563eb;
  page-break-after: always;
}

.cover-header {
  margin-bottom: 40px;
}

.cover-logo {
  font-size: 24px;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: 4px;
}

.cover-line {
  width: 200px;
  height: 2px;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  margin: 20px auto;
}

.cover-body {
  margin-bottom: 60px;
}

.cover-title {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 16px;
  letter-spacing: 8px;
}

.cover-subtitle {
  font-size: 18px;
  color: #666;
  margin-bottom: 30px;
}

.cover-meta {
  display: flex;
  justify-content: center;
  gap: 40px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #999;
}

.meta-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.cover-footer {
  padding-top: 40px;
}

.footer-text {
  font-size: 12px;
  color: #999;
}

/* ========== 页面样式 ========== */
.report-page {
  padding: 30px 50px;
  page-break-inside: avoid;
}

.page-header {
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

/* ========== 目录页 ========== */
.toc-page {
  page-break-after: always;
}

.toc-list {
  padding: 20px 0;
}

.toc-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #e5e5e5;
}

.toc-num {
  font-size: 14px;
  font-weight: 700;
  color: #2563eb;
  width: 30px;
}

.toc-title {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.toc-page {
  font-size: 12px;
  color: #999;
}

/* ========== 内容页 ========== */
.content-page {
  page-break-after: always;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #2563eb;
  border-bottom: 2px solid #2563eb;
  padding-bottom: 6px;
  margin-bottom: 16px;
}

.radar-section {
  margin-bottom: 30px;
}

.radar-chart-area {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.chart-img {
  max-width: 280px;
}

.chart-placeholder {
  font-size: 14px;
  color: #999;
  padding: 40px;
}

/* ========== 报告内容Markdown样式 ========== */
.report-content {
  font-size: 13px;
  line-height: 1.8;
}

.report-content :deep(h2) {
  font-size: 16px;
  font-weight: 700;
  color: #2563eb;
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 6px;
  margin: 20px 0 12px;
}

.report-content :deep(h3) {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 16px 0 8px;
}

.report-content :deep(p) {
  margin: 8px 0;
  text-align: justify;
}

.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.report-content :deep(th) {
  background: #f0f4f8;
  color: #2563eb;
  font-weight: 600;
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  font-size: 12px;
}

.report-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e5e5e5;
  font-size: 12px;
}

.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.report-content :deep(li) {
  margin: 4px 0;
}

.report-content :deep(strong) {
  color: #2563eb;
}

.report-content :deep(blockquote) {
  border-left: 3px solid #2563eb;
  padding-left: 12px;
  margin: 12px 0;
  color: #666;
  background: #f8f9fa;
}

/* ========== 附录页 ========== */
.appendix-page {
  page-break-after: always;
}

.data-section {
  margin-bottom: 20px;
}

.data-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: #f0f4f8;
  color: #2563eb;
  font-weight: 600;
  padding: 8px 10px;
  border: 1px solid #e5e5e5;
  font-size: 11px;
}

.data-table td {
  padding: 8px 10px;
  border: 1px solid #e5e5e5;
  font-size: 11px;
}

.score-cell {
  font-weight: 600;
  color: #2563eb;
  text-align: center;
}

.desc-cell {
  color: #666;
  font-size: 10px;
}

/* ========== 错题列表 ========== */
.wrong-list {
  border: 1px solid #e5e5e5;
  border-radius: 4px;
}

.wrong-item {
  display: flex;
  padding: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.wrong-item:last-child {
  border-bottom: none;
}

.wrong-num {
  width: 24px;
  height: 24px;
  background: #fee;
  color: #c00;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.wrong-content {
  flex: 1;
  padding-left: 10px;
}

.wrong-q {
  font-size: 12px;
  color: #333;
  margin-bottom: 4px;
}

.wrong-a {
  font-size: 11px;
}

.user-answer {
  color: #c00;
  margin-right: 12px;
}

.correct-answer {
  color: #28a745;
}
</style>