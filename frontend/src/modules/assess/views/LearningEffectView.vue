<template>
  <div class="learning-effect-view">
    <a-card title="学习效果评估" :bordered="false">
      <template #extra>
        <div class="header-actions">
          <a-button type="primary" @click="refreshReport" :loading="isGenerating">
            <template #icon><ReloadOutlined /></template>
            刷新评估
          </a-button>
        </div>
      </template>

      <!-- 加载状态 -->
      <div v-if="isGenerating" class="loading-container">
        <a-spin size="large" tip="正在生成评估报告..." />
      </div>

      <!-- 评估报告 -->
      <div v-else-if="report" class="report-container">
        <!-- 整体掌握度 -->
        <a-row :gutter="16" class="stats-row">
          <a-col :span="6">
            <a-statistic title="整体掌握度" :value="report.overall_mastery" suffix="%" :value-style="{ color: getScoreColor(report.overall_mastery) }">
              <template #prefix>
                <CheckCircleOutlined v-if="report.overall_mastery >= 70" style="color: #52c41a" />
                <WarningOutlined v-else style="color: #faad14" />
              </template>
            </a-statistic>
          </a-col>
          <a-col :span="6">
            <a-statistic title="学习效率" :value="report.learning_efficiency.toFixed(1)" suffix="分/小时" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="总学习时长" :value="report.total_learning_duration.toFixed(1)" suffix="小时" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="连续学习天数" :value="report.statistics?.streak_days || 0" suffix="天" />
          </a-col>
        </a-row>

        <!-- 学习模块评估 -->
        <a-divider>各类型学习效果</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card title="学习模块得分" size="small">
              <div class="module-list">
                <div v-for="module in report.modules" :key="module.name" class="module-item">
                  <div class="module-header">
                    <span class="module-name">{{ module.name }}</span>
                    <a-tag :color="module.color">{{ module.score }}%</a-tag>
                  </div>
                  <a-progress :percent="module.score" :stroke-color="module.color" size="small" />
                  <div class="module-stats">
                    <span>学习 {{ module.count }} 次</span>
                    <span>{{ module.study_time_hours.toFixed(1) }} 小时</span>
                  </div>
                </div>
              </div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="学习统计" size="small">
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="总学习资源">{{ report.statistics?.total_resources || 0 }}</a-descriptions-item>
                <a-descriptions-item label="已完成资源">{{ report.statistics?.completed_resources || 0 }}</a-descriptions-item>
                <a-descriptions-item label="完成率">{{ (report.statistics?.completion_rate || 0).toFixed(1) }}%</a-descriptions-item>
                <a-descriptions-item label="答题正确率">{{ (report.statistics?.quiz_accuracy || 0).toFixed(1) }}%</a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>
        </a-row>

        <!-- 薄弱点识别 -->
        <a-divider>薄弱点识别</a-divider>
        <a-alert v-if="report.weak_points?.length > 0" type="warning" show-icon>
          <template #message>
            <div>发现 {{ report.weak_points.length }} 个薄弱点</div>
          </template>
          <template #description>
            <ul class="weak-points-list">
              <li v-for="wp in report.weak_points" :key="wp.type">
                <strong>{{ wp.type }}</strong>: {{ wp.reason }}
              </li>
            </ul>
          </template>
        </a-alert>
        <a-alert v-else type="success" message="暂无明显薄弱点" show-icon />

        <!-- 学习计划调整建议 -->
        <a-divider>学习计划调整建议</a-divider>
        <a-card v-if="report.adjustment_recommendations?.length > 0" size="small">
          <a-list :data-source="report.adjustment_recommendations" item-layout="horizontal">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #avatar>
                    <a-avatar :style="{ backgroundColor: item.priority === 'high' ? '#ff4d4f' : item.priority === 'medium' ? '#faad14' : '#52c41a' }">
                      <template #icon>
                        <WarningOutlined v-if="item.priority === 'high'" />
                        <InfoCircleOutlined v-else />
                      </template>
                    </a-avatar>
                  </template>
                  <template #title>
                    <a-tag :color="item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'green'">
                      {{ item.type }}
                    </a-tag>
                  </template>
                  <template #description>{{ item.content }}</template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
        <a-alert v-else type="info" message="暂无调整建议" show-icon />

        <!-- 优缺点总结 -->
        <a-divider>学习情况总结</a-divider>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-card title="优势" size="small" :headStyle="{ background: '#f6ffed' }">
              <ul class="summary-list strengths">
                <li v-for="s in report.strengths" :key="s">
                  <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
                  {{ s }}
                </li>
              </ul>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="待改进" size="small" :headStyle="{ background: '#fff7e6' }">
              <ul class="summary-list weaknesses">
                <li v-for="w in report.weaknesses" :key="w">
                  <WarningOutlined style="color: #faad14; margin-right: 8px" />
                  {{ w }}
                </li>
              </ul>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="建议" size="small" :headStyle="{ background: '#e6f7ff' }">
              <ul class="summary-list suggestions">
                <li v-for="s in report.suggestions" :key="s">
                  <BulbOutlined style="color: #1890ff; margin-right: 8px" />
                  {{ s }}
                </li>
              </ul>
            </a-card>
          </a-col>
        </a-row>

        <!-- 评估时间 -->
        <a-divider />
        <div class="assessment-time">
          <small>评估时间: {{ formatTime(report.assessment_time) }}</small>
        </div>
      </div>

      <!-- 无数据状态（引导用户） -->
      <div v-else class="empty-container">
        <a-empty description="暂无学习数据">
          <div class="guide-container">
            <a-alert type="info" show-icon style="margin-bottom: 16px">
              <template #message>
                学习效果评估需要基于您的学习数据，请按以下步骤开始学习：
              </template>
              <template #description>
                <ol class="guide-steps">
                  <li><a @click="router.push('/profile')">构建学习画像</a> - 系统了解您的学习背景和目标</li>
                  <li><a @click="router.push('/path')">生成学习路径</a> - 获得个性化学习计划</li>
                  <li><a @click="router.push('/resource')">学习资源内容</a> - 浏览文档、视频等资源</li>
                  <li><a @click="router.push('/assess')">完成答题评估</a> - 通过答题检验学习效果</li>
                </ol>
                <p style="margin-top: 12px; color: #8c8c8c">
                  完成以上步骤后，系统将自动记录您的学习数据，届时即可生成学习效果评估报告。
                </p>
              </template>
            </a-alert>
          </div>
        </a-empty>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAssessStore } from '../stores/assessStore'
