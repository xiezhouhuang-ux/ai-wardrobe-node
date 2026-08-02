<script setup>
import { computed } from 'vue'
import { CATEGORY_LABELS } from '../constants.js'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const search = defineModel('search', { default: '' })
const category = defineModel('category', { default: '' })
const color = defineModel('color', { default: '' })
const season = defineModel('season', { default: '' })
const style = defineModel('style', { default: '' })

const emit = defineEmits(['reset'])

const categoryOptions = Object.entries(CATEGORY_LABELS).map(([v, label]) => ({ value: v, label }))

const colorOptions = computed(() =>
  [...new Set(props.items.map((i) => i.color).filter(Boolean))].map((c) => ({ value: c, label: c }))
)

const seasonOptions = ['春', '夏', '秋', '冬', '四季'].map((s) => ({ value: s, label: s }))

const styleOptions = computed(() =>
  [...new Set(props.items.map((i) => i.style).filter(Boolean))].map((s) => ({ value: s, label: s }))
)
</script>

<template>
  <div id="filters">
    <input v-model="search" class="f-input" type="text" placeholder="搜索颜色 / 材质 / 风格 / 品牌…" />
    <select v-model="category" class="f-select">
      <option value="">全部类别</option>
      <option v-for="o in categoryOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <select v-model="color" class="f-select">
      <option value="">全部颜色</option>
      <option v-for="o in colorOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <select v-model="season" class="f-select">
      <option value="">全部季节</option>
      <option v-for="o in seasonOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <select v-model="style" class="f-select">
      <option value="">全部风格</option>
      <option v-for="o in styleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <div class="filters-spacer"></div>
    <button id="resetFilters" @click="emit('reset')">重置筛选</button>
  </div>
</template>
