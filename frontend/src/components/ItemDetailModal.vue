<script setup>
import { catLabel, segmentMethodLabel } from '../constants.js'

const props = defineProps({
  item: { type: Object, default: null },
})

const emit = defineEmits(['close', 'delete'])

function bg(url) {
  return url ? `url('${url}')` : ''
}

function tagsOf(it) {
  const t = []
  t.push({ k: '类别', v: catLabel(it.category) })
  if (it.color) t.push({ k: '颜色', v: it.color })
  if (it.season) t.push({ k: '季节', v: it.season })
  if (it.material && it.material !== '未知') t.push({ k: '材质', v: it.material })
  if (it.style) t.push({ k: '风格', v: it.style })
  if (it.fit && it.fit !== '常规') t.push({ k: '版型', v: it.fit })
  if (it.pattern && it.pattern !== '纯色') t.push({ k: '图案', v: it.pattern })
  if (it.brand) t.push({ k: '品牌', v: it.brand })
  t.push({ k: '抠图', v: segmentMethodLabel(it.segmentMethod) })
  return t
}
</script>

<template>
  <div class="modal" :class="{ hidden: !item }" @click.self="emit('close')">
    <div class="modal-backdrop"></div>
    <div v-if="item" class="modal-card">
      <button class="modal-close" @click="emit('close')">×</button>
      <div class="modal-body">
        <div class="modal-img" :style="{ backgroundImage: bg(item.imageUrl) }"></div>
        <div class="modal-info">
          <h3>{{ catLabel(item.category) }} · {{ item.color }}</h3>
          <div class="tag-list">
            <span v-for="t in tagsOf(item)" :key="t.k" class="tag">{{ t.k }}：{{ t.v }}</span>
          </div>
          <div class="modal-source" v-if="item.sourcePhoto">
            来源照片：<a :href="item.sourcePhoto" target="_blank" rel="noopener">{{ item.sourcePhoto }}</a>
          </div>
          <button class="danger-btn" @click="emit('delete', item.id)">删除该单品</button>
        </div>
      </div>
    </div>
  </div>
</template>
