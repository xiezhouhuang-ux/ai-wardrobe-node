<script setup>
import { ref } from 'vue'
import { processPhotos } from '../api.js'

const emit = defineEmits(['processed'])

const fileInput = ref(null)
const dropzone = ref(null)
const dragging = ref(false)
const progress = ref({ visible: false, pct: 0, text: '' })

function pickFiles() {
  fileInput.value?.click()
}

function onInputChange(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) runUpload(files)
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  const files = Array.from(e.dataTransfer?.files || []).filter((f) => f.type.startsWith('image/'))
  if (files.length) runUpload(files)
}

async function runUpload(files) {
  progress.value = { visible: true, pct: 8, text: `正在上传 ${files.length} 张照片…` }
  try {
    const data = await processPhotos(files)
    let count = 0
    for (const p of data.result || []) count += (p.items || []).length
    progress.value = {
      visible: true,
      pct: 100,
      text: data.demoMode
        ? `demo 模式：已保存 ${files.length} 张原图（未调用识别模型）`
        : `已成功整理 ${count} 件单品，从 ${files.length} 张照片中`,
    }
    emit('processed', data)
    if (data.demoMode) {
      alert(`demo 模式：已保存 ${files.length} 张原图。配置 QWEN_API_KEY 后可启用自动识别与抠图。`)
    } else {
      alert(`已成功整理 ${count} 件单品 🎉`)
    }
  } catch (err) {
    progress.value = { visible: true, pct: 0, text: '处理失败：' + err.message }
    alert('处理失败：' + err.message)
  }
}
</script>

<template>
  <div
    ref="dropzone"
    class="dropzone"
    :class="{ drag: dragging }"
    @click="pickFiles"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <div class="dz-inner">
      <div class="dz-icon">📷</div>
      <div class="dz-title">点击或拖拽上传穿搭照片</div>
      <div class="dz-hint">支持多张 · 自动识别单品并整理入库</div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      multiple
      hidden
      @change="onInputChange"
    />
  </div>

  <div class="progress" :class="{ hidden: !progress.visible }">
    <div class="progress-bar"><div :style="{ width: progress.pct + '%' }"></div></div>
    <div id="progressText">{{ progress.text }}</div>
  </div>
</template>
