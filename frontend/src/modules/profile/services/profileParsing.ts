export function parseProfileUpdate(content: string): Record<string, string> | null {
  const match = content.match(/```profile-update\n([\s\S]*?)```/)
  if (!match) return null

  const block = match[1]
  const result: Record<string, string> = {}
  block.split('|').forEach(pair => {
    const [key, val] = pair.split(':')
    if (key && val) {
      result[key.trim()] = val.trim()
    }
  })
  return Object.keys(result).length > 0 ? result : null
}

export function parseProfileSummary(content: string): Record<string, string> | null {
  const match = content.match(/```profile-summary\n([\s\S]*?)```/)
  if (!match) return null

  const block = match[1]
  const result: Record<string, string> = {}
  block.split('|').forEach(pair => {
    const [key, val] = pair.split(':')
    if (key && val) {
      result[key.trim()] = val.trim()
    }
  })
  return Object.keys(result).length > 0 ? result : null
}
