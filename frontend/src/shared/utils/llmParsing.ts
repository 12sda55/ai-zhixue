/**
 * LLM 输出解析工具 — 全局唯一规范实现
 *
 * 从 LLM 的流式/块状输出中提取代码块、安全解析 JSON、修复截断、解析资源列表。
 * 其他文件不得重复实现这些函数，一律从此模块导入。
 */

import type { ResourceItem } from '../types'

/**
 * 从 LLM 输出中提取指定类型的代码块
 *
 * 策略：
 * 1. 精确匹配 ```type\n...\n``` 代码块
 * 2. 匹配无类型标记的 ``` 代码块（内容需以 [ 或 { 开头）
 * 3. 把整个输出当 JSON 解析（有些模型不包裹代码块）
 */
export function extractCodeBlock(raw: string, type: string): string | null {
  // 容错：允许 ``` 前后有空格、代码块标记后可能有额外文字、换行风格差异
  const regex = new RegExp('```\\s*' + type + '[^\\n]*\\n([\\s\\S]*?)\\n\\s*```')
  let match = raw.match(regex)
  if (match) return match[1].trim()

  // fallback：尝试匹配没有类型标记的 ``` 代码块（AI 有时省略类型）
  const genericRegex = new RegExp('```(?:json)?\\s*\\n([\\s\\S]*?)\\n\\s*```')
  match = raw.match(genericRegex)
  if (match) {
    const content = match[1].trim()
    if (content.startsWith('[') || content.startsWith('{')) {
      return content
    }
  }

  // fallback：直接尝试把整个原始输出当 JSON 解析（有些模型不包裹代码块）
  const trimmed = raw.trim()
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    return trimmed
  }

  return null
}

/** 尝试修复被截断的 JSON（补全缺失的括号） */
export function repairJson(raw: string): string {
  let s = raw.trim()
  if (!s) return s

  // 去掉末尾的逗号、不完整的键值对
  s = s.replace(/,\s*$/, '')

  // 计算未闭合的括号
  const stack: string[] = []
  let inStr = false
  let escape = false
  for (const ch of s) {
    if (escape) { escape = false; continue }
    if (ch === '\\') { escape = true; continue }
    if (ch === '"') { inStr = !inStr; continue }
    if (inStr) continue
    if (ch === '{' || ch === '[') stack.push(ch)
    if (ch === '}') { if (stack.length && stack[stack.length - 1] === '{') stack.pop() }
    if (ch === ']') { if (stack.length && stack[stack.length - 1] === '[') stack.pop() }
  }

  // 如果正在字符串内，先闭合字符串
  if (inStr) s += '"'

  // 补全不完整的最后一个对象/数组元素（截断可能停在 "key": "val 中间）
  s = s.replace(/,\s*"[^"]*"?\s*:\s*$/, '')

  // 补全未闭合的括号（逆序）
  for (let i = stack.length - 1; i >= 0; i--) {
    s += stack[i] === '{' ? '}' : ']'
  }

  return s
}

/**
 * 安全解析 JSON
 *
 * 3 级 fallback：
 * 1. 直接解析
 * 2. 修复截断后解析
 * 3. 提取第一个完整的 JSON 数组/对象后解析
 */
export function safeJsonParse(raw: string): any {
  try { return JSON.parse(raw) } catch { /* 继续 */ }
  try { return JSON.parse(repairJson(raw)) } catch { /* 继续 */ }
  const arrMatch = raw.match(/\[[\s\S]*?\]/)
  if (arrMatch) {
    try { return JSON.parse(repairJson(arrMatch[0])) } catch { /* 继续 */ }
  }
  const objMatch = raw.match(/\{[\s\S]*?\}/)
  if (objMatch) {
    try { return JSON.parse(repairJson(objMatch[0])) } catch { /* 继续 */ }
  }
  return null
}

/**
 * 解析 resource-list 代码块为 ResourceItem 数组
 *
 * @param raw LLM 原始输出
 * @param defaultType 资源类型缺省值（agentStore 传 'video'，其余传 'document'）
 */
export function parseResourceList(raw: string, defaultType: string = 'document'): ResourceItem[] {
  const block = extractCodeBlock(raw, 'resource-list')
  if (!block) {
    // fallback：从原始文本中尝试提取 JSON 数组
    const arrMatch = raw.match(/\[[\s\S]*\]/)
    if (arrMatch) {
      const parsed = safeJsonParse(arrMatch[0])
      if (Array.isArray(parsed)) {
        return parsed.map((item: any, i: number) => normalizeResourceItem(item, i, defaultType))
      }
    }
    return []
  }
  const parsed = safeJsonParse(block)
  if (!Array.isArray(parsed)) return []
  return parsed.map((item: any, i: number) => normalizeResourceItem(item, i, defaultType))
}

/** 将 LLM 输出的单个资源对象规范化为 ResourceItem */
function normalizeResourceItem(item: any, i: number, defaultType: string): ResourceItem {
  return {
    id: `res-${Date.now()}-${i}`,
    title: item.title || '未命名资源',
    type: item.type || defaultType,
    module: item.module || '',
    description: item.description || '',
    content: item.content || item.explanation || item.description || '',
    difficulty: item.difficulty || 'intermediate',
    tags: item.tags || [],
    url: item.url || '',
    createdAt: new Date().toISOString(),
    aiGenerated: true,
  } as ResourceItem
}