import { useAuthStore } from '../../auth/stores/authStore'
import {
  CheckCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '../../../shared/utils/request'

const router = useRouter()
const assessStore = useAssessStore()
const authStore = useAuthStore()
const report = ref<any>(null)
const isGenerating = ref(false)

onMounted(async () => {
  await refreshReport()
})

async function refreshReport() {
  isGenerating.value = true
  try {
    const userId = authStore.user?.id || ''

    const response = await request.get(`/assess/learning-effect`, {
      params: { user_id: userId }
    })

    if (response.data?.success && response.data?.data) {
      report.value = response.data.data
    } else if (response.data) {
      report.value = response.data
    }

    // 逻辑闭环：只有当有实际学习数据时才显示"生成成功"
    if (report.value && report.value.statistics?.total_resources > 0) {
      message.success('评估报告生成成功')
    } else {
      // 没有学习数据时，不显示"生成成功"，保持空状态引导用户
      report.value = null
    }
  } catch (error: any) {
    console.error('获取学习效果评估失败:', error)
    // 错误时不显示任何消息，保持空状态
    report.value = null
  } finally {
    isGenerating.value = false
  }
}

function getScoreColor(score: number): string {
  if (score >= 70) return '#52c41a'
  if (score >= 50) return '#faad14'
  return '#ff4d4f'
}

function formatTime(time: string): string {
  if (!time) return '未知'
  try {
    return new Date(time).toLocaleString('zh-CN')
  } catch {
    return time
  }
}
</script>

<style scoped lang="less">
.learning-effect-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.loading-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.stats-row {
  margin-bottom: 24px;
}

.module-list {
  .module-item {
    margin-bottom: 16px;
    
    .module-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .module-name {
        font-weight: 500;
      }
    }
    
    .module-stats {
      display: flex;
      justify-content: space-between;
      margin-top: 4px;
      font-size: 12px;
      color: #8c8c8c;
    }
  }
}

.weak-points-list {
  margin: 0;
  padding-left: 20px;
  
  li {
    margin-bottom: 8px;
  }
}

.summary-list {
  margin: 0;
  padding: 0;
  list-style: none;
  
  li {
    margin-bottom: 12px;
    display: flex;
    align-items: flex-start;
  }
  
  &.strengths li {
    color: #52c41a;
  }
  
  &.weaknesses li {
    color: #faad14;
  }
  
  &.suggestions li {
    color: #1890ff;
  }
}

.assessment-time {
  text-align: center;
  color: #8c8c8c;
}

.guide-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 16px;
}

.guide-steps {
  margin: 12px 0;
  padding-left: 24px;
  
  li {
    margin-bottom: 12px;
    line-height: 1.8;
    
    a {
      color: #1890ff;
      cursor: pointer;
      font-weight: 500;
      
      &:hover {
        color: #40a9ff;
        text-decoration: underline;
      }
    }
  }
}
</style>