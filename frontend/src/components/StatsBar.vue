<script setup>
import { computed } from 'vue'
import { CATEGORY_LABELS } from '../constants.js'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const stats = computed(() => {
  const cats = {}
  for (const it of props.items) {
    const c = it.category || '其他'
    cats[c] = (cats[c] || 0) + 1
  }
  return Object.entries(cats).map(([cat, n]) => ({
    cat,
    label: CATEGORY_LABELS[cat] || cat,
    n,
  }))
})
</script>

<template>
  <div id="stats">
    <div class="stat-chip">全部 <b>{{ items.length }}</b> 件</div>
    <div v-for="s in stats" :key="s.cat" class="stat-chip">
      {{ s.label }} <b>{{ s.n }}</b>
    </div>
  </div>
</template>
