/**
 * Agent 输出解析工具 — 从 agentStore 抽离的纯函数
 *
 * 这些函数无响应式依赖，仅依赖 shared/utils/llmParsing 和 ResourceItem 类型。
 * agentStore 通过 import 调用，保持 store 专注于响应式状态管理和 agent 编排。
 */

import type { ResourceItem } from '../../../shared/types'
import { extractCodeBlock, safeJsonParse } from '../../../shared/utils/llmParsing'

/** 解析 mindmap-data 代码块为 markdown 格式（供 MindMapViewer 渲染） */
export function parseMindmapData(raw: string): ResourceItem | null {
  const block = extractCodeBlock(raw, 'mindmap-data')
  if (!block) return null
  const tree = safeJsonParse(block)
  if (!tree) return null
  const md = treeToMarkdown(tree)
  if (!md.trim()) return null
  return {
    id: `agent-mindmap-${Date.now()}`,
    title: '知识体系导图',
    type: 'mindmap',
    module: '',
    content: md,
    createdAt: new Date().toISOString(),
    aiGenerated: true,
  }
}

export function treeToMarkdown(node: any, depth = 0): string {
  if (!node || !node.name) return ''

  const indent = '#'.repeat(Math.min(depth + 1, 6))
  const highlight = node.highlight ? '🔴 ' : ''
  let md = `${indent} ${highlight}${node.name}\n`

  if (node.desc) {
    md += `${node.desc}\n\n`
  }

  if (node.children && Array.isArray(node.children)) {
    for (const child of node.children) {
      md += treeToMarkdown(child, depth + 1)
    }
  }

  return md
}

/** 根据主题选择 fallback 导图模板 */
export function getFallbackMindmap(topic: string, _weakPoints: string[] = []): string {
  const templates: Record<string, string> = {
    '计算机科学': `# 数据结构知识体系

## 线性结构
### 数组
连续内存存储，支持 O(1) 随机访问

### 链表
动态节点结构，插入删除 O(1)

### 栈
后进先出 LIFO，函数调用栈的基础

### 队列
先进先出 FIFO，广度优先搜索的基础

## 树形结构
### 二叉树
每个节点最多两个子节点，递归定义

### 二叉搜索树
左子树 < 根 < 右子树，支持高效查找

### 堆
完全二叉树，大顶堆/小顶堆用于优先队列

## 图结构
### 邻接表
链表数组，适合稀疏图

### 邻接矩阵
二维数组，适合稠密图

## 算法
### 排序算法
快排、归并、堆排的时间复杂度对比

### 查找算法
二分查找 O(log n)、哈希查找 O(1)

### 动态规划
最优子结构 + 重叠子问题`,
    '软件工程': `# 数据结构知识体系

## 线性结构
### 数组
连续内存存储，支持 O(1) 随机访问

### 链表
动态节点结构，插入删除 O(1)

### 栈
后进先出 LIFO，函数调用栈的基础

### 队列
先进先出 FIFO，广度优先搜索的基础

## 树形结构
### 二叉树
每个节点最多两个子节点，递归定义

### 二叉搜索树
左子树 < 根 < 右子树，支持高效查找

### 堆
完全二叉树，大顶堆/小顶堆用于优先队列

## 图结构
### 邻接表
链表数组，适合稀疏图

### 邻接矩阵
二维数组，适合稠密图

## 算法
### 排序算法
快排、归并、堆排的时间复杂度对比

### 查找算法
二分查找 O(log n)、哈希查找 O(1)

### 动态规划
最优子结构 + 重叠子问题`,
  }

  const defaultTemplate = `# ${topic}知识体系

## 基础概念
### 核心定义
本领域的基本概念和术语

### 基本原理
核心工作原理和机制

## 核心内容
### 主要方法
常用的技术和方法

### 重要工具
相关工具和框架

## 进阶应用
### 实践案例
典型应用场景

### 扩展知识
前沿发展和趋势`

  return templates[topic] || defaultTemplate
}

