import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RadarSnapshot } from '../../../shared/types'
import { useProfileStore } from '../../profile/stores/profileStore'
import { loadSnapshotsFromStorage, saveSnapshotsToStorage, deleteSnapshotFromApi, saveSnapshotToApi } from '../api/galleryApi'

export const useGalleryStore = defineStore('gallery', () => {
  /* ===== State ===== */
  const snapshots = ref<RadarSnapshot[]>([])
  const currentSnapshot = ref<RadarSnapshot | null>(null)
  const isLoading = ref(false)

  /* ===== Computed ===== */
  const perfectSnapshots = computed(() => snapshots.value.filter(s => s.isPerfect))
  const manualSnapshots = computed(() => snapshots.value.filter(s => !s.isPerfect))
  const perfectCount = computed(() => perfectSnapshots.value.length)
  const totalSavedCount = computed(() => snapshots.value.length)
  const maxGrowth = computed(() => {
    if (snapshots.value.length === 0) return 0
    return Math.max(...snapshots.value.map(s => s.growthFromInitial))
  })

  /* ===== Methods ===== */

  /** 从 profileStore 和 localStorage 加载快照 */
  function loadSnapshots() {
    isLoading.value = true
    try {
      const profileStore = useProfileStore()
      // 优先使用 profileStore 中的快照数据
      if (profileStore.profileData?.snapshots?.length) {
        snapshots.value = [...profileStore.profileData.snapshots]
      } else {
        // 回退到 localStorage
        snapshots.value = loadSnapshotsFromStorage()
      }
    } finally {
      isLoading.value = false
    }
  }

  /** 根据 ID 查找快照 */
  function getSnapshotById(id: string): RadarSnapshot | undefined {
    return snapshots.value.find(s => s.id === id)
  }

  /** 保存当前画像快照 */
  function saveCurrentSnapshot(title: string, description?: string): RadarSnapshot | null {
    const profileStore = useProfileStore()
    const snapshot = profileStore.saveSnapshot(title, description)
    if (snapshot) {
      // 同步到 localStorage
      saveSnapshotToApi(snapshot)
      // 刷新列表
      loadSnapshots()
    }
    return snapshot
  }

  /** 删除快照 */
  function deleteSnapshot(id: string): boolean {
    const profileStore = useProfileStore()
    profileStore.deleteSnapshot(id)
    deleteSnapshotFromApi(id)
    // 刷新列表
    loadSnapshots()
    return true
  }

  /** 设置当前查看的快照 */
  function setCurrentSnapshot(id: string): boolean {
    const snapshot = getSnapshotById(id)
    if (snapshot) {
      currentSnapshot.value = snapshot
      return true
    }
    currentSnapshot.value = null
    return false
  }

  return {
    // state
    snapshots,
    currentSnapshot,
    isLoading,
    // computed
    perfectSnapshots,
    manualSnapshots,
    perfectCount,
    totalSavedCount,
    maxGrowth,
    // methods
    loadSnapshots,
    getSnapshotById,
    saveCurrentSnapshot,
    deleteSnapshot,
    setCurrentSnapshot,
  }
})
