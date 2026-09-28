/**
 * 报告生成 Agent Prompts
 * 专职生成专业的学习报告，类似Word文档格式
 */

import type { ProfileData } from '../../../shared/types'

/** 构建报告生成消息 */
export function buildReportMessages(
  profileData: ProfileData,
  pathData: {
    completedStages: number
    activeStages: number
    pendingStages: number
    totalProgress: number
    stages: any[]
  },
  assessData: {
    totalAssessCount: number
    wrongAnswers: any[]
    avgScore?: number
  },
  qaData: {
    totalQuestions: number
    recentTopics: string[]
  },
  resourceData: {
    total: number
    completed: number
    byType: Record<string, any[]>
  }
): { role: 'system' | 'user'; content: string }[] {
  const systemPrompt = `你是一位专业的教育报告撰写专家，负责为学生生成详细的学习报告。

**报告格式要求**：
1. 使用正式的报告语言，避免口语化表达
2. 每个章节要有清晰的标题和编号
3. 使用表格、列表等结构化元素展示数据
4. 给出具体的数据分析和改进建议
5. 语言风格类似Word文档中的正式报告

**报告结构**：
## 一、学习概况总结
- 学习周期概述
- 整体学习表现评价

## 二、画像维度分析
- 各维度得分解读
- 学习风格特点分析

## 三、学习路径进展
- 阶段完成情况
- 知识点掌握进度

## 四、测评表现分析
- 测评成绩统计
- 错题类型分析
- 知识薄弱点诊断

## 五、答疑互动情况
- 答疑问题统计
- 知识困惑点分析

## 六、资源利用情况
- 资源完成率分析
- 学习偏好统计

## 七、综合评价与建议
- 学习成效综合评价
- 后续学习建议
- 重点突破方向

请严格按照上述结构生成报告，使用Markdown格式。`

  const userPrompt = `请根据以下数据生成一份专业的学习报告：

**【学生画像】**
- 专业方向：${profileData.major || '未设置'}
- 年级水平：${profileData.grade || '未设置'}
- 基础水平：${profileData.base_level || '未设置'}
- 学习目标：${profileData.study_goal || '未设置'}
- 认知风格：${profileData.cognitive_style || '未设置'}
- 学习节奏：${profileData.study_rhythm || '未设置'}
- 内容偏好：${profileData.interest_preference || '未设置'}
- 薄弱知识点：${profileData.weak_points?.join('、') || '无'}
- 已掌握知识点：${profileData.masteredPoints?.join('、') || '暂无'}

**【画像维度得分】**
${profileData.dimensions?.map(d => `- ${d.name}：${d.value}分（${d.label}）`).join('\n') || '暂无数据'}

**【学习路径进展】**
- 已完成阶段：${pathData.completedStages}个
- 进行中阶段：${pathData.activeStages}个
- 待开始阶段：${pathData.pendingStages}个
- 总进度：${pathData.totalProgress}%
${pathData.stages?.slice(0, 5).map(s => `  - ${s.title}：${s.progress}%（${s.status === 'completed' ? '已完成' : s.status === 'active' ? '进行中' : '待开始'}）`).join('\n') || ''}

**【测评表现】**
- 完成测评次数：${assessData.totalAssessCount}次
- 平均得分：${assessData.avgScore || '暂无'}分
- 错题数量：${assessData.wrongAnswers?.length || 0}道
${assessData.wrongAnswers?.slice(0, 5).map(w => `  - ${w.question?.slice(0, 30)}...`).join('\n') || ''}

**【答疑互动】**
- 答疑问题总数：${qaData.totalQuestions}个
- 近期关注话题：${qaData.recentTopics?.join('、') || '暂无'}

**【资源利用】**
- 资源总数：${resourceData.total}个
- 已完成资源：${resourceData.completed}个
- 完成率：${resourceData.total > 0 ? Math.round(resourceData.completed / resourceData.total * 100) : 0}%
${Object.entries(resourceData.byType || {}).map(([type, items]) => `  - ${type}类型：${items?.length || 0}个`).join('\n') || ''}

**【学习统计】**
- 连续学习天数：${profileData.streakDays || 0}天
- 累计学习时长：${Math.round((profileData.totalStudyMinutes || 0) / 60)}小时
- 完成资源数：${profileData.completedResourceCount || 0}个
- 完成阶段数：${profileData.completedStageCount || 0}个
- 完成测评数：${profileData.completedAssessCount || 0}次

请生成一份完整、专业的学习报告。`

  return [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ]
}

