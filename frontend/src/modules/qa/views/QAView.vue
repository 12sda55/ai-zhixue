<template>
  <div class="qa-container">
    <!-- 左侧：聊天面板 -->
    <div class="qa-left">
      <QaChat />
    </div>

    <!-- 右侧：画像概览 + 历史记录 -->
    <div class="qa-right">
      <div class="qa-header">
        <span class="qa-header-icon">💬</span>
        <div class="qa-header-info">
          <div class="qa-header-title">智能答疑</div>
          <div class="qa-header-sub">基于画像的个性化解答</div>
        </div>
      </div>

      <!-- 当前画像摘要 -->
      <div class="qa-profile">
        <div class="qa-profile-title">当前画像</div>
        <div class="qa-profile-tags">
          <span class="qa-tag">{{ profileData.base_level }}</span>
          <span class="qa-tag qa-tag-purple">{{ profileData.cognitive_style }}</span>
          <span class="qa-tag">{{ profileData.study_goal }}</span>
        </div>
        <div v-if="profileData.weak_points.length" class="qa-weak">
          <span class="qa-weak-label">薄弱点</span>
          <span v-for="wp in profileData.weak_points" :key="wp" class="qa-weak-tag">{{ wp }}</span>
        </div>
      </div>

      <!-- 历史记录 -->
      <div class="qa-history">
        <div class="qa-section-title">最近提问</div>
        <div class="qa-history-list">
          <div v-for="h in history" :key="h.question" class="qa-history-item">
            <span class="qa-history-text">{{ h.question }}</span>
            <span class="qa-history-time">{{ h.time }}</span>
          </div>
          <div v-if="!history.length" class="qa-history-empty">暂无提问记录</div>
        </div>
      </div>

      <!-- 快速提问 -->
      <div class="qa-quick">
        <div class="qa-section-title">快速提问</div>
        <div class="qa-quick-list">
          <button v-for="q in quickQuestions" :key="q" class="qa-quick-btn" @click="store.sendMessage(q)">
            {{ q }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useQaStore } from '../stores/qaStore'
import { useProfileStore } from '../../profile/stores/profileStore'
import QaChat from '../components/QaChat.vue'

const store = useQaStore()
const profileStore = useProfileStore()
const profileData = computed(() => profileStore.profileData)
const history = computed(() => store.history)

