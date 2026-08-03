<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTryOnResultData, clearTryOnResultData } from '../utils/tryon-cache.js'
import { saveTryOnRecord, getItems } from '../api.js'

const router = useRouter()

const resultUrl = ref('')
const itemIds = ref([])
const selectedItems = ref([])
const saving = ref(false)
const saved = ref(false)
const error = ref('')

onMounted(async () => {
  const cache = getTryOnResultData()
  if (!cache || !cache.resultUrl || !cache.itemIds?.length) {
    router.replace('/tryon')
    return
  }
  resultUrl.value = cache.resultUrl
  itemIds.value = cache.itemIds

  try {
    const allItems = await getItems()
    selectedItems.value = allItems.filter(it => itemIds.value.includes(it.id))
  } catch { /* ignore */ }
})

function goBack() {
  clearTryOnResultData()
  router.replace('/tryon')
}

async function handleSave() {
  if (saving.value || saved.value || !resultUrl.value) return
  saving.value = true
  error.value = ''
  try {
    await saveTryOnRecord(itemIds.value, resultUrl.value)
    saved.value = true
  } catch (err) {
    error.value = err.message || '保存失败，请重试'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="tryon-result-page">
    <div class="toolbar">
      <button class="back-btn" @click="goBack">&larr; 返回试穿</button>
      <h2>试穿效果预览</h2>
      <div class="spacer"></div>
    </div>

    <div class="result-card">
      <img :src="resultUrl" class="result-img" alt="AI试穿效果" />

      <div class="item-tags" v-if="selectedItems.length">
        <h4>搭配单品</h4>
        <div class="tags">
          <span v-for="it in selectedItems" :key="it.id" class="tag">
            <img v-if="it.imageUrl" :src="it.imageUrl" class="tag-thumb" />
            {{ it.color || '' }} {{ it.category || '' }}
          </span>
        </div>
      </div>

      <div class="actions">
        <button
          class="btn save-btn"
          :disabled="saving || saved"
          @click="handleSave"
        >
          {{ saved ? '✓ 已保存' : saving ? '保存中…' : '💾 保存此搭配' }}
        </button>
      </div>

      <div v-if="error" class="error-msg">⚠️ {{ error }}</div>
    </div>
  </div>
</template>

<style scoped>
.tryon-result-page {
  min-height: calc(100vh - 108px);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.toolbar h2 {
  margin: 0;
  font-size: 18px;
  text-align: center;
  flex: 1;
}
.spacer {
  width: 80px;
}
.back-btn {
  border: 1px solid #dde;
  background: #fff;
  border-radius: 8px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 14px;
  color: #555;
  white-space: nowrap;
}
.back-btn:hover {
  background: #f5f6f8;
}

.result-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e8ecf1;
  overflow: hidden;
}
.result-img {
  width: 100%;
  display: block;
  border-radius: 14px 14px 0 0;
}

.item-tags {
  padding: 16px 16px 0;
}
.item-tags h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #555;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  font-size: 12px;
  background: #f0f2f6;
  color: #1a2b3c;
  padding: 4px 10px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tag-thumb {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  object-fit: cover;
}

.actions {
  padding: 16px;
}
.save-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: #5b7fff;
  color: #fff;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
}
.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  padding: 0 16px 16px;
  color: #e23b3b;
  font-size: 13px;
  text-align: center;
}
</style>