/** 解析 knowledge-graph 代码块 */
export function parseKnowledgeGraph(raw: string): ResourceItem | null {
  const block = extractCodeBlock(raw, 'knowledge-graph')
  if (!block) return null

  const graph = safeJsonParse(block)
  if (!graph) return null

  if (!graph.nodes || !Array.isArray(graph.nodes) ||
      !graph.edges || !Array.isArray(graph.edges)) {
    console.warn('[KnowledgeGraph] Invalid structure')
    return null
  }

  const nodeIds = new Set(graph.nodes.map((n: any) => n.id))
  if (nodeIds.size !== graph.nodes.length) {
    console.warn('[KnowledgeGraph] Duplicate node ids — attempting repair')
    const seen = new Set()
    graph.nodes = graph.nodes.filter((n: any) => {
      if (seen.has(n.id)) return false
      seen.add(n.id)
      return true
    })
  }

  const validNodeIds = new Set(graph.nodes.map((n: any) => n.id))
  graph.edges = graph.edges.filter((e: any) =>
    validNodeIds.has(e.source) && validNodeIds.has(e.target)
  )

  if (graph.nodes.length === 0) return null

  return {
    id: `agent-knowledge-graph-${Date.now()}`,
    title: '知识关联图谱',
    type: 'knowledge-graph',
    module: '',
    content: JSON.stringify(graph),
    createdAt: new Date().toISOString(),
    aiGenerated: true,
  }
}

/** 知识图谱 fallback */
export function getFallbackKnowledgeGraph(_topic: string, _weakPoints: string[] = []): string {
  const graph = {
    nodes: [
      { id: 'basics', name: '基础概念', category: 'core', importance: 5, desc: '核心定义和术语' },
      { id: 'principles', name: '基本原理', category: 'core', importance: 4, desc: '核心工作机制' },
      { id: 'methods', name: '主要方法', category: 'algorithm', importance: 4, desc: '常用技术方法' },
      { id: 'tools', name: '工具框架', category: 'application', importance: 3, desc: '相关工具和框架' },
      { id: 'practice', name: '实践应用', category: 'application', importance: 3, desc: '典型应用场景' },
      { id: 'advanced', name: '进阶内容', category: 'advanced', importance: 2, desc: '深入扩展知识' }
    ],
    edges: [
      { source: 'basics', target: 'principles', label: '基础' },
      { source: 'principles', target: 'methods', label: '支撑' },
      { source: 'methods', target: 'tools', label: '实现' },
      { source: 'tools', target: 'practice', label: '应用' },
      { source: 'practice', target: 'advanced', label: '延伸' },
      { source: 'basics', target: 'methods', label: '前置' }
    ]
  }
  return JSON.stringify(graph)
}

/** 解析 code-example 代码块 */
export function parseCodeExample(raw: string, topic: string): ResourceItem | null {
  const block = extractCodeBlock(raw, 'code-example')
  if (!block) return null
  const parsed = safeJsonParse(block)
  if (!parsed) return null
  return {
    id: `agent-code-${Date.now()}`,
    title: parsed.title || `${topic} 代码示例`,
    type: 'code',
    module: topic,
    content: parsed.code || block,
    description: parsed.explanation || '',
    difficulty: parsed.difficulty || '',
    createdAt: new Date().toISOString(),
    aiGenerated: true,
  }
}

/** 解析 assess-questions 代码块 */
export function parseAssessQuestions(raw: string, topic: string): ResourceItem | null {
  const block = extractCodeBlock(raw, 'assess-questions')
  if (!block) {
    if (raw.trim()) {
      return {
        id: `agent-exercise-${Date.now()}`,
        title: `${topic} 练习题`,
        type: 'exercise',
        module: topic,
        content: raw,
        createdAt: new Date().toISOString(),
        aiGenerated: true,
      }
    }
    return null
  }
  const parsed = safeJsonParse(block)
  if (!parsed || !Array.isArray(parsed)) {
    return {
      id: `agent-exercise-${Date.now()}`,
      title: `${topic} 练习题`,
      type: 'exercise',
      module: topic,
      content: block,
      createdAt: new Date().toISOString(),
      aiGenerated: true,
    }
  }
  let md = `## ${topic} 练习题\n\n`
  for (const q of parsed) {
    md += `### ${q.id || ''}. ${q.question || ''}\n\n`
    if (q.options) {
      for (const opt of q.options) { md += `- ${opt}\n` }
    }
    md += `\n> **答案**: ${q.answer || ''}\n\n`
    if (q.explanation) md += `> ${q.explanation}\n\n`
  }
  return {
    id: `agent-exercise-${Date.now()}`,
    title: `${topic} 练习题`,
    type: 'exercise',
    module: topic,
    content: md,
    createdAt: new Date().toISOString(),
    aiGenerated: true,
  }
}

