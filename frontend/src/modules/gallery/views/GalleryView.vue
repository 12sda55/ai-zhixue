<template>
  <div class="gallery-view">
    <!-- 顶部标题区 -->
    <div class="gallery-header">
      <div class="header-text">
        <h1 class="header-title">🏛️ 完美雷达图展馆</h1>
        <p class="header-desc">收藏你学习的来时路</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-value">{{ galleryStore.perfectCount }}</span>
          <span class="stat-label">完美达成</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ galleryStore.totalSavedCount }}</span>
          <span class="stat-label">收藏画作</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ galleryStore.maxGrowth }}</span>
          <span class="stat-label">最高提升</span>
        </div>
      </div>
    </div>

    <!-- 画作网格 -->
    <div class="gallery-grid">
      <!-- 完美画作大卡 -->
      <PaintingCard
        v-for="snapshot in galleryStore.perfectSnapshots"
        :key="snapshot.id"
        :snapshot="snapshot"
        @click="goToDetail(snapshot.id)"
        @delete="handleDelete"
      />

      <!-- 手动保存标准卡片 -->
      <PaintingCard
        v-for="snapshot in galleryStore.manualSnapshots"
        :key="snapshot.id"
        :snapshot="snapshot"
        @click="goToDetail(snapshot.id)"
        @delete="handleDelete"
      />

      <!-- 空状态 -->
      <div v-if="galleryStore.snapshots.length === 0" class="empty-state">
        <div class="empty-icon">🎨</div>
        <p class="empty-text">还没有收藏的画作</p>
        <p class="empty-hint">完成学习后保存你的雷达图快照，它会出现在这里</p>
      </div>
    </div>

    <!-- 底部手动保存按钮 -->
    <div class="gallery-footer">
      <button class="btn-save-snapshot" @click="handleSaveSnapshot">
        <span class="btn-icon">📸</span>
        保存当前画像
      </button>
    </div>

    <!-- 完美达成提示 -->
    <PerfectToast
      :visible="showPerfect"
      @save="handlePerfectSave"
      @close="showPerfect = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGalleryStore } from '../stores/galleryStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import { message } from 'ant-design-vue'
import PaintingCard from '../components/PaintingCard.vue'
import PerfectToast from '../components/PerfectToast.vue'

const router = useRouter()
const galleryStore = useGalleryStore()
const profileStore = useProfileStore()
const showPerfect = ref(false)

onMounted(() => {
  galleryStore.loadSnapshots()
})

// 监听 profileStore 的完美达成提示
watch(() => profileStore.showPerfectToast, (val) => {
  if (val) {
    showPerfect.value = true
    profileStore.showPerfectToast = false
  }
})

function goToDetail(id: string) {
  router.push(`/gallery/${id}`)
}

function handleSaveSnapshot() {
  const title = `画像快照 - ${new Date().toLocaleDateString('zh-CN')}`
  galleryStore.saveCurrentSnapshot(title)
}

function handlePerfectSave() {
  const title = '⭐ 完美雷达图达成！'
  galleryStore.saveCurrentSnapshot(title, '8维全部 ≥ 90 的完美画像')
  showPerfect.value = false
}

function handleDelete(id: string) {
  galleryStore.deleteSnapshot(id)
  message.success('画作已删除')
}
</script>

<style lang="less" scoped>
.gallery-view {
  min-height: 100%;
  padding: 24px;
}

/* ===== 顶部标题区 ===== */
.gallery-header {
  margin-bottom: 28px;

  .header-text {
    margin-bottom: 16px;
  }

  .header-title {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: #64748b;
    margin: 0;
  }
}

.header-stats {
  display: inline-flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(14px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  .stat-value {
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .stat-label {
    font-size: 12px;
    color: #94a3b8;
  }
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: rgba(37, 99, 235, 0.1);
}

/* ===== 画作网格 ===== */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

/* ===== 空状态 ===== */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.6;
  }

  .empty-text {
    font-size: 16px;
    font-weight: 600;
    color: #475569;
    margin: 0 0 6px;
  }

  .empty-hint {
    font-size: 13px;
    color: #94a3b8;
    margin: 0;
  }
}

/* ===== 底部保存按钮 ===== */
.gallery-footer {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.btn-save-snapshot {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.25s ease;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);

  .btn-icon {
    font-size: 18px;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
  }

  &:active {
    transform: translateY(0);
  }
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .gallery-view {
    padding: 16px;
  }

  .gallery-grid {
    grid-template-columns: 1fr;
  }

  .gallery-header .header-title {
    font-size: 20px;
  }

  .header-stats {
    gap: 12px;
    padding: 10px 16px;
  }
}
</style>
