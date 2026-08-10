<template>
  <div class="page">
    <div class="toolbar">
      <input v-model="keyword" class="search" placeholder="按昵称 / openid 搜索" @keyup.enter="onSearch" />
      <button class="btn" @click="onSearch">搜索</button>
      <button class="btn ghost" @click="reset">重置</button>
    </div>

    <div class="table-card">
      <table class="table">
        <thead>
          <tr>
            <th style="width: 80px">头像</th>
            <th>昵称</th>
            <th>openid</th>
            <th>注册时间</th>
            <th>最近活跃</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in list" :key="u.openid">
            <td><img class="thumb" :src="fix(u.avatar)" /></td>
            <td>{{ u.nickname || '微信用户' }}</td>
            <td class="mono">{{ u.openid }}</td>
            <td>{{ fmtTime(u.createdAt) }}</td>
            <td>{{ fmtTime(u.updatedAt) }}</td>
          </tr>
          <tr v-if="!list.length">
            <td colspan="5" class="empty">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pager" v-if="total > size">
      <button class="page-btn" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span class="page-info">{{ page }} / {{ pages }}</span>
      <button class="page-btn" :disabled="page >= pages" @click="go(page + 1)">下一页</button>
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

const pages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

async function load() {
  const res = await adminApi.users(page.value, size.value, keyword.value)
  list.value = res.list || []
  total.value = res.total || 0
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

onMounted(load)
</script>

<style scoped>
@import './table.css';
</style>
