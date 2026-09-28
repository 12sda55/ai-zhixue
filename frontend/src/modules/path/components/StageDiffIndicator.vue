<template>
  <div v-if="hasChanges && diff" class="diff-indicator">
    <div v-if="diff.addedStages.length" class="diff-group added">
      <div class="diff-title">新增阶段</div>
      <div v-for="s in diff.addedStages" :key="s.id" class="diff-item add">
        <span class="diff-sign">+</span> {{ s.title }}
      </div>
    </div>

    <div v-if="diff.removedStages.length" class="diff-group removed">
      <div class="diff-title">移除阶段</div>
      <div v-for="s in diff.removedStages" :key="s.id" class="diff-item remove">
        <span class="diff-sign">−</span> {{ s.title }}
      </div>
    </div>

    <div v-if="diff.modifiedStages.length" class="diff-group modified">
      <div class="diff-title">调整阶段</div>
      <div v-for="m in diff.modifiedStages" :key="m.new.id" class="diff-item modify">
        <span class="diff-sign">~</span> {{ m.new.title }}
        <span v-if="m.old.suggestedDays !== m.new.suggestedDays" class="diff-detail">
          {{ m.old.suggestedDays }}天 → {{ m.new.suggestedDays }}天
        </span>
      </div>
    </div>

    <div v-if="diff.addedResources.length" class="diff-group added">
      <div class="diff-title">新增资源</div>
      <div v-for="r in diff.addedResources" :key="r.resource.id" class="diff-item add">
        <span class="diff-sign">+</span> {{ r.resource.name }}
      </div>
    </div>

    <div v-if="diff.removedResources.length" class="diff-group removed">
      <div class="diff-title">移除资源</div>
      <div v-for="r in diff.removedResources" :key="r.resource.id" class="diff-item remove">
        <span class="diff-sign">−</span> {{ r.resource.name }}
      </div>
    </div>

    <button class="diff-dismiss" @click="$emit('dismiss')">知道了</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PathDiff } from '../../../shared/types'

const props = defineProps<{
  diff: PathDiff | null
}>()

defineEmits<{
  dismiss: []
}>()

const hasChanges = computed(() => {
  if (!props.diff) return false
  const d = props.diff
  return d.addedStages.length || d.removedStages.length || d.modifiedStages.length ||
    d.addedResources.length || d.removedResources.length
})
</script>

<style lang="less" scoped>
.diff-indicator {
  padding: 12px 14px;
  background: rgba(167, 139, 250, 0.06);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 10px;
  margin-bottom: 12px;
}

.diff-group {
  margin-bottom: 8px;

  &:last-of-type { margin-bottom: 10px; }
}

.diff-title {
  font-size: 10px;
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 4px;
}

.diff-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 0;

  &.add { color: #34d399; }
  &.remove { color: #ef4444; }
  &.modify { color: #f59e0b; }
}

.diff-sign {
  font-weight: 700;
  width: 14px;
  text-align: center;
}

.diff-detail {
  font-size: 10px;
  color: #5a7a8a;
  margin-left: 6px;
}

.diff-dismiss {
  display: block;
  width: 100%;
  padding: 6px;
  border-radius: 6px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  background: rgba(167, 139, 250, 0.06);
  color: #a78bfa;
  font-size: 11px;
  cursor: pointer;

  &:hover { background: rgba(167, 139, 250, 0.12); }
}
</style>
