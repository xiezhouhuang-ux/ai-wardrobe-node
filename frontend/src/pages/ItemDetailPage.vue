<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '../api.js'
import { session } from '../session.js'
import { catLabel, colorHex, segmentMethodLabel } from '../constants.js'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const loading = ref(true)
const error = ref('')

// 所有属性（含中文标签），统一展示
const fields = computed(() => {
  const it = item.value
  if (!it) return []
  const f = []
  if (it.category) f.push({ k: '类别', v: catLabel(it.category) })
  if (it.color) f.push({ k: '颜色', v: it.color, colorDot: true })
  if (it.season) f.push({ k: '季节', v: it.season })
  if (it.material && it.material !== '未知') f.push({ k: '材质', v: it.material })
  if (it.style) f.push({ k: '风格', v: it.style })
  if (it.fit && it.fit !== '常规') f.push({ k: '版型', v: it.fit })
  if (it.pattern && it.pattern !== '纯色') f.push({ k: '图案', v: it.pattern })
  if (it.brand) f.push({ k: '品牌', v: it.brand })
  if (typeof it.hasLogo === 'boolean') f.push({ k: '是否有 Logo', v: it.hasLogo ? '有' : '无' })
  f.push({ k: '分割方式', v: segmentMethodLabel(it.segmentMethod) })
  if (it.createdAt) {
    const d = new Date(it.createdAt)
    f.push({ k: '入库时间', v: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` })
  }
  return f
})

onMounted(async () => {
  const id = route.params.id
  // 优先从预览会话的临时单品中取（含 OSS 预览地址）
  const temp = session.segmented.find((it) => it.id === id)
  if (temp) {
    item.value = temp
    loading.value = false
    return
  }
  // 否则从后端拉取已入库单品
  try {
    item.value = await api.getItem(id)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

async function onDelete() {
  if (!item.value) return
  await api.deleteItem(item.value.id)
  router.replace('/')
}
</script>

<template>
  <div class="detail-wrap" v-if="!loading">
    <button class="back" @click="router.back()">← 返回</button>

    <div v-if="error" class="error">⚠️ {{ error }}</div>

    <div v-if="item" class="detail">
      <div class="imgs">
        <div class="img-box">
          <div class="img-label">单品预览图</div>
          <div class="img" :style="{ backgroundImage: item.imageUrl ? `url('${item.imageUrl}')` : '' }"></div>
        </div>
        <div class="img-box" v-if="item.sourcePhoto">
          <div class="img-label">原图</div>
          <div class="img" :style="{ backgroundImage: `url('${item.sourcePhoto}')` }"></div>
        </div>
      </div>

      <div class="info">
        <h2>{{ catLabel(item.category) }}<span v-if="item.color"> · {{ item.color }}</span></h2>
        <div class="attrs">
          <div class="attr" v-for="a in fields" :key="a.k">
            <span class="ak">{{ a.k }}</span>
            <span class="av">
              <span v-if="a.colorDot" class="color-dot" :style="{ background: colorHex(a.v) }"></span>
              {{ a.v }}
            </span>
          </div>
        </div>
        <button class="danger-btn" @click="onDelete">删除该单品</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-wrap { max-width: 900px; margin: 0 auto; }
.back { background: none; border: none; color: var(--accent); font-size: 14px; cursor: pointer; padding: 4px 0; }
.error { color: #e23b3b; font-size: 13px; margin: 10px 0; }
.detail { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 12px; }
.imgs { display: flex; flex-direction: column; gap: 14px; }
.img-box { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 12px; }
.img-label { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
.img { height: 280px; background: #f0f2f6 center/contain no-repeat; border-radius: 10px; }
.info h2 { margin: 0 0 14px; font-size: 20px; }
.attrs { display: flex; flex-direction: column; gap: 2px; }
.attr { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 14px; }
.ak { color: var(--muted); }
.av { display: inline-flex; align-items: center; gap: 8px; }
.color-dot { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--line); }
.danger-btn { margin-top: 18px; height: 42px; border: 1px solid #f0bcbc; color: #e23b3b; background: #fff; border-radius: 10px; cursor: pointer; width: 100%; }
@media (max-width: 640px) { .detail { grid-template-columns: 1fr; } }
</style>
