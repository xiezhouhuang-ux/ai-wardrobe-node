<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import { session, resetSession } from '../session.js'

const router = useRouter()
const fileInput = ref(null)
const dragging = ref(false)
const loading = ref(false)
const error = ref('')

function pick() {
  fileInput.value?.click()
}

function onInputChange(e) {
  const f = e.target.files && e.target.files[0]
  if (f) run(f)
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer?.files && e.dataTransfer.files[0]
  if (f && f.type.startsWith('image/')) run(f)
}

async function run(file) {
  error.value = ''
  loading.value = true
  try {
    resetSession()
    const data = await api.analyzePhoto(file)
    session.photoId = data.photoId
    session.photoUrl = data.photoUrl
    session.candidates = data.candidates || []
    router.push('/confirm')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="upload-wrap">
    <h2 class="title">上传穿搭照片</h2>
    <p class="sub">上传后先用视觉模型分析出单品，确认后再分割入库</p>

    <div
      class="dropzone"
      :class="{ drag: dragging }"
      @click="pick"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <div class="dz-inner">
        <div class="dz-icon">📷</div>
        <div class="dz-title">点击或拖拽上传穿搭照片</div>
        <div class="dz-hint">支持 jpg / png / webp 等图片</div>
      </div>
      <input ref="fileInput" type="file" accept="image/*" hidden @change="onInputChange" />
    </div>

    <div v-if="loading" class="loading">正在用视觉模型分析单品…</div>
    <div v-if="error" class="error">⚠️ {{ error }}</div>
  </div>
</template>

<style scoped>
.upload-wrap { max-width: 640px; margin: 0 auto; }
.title { font-size: 20px; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 18px; font-size: 14px; }
.dropzone {
  border: 2px dashed var(--line); border-radius: 16px; padding: 48px;
  text-align: center; cursor: pointer; transition: .2s;
  background: linear-gradient(180deg, #fbfcff, #f6f8ff);
}
.dropzone:hover, .dropzone.drag { border-color: var(--accent); background: var(--accent-soft); }
.dz-icon { font-size: 38px; }
.dz-title { font-weight: 600; margin-top: 8px; }
.dz-hint { font-size: 13px; color: var(--muted); margin-top: 6px; }
.loading { margin-top: 16px; color: var(--accent); font-size: 14px; }
.error { margin-top: 16px; color: #e23b3b; font-size: 14px; }
</style>
