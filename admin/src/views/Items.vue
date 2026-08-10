<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="keyword" class="search" placeholder="按名称 / 品类 / 颜色搜索" @keyup.enter="onSearch" />
      <button class="btn" @click="onSearch">搜索</button>
      <button class="btn ghost" @click="reset">重置</button>
    </div>

    <div class="table-card">
      <div v-if="loading" class="loading-mask">
        <span class="spinner"></span> 加载中…
      </div>
      <table class="table">
        <thead>
          <tr>
            <th style="width: 80px">图片</th>
            <th>名称</th>
            <th>品类</th>
            <th>颜色</th>
            <th>风格</th>
            <th>用户</th>
            <th>创建时间</th>
            <th style="width: 100px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in list" :key="it.id">
            <td><img class="thumb" :src="fix(it.imageUrl)" @click="preview(it)" style="cursor: pointer" /></td>
            <td>{{ it.name || '-' }}</td>
            <td>{{ it.category || '-' }}</td>
            <td>{{ it.color || '-' }}</td>
            <td>{{ it.style || '-' }}</td>
            <td class="mono">{{ it.openid }}</td>
            <td>{{ fmtTime(it.createdAt) }}</td>
            <td>
              <button class="link danger" @click="remove(it)">删除</button>
            </td>
          </tr>
          <tr v-if="!list.length">
            <td colspan="8" class="empty">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pager" v-if="total > size">
      <button class="page-btn" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span class="page-info">{{ page }} / {{ pages }}</span>
      <button class="page-btn" :disabled="page >= pages" @click="go(page + 1)">下一页</button>
    </div>

    <div v-if="previewUrl" class="lightbox" @click="closePreview">
      <img class="lightbox-img" :src="previewUrl" @click.stop />
      <button class="lightbox-close" @click="closePreview">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '../api'
import { fix, fmtTime } from '../utils/img'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const keyword = ref('')
const loading = ref(false)
const previewUrl = ref('')

const pages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

async function load() {
  loading.value = true
  try {
    const res = await adminApi.items(page.value, size.value, keyword.value)
    list.value = res.list || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

function preview(it) {
  previewUrl.value = fix(it.imageUrl)
}

function closePreview() {
  previewUrl.value = ''
}

function go(p) {
  if (p < 1 || p > pages.value) return
  page.value = p
  load()
}

function onSearch() {
  page.value = 1
  load()
}

function reset() {
  keyword.value = ''
  page.value = 1
  load()
}

async function remove(it) {
  if (!confirm(`确认删除单品「${it.name || it.id}」？`)) return
  try {
    await adminApi.deleteItem(it.id)
    load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
@import './table.css';
</style>
