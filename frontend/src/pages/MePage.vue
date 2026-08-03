<script setup>
import { ref, onMounted } from 'vue'
import * as api from '../api.js'

const userPhoto = ref(null)
const uploading = ref(false)
const error = ref('')
const fileInput = ref(null)

const tryonRecords = ref([])
const recordsLoading = ref(false)

onMounted(async () => {
  try {
    userPhoto.value = await api.getUserPhoto()
  } catch {
    // 尚未上传，正常
  }
  loadRecords()
})

async function loadRecords() {
  recordsLoading.value = true
  try {
    tryonRecords.value = await api.getTryOnRecords()
  } catch {
    // ignore
  } finally {
    recordsLoading.value = false
  }
}

async function deleteRecord(recordId) {
  try {
    await api.deleteTryOnRecord(recordId)
    tryonRecords.value = tryonRecords.value.filter(r => r.id !== recordId)
  } catch {
    // ignore
  }
}

function formatDate(ts) {
  const d = new Date(ts)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const res = await api.uploadUserPhoto(file)
    userPhoto.value = res.photo
  } catch (err) {
    error.value = err.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

function retake() {
  userPhoto.value = null
}
</script>

<template>
  <div class="page">
    <h1 class="title">我的</h1>

    <div class="section">
      <h3>AI 试穿底图</h3>
      <p class="hint">上传一张您的全身正面照，用于 AI 试穿效果生成。建议在光线充足的纯色背景前拍摄。</p>

      <!-- 已有照片 -->
      <div v-if="userPhoto" class="photo-card">
        <img :src="userPhoto.url" alt="全身照" class="photo-preview" />
        <div class="photo-actions">
          <span class="photo-time">上传于 {{ new Date(userPhoto.createdAt).toLocaleDateString() }}</span>
          <button class="btn outline" @click="retake">重新上传</button>
        </div>
      </div>

      <!-- 上传区域 -->
      <div v-else class="upload-zone" @click="triggerUpload">
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          class="hidden-input"
          @change="handleFile"
        />
        <div v-if="uploading" class="up-loading">上传中…</div>
        <template v-else>
          <div class="up-icon">📷</div>
          <div class="up-text">点击上传全身正面照</div>
          <div class="up-sub">支持 JPG、PNG、WebP</div>
        </template>
      </div>

      <div v-if="error" class="error">⚠️ {{ error }}</div>
    </div>

    <!-- 试穿记录 -->
    <div class="section records-section">
      <h3>我的试穿记录</h3>
      <div v-if="recordsLoading" class="records-loading">加载中…</div>
      <div v-else-if="tryonRecords.length === 0" class="records-empty">
        <div class="empty-icon">👔</div>
        <div>暂无保存的试穿搭配</div>
        <div class="empty-sub">在 AI 试穿页面生成效果后可保存到这里</div>
      </div>
      <div v-else class="records-list">
        <div v-for="rec in tryonRecords" :key="rec.id" class="record-card">
          <img :src="rec.resultUrl" class="record-img" alt="试穿效果" />
          <div class="record-info">
            <div class="record-date">{{ formatDate(rec.createdAt) }}</div>
            <div class="record-items">
              <span v-for="it in rec.items" :key="it.id" class="record-tag">{{ it.name || it.category }}</span>
            </div>
          </div>
          <button class="record-del" @click="deleteRecord(rec.id)" title="删除">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 0 4px; }
.title { font-size: 22px; margin: 0 0 18px; }

.section {
  background: #fff;
  border-radius: 14px;
  padding: 18px;
  border: 1px solid var(--line, #e8ecf1);
}
.section h3 { margin: 0 0 6px; font-size: 16px; }
.hint { margin: 0 0 14px; color: var(--muted, #93a0b2); font-size: 13px; line-height: 1.5; }

.photo-card {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--line, #e8ecf1);
}
.photo-preview {
  width: 100%;
  max-height: 320px;
  object-fit: cover;
  display: block;
}
.photo-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
}
.photo-time { font-size: 12px; color: var(--muted, #93a0b2); }

.btn.outline {
  height: 32px;
  border: 1px solid var(--line, #dde);
  background: #fff;
  border-radius: 8px;
  padding: 0 14px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink, #1a2b3c);
}
.btn.outline:hover { background: #f5f7fa; }

.upload-zone {
  border: 2px dashed var(--line, #dde);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color .2s;
}
.upload-zone:hover { border-color: var(--accent, #5b7fff); }
.up-icon { font-size: 40px; margin-bottom: 8px; }
.up-text { font-size: 15px; color: var(--ink, #1a2b3c); }
.up-sub { font-size: 12px; color: var(--muted, #93a0b2); margin-top: 4px; }
.up-loading { padding: 20px; color: var(--muted, #93a0b2); }

.hidden-input { display: none; }
.error { color: #e23b3b; font-size: 13px; margin-top: 10px; }

/* 试穿记录 */
.records-section { margin-top: 14px; }
.records-loading { padding: 20px; text-align: center; color: var(--muted, #93a0b2); font-size: 13px; }
.records-empty { text-align: center; padding: 30px 0; }
.empty-icon { font-size: 36px; margin-bottom: 8px; }
.records-empty > div:nth-child(2) { font-size: 14px; color: var(--ink, #1a2b3c); }
.empty-sub { font-size: 12px; color: var(--muted, #93a0b2); margin-top: 4px; }
.records-list { display: flex; flex-direction: column; gap: 10px; margin-top: 10px; }
.record-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8f9fb;
  border-radius: 10px;
  padding: 10px;
  position: relative;
}
.record-img {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}
.record-info { flex: 1; min-width: 0; }
.record-date { font-size: 12px; color: var(--muted, #93a0b2); margin-bottom: 4px; }
.record-items { display: flex; flex-wrap: wrap; gap: 4px; }
.record-tag {
  font-size: 11px;
  background: #e8ecf1;
  color: var(--ink, #1a2b3c);
  padding: 2px 8px;
  border-radius: 6px;
}
.record-del {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border: none;
  background: rgba(0,0,0,.06);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
}
.record-del:hover { background: rgba(226,59,59,.1); color: #e23b3b; }
</style>
