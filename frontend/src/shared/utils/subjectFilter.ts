/**
 * 科目相关性检测 — 全局唯一规范实现
 *
 * 其他文件不得内联 CS 关键词列表，一律从此模块导入。
 */

/** CS/编程类科目关键词 */
export const CS_SUBJECT_KEYWORDS: readonly string[] = [
  '数据结构', '算法', '编程', 'Python', 'Java', 'C++', 'C语言', 'JavaScript',
  '操作系统', '计算机网络', '数据库', '编译原理', '计算机组成', '软件工程',
]

/** CS/编程类薄弱点关键词（用于检测跨科目数据污染） */
export const CS_WEAKPOINT_KEYWORDS: readonly string[] = [
  '递归', '算法', '数据结构', '排序', '二叉树', '链表', '栈', '队列', '哈希表',
  '动态规划', '贪心', '回溯', '分治', '指针', '数组', '图', '树', '堆',
  '编译', '正则', '进程', '线程', '死锁', '内存', '缓存', 'CPU',
]

/** 判断科目是否为 CS/编程类 */
export function isCSSubject(subject: string): boolean {
  if (!subject) return false
  // 同时检查科目关键词和薄弱点关键词
  // 原因：用户可能选择"递归"等子主题作为科目，它在 CS_WEAKPOINT_KEYWORDS 里但不在 CS_SUBJECT_KEYWORDS 里
  return CS_SUBJECT_KEYWORDS.some(kw => subject.includes(kw)) ||
         CS_WEAKPOINT_KEYWORDS.some(kw => subject.includes(kw))
}

/** 判断薄弱点是否为 CS/编程类内容 */
export function isCSWeakPoint(wp: string): boolean {
  if (!wp) return false
  return CS_WEAKPOINT_KEYWORDS.some(kw => wp.includes(kw))
}

/** 过滤掉与当前科目不匹配的薄弱点（防止跨科目数据污染） */
export function filterRelevantWeakPoints(weakPoints: string[], subject: string): string[] {
  if (!weakPoints || !Array.isArray(weakPoints)) return []
  if (!subject) return weakPoints
  const subjectIsCS = isCSSubject(subject)
  return weakPoints.filter(wp => subjectIsCS ? isCSWeakPoint(wp) : !isCSWeakPoint(wp))
}