/** 根据画像动态生成快速提问建议 */
const quickQuestions = computed(() => {
  const data = profileData.value
  const major = data.major || ''
  const weakPoints = data.weak_points || []
  const masteredPoints = data.masteredPoints || []
  const baseLevel = data.base_level || ''
  
  // 专业相关的基础问题模板
  const majorQuestions: Record<string, string[]> = {
    '软件工程': [
      '什么是软件生命周期？',
      '面向对象编程的核心概念是什么？',
      '什么是设计模式？常见的有哪些？',
      '软件测试有哪些类型？',
      '什么是版本控制？Git有什么优势？',
      '敏捷开发和瀑布模型的区别？',
    ],
    '计算机科学与技术': [
      '什么是时间复杂度和空间复杂度？',
      '链表和数组的区别是什么？',
      'BFS 和 DFS 的区别和应用场景？',
      '什么是二叉搜索树？',
      '快速排序的原理是什么？',
      '栈和队列的区别和应用？',
    ],
    '物理学': [
      '牛顿三大定律分别是什么？',
      '什么是动能和势能？',
      '光的折射和反射有什么区别？',
      '什么是电磁感应？',
      '量子力学的基本原理是什么？',
      '热力学第一定律是什么？',
    ],
    '化学': [
      '什么是有机化合物？',
      '羟基和羧基有什么区别？',
      '酯化反应的原理是什么？',
      '什么是取代反应和加成反应？',
      '苯环的结构特点是什么？',
      '烷烃的通式是什么？',
    ],
    '数学与应用数学': [
      '极限的定义是什么？',
      '导数的几何意义是什么？',
      '不定积分的基本公式有哪些？',
      '矩阵乘法满足什么性质？',
      '什么是线性方程组？',
      '概率的基本性质有哪些？',
    ],
    '历史学': [
      '秦朝为什么能统一中国？',
      '唐朝的盛世有哪些特点？',
      '鸦片战争对中国有什么影响？',
      '辛亥革命的意义是什么？',
      '文艺复兴的核心思想是什么？',
      '工业革命如何改变世界？',
    ],
    '经济学': [
      '供给和需求的关系是什么？',
      'GDP是什么？如何计算？',
      '通货膨胀的原因和影响？',
      '什么是货币政策？',
      '市场失灵的原因有哪些？',
      '什么是边际效用？',
    ],
    '医学': [
      '人体有哪些主要系统？',
      '血液循环的路径是什么？',
      '什么是免疫系统？',
      '药物代谢的过程是什么？',
      '什么是病理变化？',
      '解剖学的基本概念有哪些？',
    ],
  }
  
  // 根据专业获取基础问题
  let questions: string[] = []
  
  // 匹配专业关键词
  const majorLower = major.toLowerCase()
  for (const [key, qs] of Object.entries(majorQuestions)) {
    if (majorLower.includes(key.toLowerCase()) || key.toLowerCase().includes(majorLower)) {
      questions = [...qs]
      break
    }
  }
  
  // 如果没有匹配到专业，使用通用问题
  if (questions.length === 0) {
    questions = [
      '这个领域的基础概念有哪些？',
      '如何理解这个知识点？',
      '这个概念的应用场景是什么？',
      '学习这个领域有什么建议？',
      '这个知识点和其他知识有什么联系？',
      '如何更好地掌握这个内容？',
    ]
  }
  
  // 根据薄弱知识点生成针对性问题
  if (weakPoints.length > 0) {
    const weakQuestions = weakPoints.slice(0, 2).map(point => 
      `${point}是什么？请详细解释`
    )
    // 将薄弱点问题插入到前面
    questions = [...weakQuestions, ...questions.slice(0, 4)]
  }
  
  // 根据已掌握知识点生成进阶问题
  if (masteredPoints.length > 0 && baseLevel !== '入门') {
    const advancedQuestions = masteredPoints.slice(0, 2).map(point => 
      `${point}的进阶应用有哪些？`
    )
    // 替换部分基础问题为进阶问题
    if (advancedQuestions.length > 0) {
      questions = [...questions.slice(0, 3), ...advancedQuestions, ...questions.slice(5)]
    }
  }
  
  // 返回最多6个问题
  return questions.slice(0, 6)
})
</script>

<style lang="less">
.qa-container {
  display: flex;
  height: 100%;
  background: transparent;
  overflow: hidden;
}

.qa-left {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 16px;
  background: transparent;
}

.qa-right {
  width: 320px;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-left: 1px solid rgba(37, 99, 235, 0.1);
  color: #1e293b;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.2); border-radius: 3px; }
}

.qa-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.qa-header-icon { font-size: 22px; }

.qa-header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qa-header-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.qa-header-sub {
  font-size: 12px;
  color: #94a3b8;
}

/* ===== 画像摘要 ===== */
.qa-profile {
  padding: 16px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);
}

.qa-profile-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 10px;
}

.qa-profile-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.qa-tag {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-weight: 500;
}

.qa-tag-purple {
  background: rgba(6, 182, 212, 0.1) !important;
  color: #06b6d4 !important;
}

.qa-weak {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.qa-weak-label {
  font-size: 12px;
  color: #f59e0b;
  font-weight: 600;
}

.qa-weak-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  font-weight: 500;
}

/* ===== 历史记录 ===== */
.qa-history {
  margin-bottom: 20px;
}

.qa-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 10px;
}

.qa-history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qa-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  border: 1px solid rgba(37, 99, 235, 0.1);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(37, 99, 235, 0.08);
    border-color: rgba(37, 99, 235, 0.2);
  }
}

.qa-history-text {
  font-size: 12px;
  color: #475569;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qa-history-time {
  font-size: 10px;
  color: #94a3b8;
  flex-shrink: 0;
  margin-left: 10px;
}

.qa-history-empty {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  padding: 16px;
}

/* ===== 快速提问 ===== */
.qa-quick {
  margin-bottom: 20px;
}

.qa-quick-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qa-quick-btn {
  font-size: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  background: transparent;
  backdrop-filter: blur(16px) saturate(1.3);
  color: #475569;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(76, 78, 100, 0.06);

  &:hover {
    background: rgba(37, 99, 235, 0.08);
    border-color: rgba(37, 99, 235, 0.3);
    color: #2563eb;
  }
}

@media (max-width: 768px) {
  .qa-layout {
    flex-direction: column;
  }
  .qa-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(37, 99, 235, 0.1);
    max-height: 200px;
  }
}
</style>
