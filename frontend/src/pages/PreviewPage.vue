<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import { session, resetSession } from '../session.js'
import { catLabel, colorHex, segmentMethodLabel } from '../constants.js'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const done = ref(false)

const selected = ref([])

onMounted(() => {
  if (!session.segmented.length) {
    router.replace('/upload')
    return
  }
  selected.value = session.segmented.map(() => true)
})

const allChecked = computed({
  get: () => selected.value.length > 0 && selected.value.every(Boolean),
  set: (v) => { selected.value = selected.value.map(() => v) },
})

const chosenCount = computed(() => selected.value.filter(Boolean).length)

const cards = computed(() =>
  session.segmented.map((it, i) => ({ ...it, _idx: i, _on: selected.value[i] }))
)

function downloadOne(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name || 'item.png'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function downloadSelected() {
  session.segmented.forEach((it, i) => {
    if (selected.value[i]) downloadOne(it.imageUrl, (it.id || 'item') + '.png')
  })
}

async function commit() {
  const items = session.segmented.filter((_, i) => selected.value[i])
  if (!items.length) {
    error.value = '请至少勾选一个单品'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await api.commitItems(items)
    done.value = true
    resetSession()
    setTimeout(() => router.push('/'), 1200)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="preview-wrap" v-if="session.segmented.length">
    <div class="section-head">
      <h2>预览并入库</h2>
      <span class="count-hint">已选 {{ chosenCount }} / {{ session.segmented.length }}</span>
    </div>

    <label class="select-all">
      <input type="checkbox" v-model="allChecked" />
      全选
    </label>

    <div v-if="done" class="done-banner">✅ 已入库，正在返回衣橱…</div>

    <div class="gallery">
      <div
        v-for="c in cards"
        :key="c._idx"
        class="card"
        :class="{ off: !c._on }"
        @click="selected[c._idx] = !selected[c._idx]"
      >
        <span class="cat-badge">{{ catLabel(c.category) }}</span>
        <div class="item-img" :style="{ backgroundImage: c.imageUrl ? `url('${c.imageUrl}')` : '' }"></div>
        <div class="item-meta">
          <div class="row1">
            <span class="color-dot" :style="{ background: colorHex(c.color) }"></span>
            <span>{{ c.color }}</span>
          </div>
          <div class="row2">{{ c.style }} · {{ segmentMethodLabel(c.segmentMethod) }}</div>
        </div>
        <label class="pick" @click.stop>
          <input type="checkbox" :checked="c._on" @click.stop="selected[c._idx] = !selected[c._idx]" />
          入库
        </label>
      </div>
    </div>

    <div v-if="error" class="error">⚠️ {{ error }}</div>

    <div class="actions">
      <button class="btn ghost" @click="downloadSelected" :disabled="chosenCount === 0">下载预览图</button>
      <button class="btn primary" :disabled="loading || chosenCount === 0" @click="commit">
        {{ loading ? '入库中…' : '确认入库' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.preview-wrap { max-width: 1100px; margin: 0 auto; }
.select-all { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; margin-bottom: 12px; }
.done-banner { background: #eafaf0; color: #1f9d55; border: 1px solid #bdeccd; border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; font-size: 14px; }
.gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }
.card {
  background: #fff; border: 1px solid var(--line); border-radius: 14px;
  overflow: hidden; cursor: pointer; transition: .15s; position: relative;
}
.card.off { opacity: .5; }
.card:hover { border-color: var(--accent); }
.cat-badge { position: absolute; top: 8px; left: 8px; background: rgba(29,31,36,.72); color: #fff; font-size: 11px; padding: 3px 8px; border-radius: 999px; }
.item-img { height: 170px; background: #f0f2f6 center/cover no-repeat; }
.item-meta { padding: 10px 12px; }
.row1 { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.color-dot { width: 12px; height: 12px; border-radius: 50%; border: 1px solid var(--line); }
.row2 { font-size: 12px; color: var(--muted); margin-top: 4px; }
.pick { display: flex; align-items: center; gap: 6px; padding: 8px 12px; font-size: 13px; border-top: 1px solid var(--line); }
.actions { display: flex; gap: 10px; margin-top: 16px; }
.btn { height: 44px; border-radius: 10px; padding: 0 18px; font-size: 14px; cursor: pointer; border: 1px solid var(--line); background: #fff; }
.btn.primary { background: var(--accent); color: #fff; border: none; flex: 1; }
.btn.primary:disabled, .btn.ghost:disabled { opacity: .5; cursor: not-allowed; }
.error { color: #e23b3b; font-size: 13px; margin-top: 8px; }
</style>
