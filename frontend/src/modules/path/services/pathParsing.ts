import type { ProfileData } from '../../../shared/types'
import { filterRelevantWeakPoints } from '../../../shared/utils/subjectFilter'

/** 返回画像数据的浅拷贝，其中 weak_points 已按当前科目过滤掉跨科目污染内容 */
export function getFilteredProfile(profileData: ProfileData): ProfileData {
  const subject = profileData.currentSubject || profileData.major || ''
  const filtered = filterRelevantWeakPoints(profileData.weak_points || [], subject)
  return { ...profileData, weak_points: filtered }
}

/** 解析 path-plan 代码块 */
export function parsePathPlan(raw: string): { summary: string; stages: any[] } | null {
  const match = raw.match(/```path-plan\n([\s\S]*?)```/)
  if (!match) {
    console.warn('[Path] 未找到 path-plan 代码块')
    return null
  }

  try {
    const json = JSON.parse(match[1])
    console.log('[Path] 解析成功，原始数据:', JSON.stringify(json, null, 2))
    if (!json.stages || !Array.isArray(json.stages)) return null
    return json
  } catch (e) {
    console.warn('[Path] JSON 解析失败:', e)
    try {
      const cleaned = match[1].replace(/,\s*([}\]])/g, '$1')
      const json = JSON.parse(cleaned)
      console.log('[Path] 修复后解析成功，原始数据:', JSON.stringify(json, null, 2))
      if (!json.stages || !Array.isArray(json.stages)) return null
      return json
    } catch {
      return null
    }
  }
}
