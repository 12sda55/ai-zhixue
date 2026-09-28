import type { RadarSnapshot } from '../../../shared/types'

const GALLERY_STORAGE_KEY = 'ai_learning_gallery_snapshots'

/** 从 localStorage 加载快照列表 */
export function loadSnapshotsFromStorage(): RadarSnapshot[] {
  try {
    const raw = localStorage.getItem(GALLERY_STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as RadarSnapshot[]
  } catch {
    return []
  }
}

/** 保存快照列表到 localStorage */
export function saveSnapshotsToStorage(snapshots: RadarSnapshot[]): void {
  try {
    localStorage.setItem(GALLERY_STORAGE_KEY, JSON.stringify(snapshots))
  } catch {
    console.warn('[GalleryApi] localStorage save failed')
  }
}

/** 保存单个快照（追加到 localStorage） */
export function saveSnapshotToApi(snapshot: RadarSnapshot): void {
  const snapshots = loadSnapshotsFromStorage()
  const existingIndex = snapshots.findIndex(s => s.id === snapshot.id)
  if (existingIndex >= 0) {
    snapshots[existingIndex] = snapshot
  } else {
    snapshots.unshift(snapshot)
  }
  saveSnapshotsToStorage(snapshots)
}

/** 删除快照 */
export function deleteSnapshotFromApi(id: string): void {
  const snapshots = loadSnapshotsFromStorage()
  const filtered = snapshots.filter(s => s.id !== id)
  saveSnapshotsToStorage(filtered)
}

/**
 * 后端 API 预留接口
 * 当后端就绪后，替换为真实 HTTP 请求
 */

// export async function fetchSnapshotsFromServer(userId: string): Promise<RadarSnapshot[]> {
//   const res = await fetch(`/api/gallery/snapshots?userId=${userId}`)
//   return res.json()
// }

// export async function saveSnapshotToServer(snapshot: RadarSnapshot): Promise<void> {
//   await fetch('/api/gallery/snapshots', {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify(snapshot),
//   })
// }

// export async function deleteSnapshotFromServer(id: string): Promise<void> {
//   await fetch(`/api/gallery/snapshots/${id}`, { method: 'DELETE' })
// }
