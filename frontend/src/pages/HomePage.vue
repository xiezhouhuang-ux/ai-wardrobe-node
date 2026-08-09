<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import StatsBar from '../components/StatsBar.vue'
import FilterBar from '../components/FilterBar.vue'
import Gallery from '../components/Gallery.vue'

const allItems = ref([])
const router = useRouter()
const filters = reactive({ search: '', category: '', color: '', season: '', style: '' })

const filtered = computed(() => {
  const { search, category, color, season, style } = filters
  const q = search.trim().toLowerCase()
  return allItems.value.filter((it) => {
    if (category && it.category !== category) return false
    if (color && it.color !== color) return false
    if (season && it.season !== season) return false
    if (style && it.style !== style) return false
    if (q) {
      const hay = [
        it.category, it.color, it.season, it.material,
        it.style, it.fit, it.pattern,
      ].join(' ').toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

async function loadItems() {
  allItems.value = await api.getItems()
}

async function onDelete(id) {
  await api.deleteItem(id)
  await loadItems()
}

function openItem(it) {
  router.push(`/item/${it.id}`)
}

onMounted(loadItems)
</script>

<template>
  <div>
    <div class="section-head">
      <h2>我的衣橱</h2>
      <span class="count-hint">共 {{ filtered.length }} 件</span>
    </div>

    <FilterBar
      :items="allItems"
      v-model:search="filters.search"
      v-model:category="filters.category"
      v-model:color="filters.color"
      v-model:season="filters.season"
      v-model:style="filters.style"
      @reset="Object.assign(filters, { search: '', category: '', color: '', season: '', style: '' })"
    />

    <StatsBar :items="allItems" />

    <Gallery :items="filtered" @open="openItem" />

    <div v-if="filtered.length === 0" class="empty">
      {{ allItems.length === 0 ? '还没有单品，点下方 ＋ 上传一张穿搭照片开始吧～' : '没有符合筛选条件的单品' }}
    </div>
  </div>
</template>