/** 科目关键词映射（从薄弱点推导所属科目） */
const SUBJECT_KEYWORD_MAP: Record<string, string[]> = {
  '数据结构': ['数组', '链表', '栈', '队列', '树', '二叉树', '图', '哈希', '堆', '并查集', '字典树', '线段树', '散列表', '红黑树', 'AVL', 'B树'],
  '算法': ['排序', '查找', '递归', '动态规划', '贪心', '回溯', '分治', '时间复杂度', '空间复杂度', '暴力', '枚举', '搜索'],
  '操作系统': ['进程', '线程', '内存管理', '调度', '死锁', '文件系统', '虚拟内存', '分页', '信号量'],
  '计算机网络': ['TCP', 'UDP', 'HTTP', 'IP', '路由', 'DNS', '套接字', '三次握手', '四次挥手', 'OSI'],
  '数据库': ['SQL', '索引', '事务', '锁', '范式', 'ER图', '关系模型', '查询优化', '触发器', '存储过程'],
  '编译原理': ['词法分析', '语法分析', '语义分析', '中间代码', '优化', '目标代码', 'AST', '正则'],
  '计算机组成': ['CPU', '总线', '指令集', '流水线', '缓存', '寄存器', '寻址', '中断'],
  '离散数学': ['集合', '逻辑', '命题', '谓词', '关系', '函数', '图论', '组合', '概率'],
  '线性代数': ['矩阵', '向量', '行列式', '特征值', '线性变换', '空间', '方程组'],
  '概率论': ['概率', '随机变量', '分布', '期望', '方差', '贝叶斯', '大数定律', '中心极限'],
  '英语': ['英语', '动词', '名词', '形容词', '语法', '时态', '从句', '单词', '词汇', '阅读理解', '完形填空', '翻译', '写作', '听力', '口语', '虚拟语气', '被动语态', '非谓语', '定语从句', '状语从句', '宾语从句', '主语从句'],
  '日语': ['日语', '五十音', '助词', '动词变形', '敬语', '片假名', '平假名', '汉字', 'N1', 'N2', 'N3', '语法', '听力'],
  '高等数学': ['极限', '导数', '积分', '微积分', '微分', '泰勒', '洛必达', '中值定理', '不定积分', '定积分', '级数', '多元函数'],
  '大学物理': ['力学', '电磁学', '光学', '热学', '量子', '相对论', '波动', '电场', '磁场', '电路'],
  '政治': ['马原', '毛概', '思政', '政治经济学', '科学社会主义', '时事', '近现代史', '思修'],
}

/** 从画像推断当前学习科目 */
export function inferSubject(profileData: any): string {
  if (profileData.currentSubject) return profileData.currentSubject

  const weakPoints = profileData.weak_points?.length > 0 ? profileData.weak_points : []

  for (const [subject, keywords] of Object.entries(SUBJECT_KEYWORD_MAP)) {
    if (weakPoints.some((wp: string) =>
      keywords.some(kw => wp.toLowerCase().includes(kw.toLowerCase()) || kw.toLowerCase().includes(wp.toLowerCase()))
    )) {
      return subject
    }
  }

  const major = profileData.major || ''
  if (major.includes('计算机') || major.includes('软件') || major.includes('信息')) return '数据结构'
  if (major.includes('数学')) return '离散数学'
  if (major.includes('外语') || major.includes('英语') || major.includes('文学')) return '英语'
  if (major.includes('物理')) return '大学物理'

  if (weakPoints.length > 0) return weakPoints[0]

  return '综合学习'
}