/** 降级报告模板 */
export function getFallbackReport(
  profileData: ProfileData,
  pathData: any,
  assessData: any,
  qaData: any,
  resourceData: any
): string {
  const major = profileData.major || '该专业'
  const baseLevel = profileData.base_level || '基础'
  const totalHours = Math.round((profileData.totalStudyMinutes || 0) / 60)
  const completionRate = resourceData.total > 0 
    ? Math.round(resourceData.completed / resourceData.total * 100) 
    : 0

  return `## 一、学习概况总结

本次报告基于学生在AI学习系统中的学习数据，对${major}方向的学习情况进行综合分析。学生在本学习周期内累计学习${totalHours}小时，连续学习${profileData.streakDays || 0}天，整体学习态度积极。

**学习成效概述**：
| 指标 | 数据 | 评价 |
|------|------|------|
| 累计学时 | ${totalHours}小时 | ${totalHours >= 10 ? '良好' : '待提升'} |
| 连续学习 | ${profileData.streakDays || 0}天 | ${profileData.streakDays >= 7 ? '优秀' : '需坚持'} |
| 资源完成率 | ${completionRate}% | ${completionRate >= 50 ? '良好' : '待提升'} |

## 二、画像维度分析

学生当前基础水平为**${baseLevel}**，学习目标为**${profileData.study_goal || '全面掌握'}**。

**维度得分表**：
${profileData.dimensions?.map(d => `| ${d.name} | ${d.value}分 | ${d.label} |`).join('\n') || '| 暂无数据 | - | - |'}

**学习风格特点**：
- 认知风格：${profileData.cognitive_style || '综合型'}
- 学习节奏：${profileData.study_rhythm || '适中节奏'}
- 内容偏好：${profileData.interest_preference || '综合型'}

## 三、学习路径进展

**阶段完成统计**：
| 状态 | 数量 | 占比 |
|------|------|------|
| 已完成 | ${pathData.completedStages}个 | ${pathData.totalProgress}% |
| 进行中 | ${pathData.activeStages}个 | - |
| 待开始 | ${pathData.pendingStages}个 | - |

当前学习路径总进度为**${pathData.totalProgress}%**，建议继续按计划推进。

## 四、测评表现分析

**测评数据统计**：
- 完成测评次数：${assessData.totalAssessCount}次
- 错题数量：${assessData.wrongAnswers?.length || 0}道

${assessData.wrongAnswers?.length > 0 ? `**典型错题示例**：
${assessData.wrongAnswers.slice(0, 3).map((w: any, i: number) => `${i + 1}. ${w.question?.slice(0, 50)}...`).join('\n')}` : '暂无错题记录，表现良好。'}

## 五、答疑互动情况

- 答疑问题总数：${qaData.totalQuestions}个
- 近期关注话题：${qaData.recentTopics?.join('、') || '暂无记录'}

${qaData.totalQuestions > 0 ? '学生主动提问意识较强，学习积极性高。' : '建议学生在遇到困惑时积极提问，提高学习效率。'}

## 六、资源利用情况

**资源完成统计**：
| 类型 | 数量 | 完成情况 |
|------|------|----------|
| 总资源 | ${resourceData.total}个 | ${resourceData.completed}个已完成 |
| 完成率 | ${completionRate}% | ${completionRate >= 50 ? '良好' : '待提升'} |

## 七、综合评价与建议

**综合评价**：
学生整体学习表现${completionRate >= 50 && profileData.streakDays >= 3 ? '良好' : '有待提升'}。基础水平处于${baseLevel}阶段，学习态度积极。

**后续学习建议**：

1. **巩固薄弱知识点**
   针对${profileData.weak_points?.join('、') || '当前薄弱点'}进行专项练习，建议每天安排30分钟进行针对性训练。

2. **保持学习节奏**
   当前连续学习${profileData.streakDays || 0}天，建议继续保持每日学习的习惯，形成稳定的学习节奏。

3. **提高资源利用率**
   当前资源完成率为${completionRate}%，建议优先完成核心资源，再拓展辅助学习材料。

4. **加强测评练习**
   通过测评检验学习效果，建议每周至少完成1次测评，及时发现知识薄弱点。

5. **积极答疑互动**
   鼓励学生在遇到困惑时主动提问，充分利用答疑功能解决学习难题。

---

*报告生成时间：${new Date().toLocaleDateString('zh-CN')} ${new Date().toLocaleTimeString('zh-CN')}*
*AI学习系统 自动生成*`
}