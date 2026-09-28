<template>
  <svg
    :width="size"
    :height="size"
    :viewBox="iconDef?.viewBox || '0 0 24 24'"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="['svg-icon', `icon-${name}`]"
    v-html="iconDef?.paths || ''"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { iconPaths } from '../icons'

const props = withDefaults(defineProps<{
  name: string
  size?: number | string
  strokeWidth?: number
}>(), {
  size: 20,
  strokeWidth: 2,
})

const iconDef = computed(() => iconPaths[props.name])
</script>

<style scoped>
.svg-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>