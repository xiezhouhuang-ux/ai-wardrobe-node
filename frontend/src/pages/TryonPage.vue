<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import { setTryOnResultData, clearTryOnResultData } from '../utils/tryon-cache.js'

const router = useRouter()

const wardrobe = ref([])
const userPhoto = ref(null)
const selected = ref({})   // { 上衣: itemId, 下装: itemId, 鞋: itemId, 包: itemId }
const generating = ref(false)
const error = ref('')

const CATEGORIES = ['上衣', '下装', '鞋', '包']

// 按分类分组
const grouped = computed(() => {
  const map = {}
  for (const c of CATEGORIES) map[c] = []
  for (const it of wardrobe.value) {
    const cat = it.category
    if (map[cat]) map[cat].push(it)
    else {
      // 容错：归到其他分类
      if (!map['其他']) map['其他'] = []
      map['其他'].push(it)
    }
  }
  return map
})

// 已选单品详情
const selectedItems = computed(() => {
  const arr = []
  for (const cat of CATEGORIES) {
    const id = selected.value[cat]
    if (!id) continue
    const it = wardrobe.value.find(i => i.id === id)
    if (it) arr.push(it)
  }
  return arr
})

const canGenerate = computed(() => {
  return selectedItems.value.length > 0 && !generating.value
})

onMounted(async () => {
  try {
    wardrobe.value = await api.getItems()
    userPhoto.value = await api.getUserPhoto()
  } catch {
    // 用户照片未上传
  }
})

function toggleSelect(cat, itemId) {
  if (selected.value[cat] === itemId) {
    delete selected.value[cat]
  } else {
    selected.value[cat] = itemId
  }
  // 触发响应式
  selected.value = { ...selected.value }
}

function isSelected(cat, itemId) {
  return selected.value[cat] === itemId
}

function goToMe() {
  router.push('/me')
}

async function generate() {
  const ids = Object.values(selected.value).filter(Boolean)
  if (ids.length === 0) return
  generating.value = true
  error.value = ''
  try {
    const res = await api.tryOn(ids)
    // 将结果数据写入 sessionStorage 后跳转新页面
    setTryOnResultData({ resultUrl: res.resultUrl, itemIds: ids })
    router.push('/tryon/result')
  } catch (err) {
    error.value = err.message || '试穿生成失败，请重试'
  } finally {
    generating.value = false
  }
}

function reset() {
  selected.value = {}
  error.value = ''
  clearTryOnResultData()
}
</script>

<template>
  <div class="page">
    <h1 class="title">🪄 AI 试穿</h1>

    <!-- 无全身照 -->
    <div v-if="!userPhoto" class="banner">
      <span>⚠️ 尚未上传全身正面照，无法生成试穿效果</span>
      <button class="btn ghost" @click="goToMe">去上传</button>
    </div>

    <!-- 全身照已就绪 -->
    <div v-else class="photo-row">
      <img :src="userPhoto.url" class="user-photo" alt="我的全身照" />
      <span class="badge">✓ 底图已就绪</span>
    </div>

    <!-- 选择单品 -->
    <div class="section">
      <h3>选择穿搭单品 <span class="sel-count">已选 {{ selectedItems.length }} / 4</span></h3>

      <div v-for="cat in CATEGORIES" :key="cat" class="cat-section">
        <div class="cat-head">{{ cat }}</div>
        <div v-if="grouped[cat]?.length" class="items-row">
          <div
            v-for="it in grouped[cat]"
            :key="it.id"
            class="item-card"
            :class="{ active: isSelected(cat, it.id) }"
            @click="toggleSelect(cat, it.id)"
          >
            <div
              class="item-thumb"
              :style="{ backgroundImage: `url('${it.imageUrl}')` }"
            ></div>
            <div class="item-meta">
              <span class="item-name">{{ it.color || it.category }}</span>
              <span class="item-check">{{ isSelected(cat, it.id) ? '✓' : '' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="cat-empty">暂无{{ cat }}单品，去衣橱添加</div>
      </div>
    </div>

    <!-- 已选概览 + 操作 -->
    <div v-if="selectedItems.length" class="overview">
      <div class="ov-title">已选单品</div>
      <div class="ov-items">
        <div v-for="it in selectedItems" :key="it.id" class="ov-chip">
          <div class="ov-thumb" :style="{ backgroundImage: `url('${it.imageUrl}')` }"></div>
          <span>{{ it.category }} · {{ it.color }}</span>
        </div>
      </div>
      <button class="btn primary" :disabled="!canGenerate" @click="generate">
        {{ generating ? '正在生成…' : '生成试穿效果' }}
      </button>
      <button class="btn outline" style="margin-top:8px" @click="reset">🔄 重新选择</button>
    </div>

    <div v-if="error" class="error">⚠️ {{ error }}</div>
  </div>
</template>

<style scoped>
.page { padding: 0 4px 100px; }
.title { font-size: 22px; margin: 0 0 16px; }

/* 提示条 */
.banner {
  background: #fff7e6;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 14px;
}
.btn.ghost {
  height: 30px;
  border: 1px solid var(--accent, #5b7fff);
  background: #fff;
  color: var(--accent, #5b7fff);
  border-radius: 7px;
  padding: 0 12px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

/* 底图信息 */
.photo-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  background: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--line, #e8ecf1);
}
.user-photo {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
}
.badge {
  color: #3a9d5a;
  font-size: 13px;
  font-weight: 500;
}

/* 选择区 */
.section {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--line, #e8ecf1);
  margin-bottom: 14px;
}
.section h3 {
  margin: 0 0 12px;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sel-count { font-size: 12px; color: var(--muted, #93a0b2); font-weight: 400; }

.cat-section { margin-bottom: 12px; }
.cat-section:last-child { margin-bottom: 0; }
.cat-head {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #1a2b3c);
  margin-bottom: 8px;
}
.cat-empty {
  font-size: 12px;
  color: var(--muted, #93a0b2);
  padding: 8px 0;
}

.items-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  -webkit-overflow-scrolling: touch;
}
.items-row::-webkit-scrollbar { display: none; }

.item-card {
  flex-shrink: 0;
  width: 72px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border .15s;
  background: #f8f9fb;
}
.item-card.active { border-color: var(--accent, #5b7fff); }
.item-thumb {
  width: 72px;
  height: 72px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.item-meta {
  padding: 4px 6px 6px;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-check { color: var(--accent, #5b7fff); font-weight: 700; flex-shrink: 0; }

/* 已选概览 */
.overview {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--line, #e8ecf1);
  margin-bottom: 14px;
}
.ov-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.ov-items { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.ov-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f0f2f6;
  border-radius: 8px;
  padding: 4px 10px 4px 4px;
  font-size: 12px;
}
.ov-thumb {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background-size: cover;
  background-position: center;
}

.btn.primary {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: var(--accent, #5b7fff);
  color: #fff;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
}
.btn.primary:disabled { opacity: .5; cursor: not-allowed; }

.btn.outline {
  width: 100%;
  height: 38px;
  border: 1px solid var(--line, #dde);
  background: #fff;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.error {
  color: #e23b3b;
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}
</style>
