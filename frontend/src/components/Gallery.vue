<script setup>
import { CATEGORY_LABELS, colorHex } from '../constants.js'

defineProps({
  items: { type: Array, default: () => [] },
})

const emit = defineEmits(['open'])

function bg(url) {
  return url ? `url('${url}')` : ''
}
</script>

<template>
  <div class="gallery">
    <div
      v-for="it in items"
      :key="it.id"
      class="item-card"
      @click="emit('open', it)"
    >
      <span class="cat-badge">{{ CATEGORY_LABELS[it.category] || it.category }}</span>
      <div
        class="item-img"
        :style="{ backgroundImage: bg(it.imageUrl) }"
      ></div>
      <div class="item-meta">
        <div class="row1">
          <span class="color-dot" :style="{ background: colorHex(it.color) }"></span>
          <span>{{ it.color }}</span>
        </div>
        <div class="row2">{{ it.style }} · {{ it.season }}</div>
      </div>
    </div>
  </div>
</template>
