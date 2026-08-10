<template>
  <div class="page">
    <div class="table-card">
      <table class="table">
        <thead>
          <tr>
            <th style="width: 120px">结果图</th>
            <th>单品</th>
            <th>用户</th>
            <th>创建时间</th>
            <th style="width: 100px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in list" :key="r.id">
            <td>
              <img class="thumb" :src="fix(r.resultUrl)" @click="preview(r.resultUrl)" />
            </td>
            <td>
              <span v-for="it in r.items || []" :key="it.id" class="chip">
                {{ it.name || it.category }}
              </span>
              <span v-if="!r.items || !r.items.length">-</span>
            </td>
            <td class="mono">{{ r.openid }}</td>
            <td>{{ fmtTime(r.createdAt) }}</td>
            <td>
              <button class="link danger" @click="remove(r)">删除</button>
            </td>
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

    <div v-if="previewUrl" class="mask" @click="previewUrl = ''">
      <img class="big" :src="fix(previewUrl)" />
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
const previewUrl = ref('')

const pages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

async function load() {
  const res = await adminApi.tryon(page.value, size.value)
  list.value = res.list || []
  total.value = res.total || 0
}

function go(p) {
  if (p < 1 || p > pages.value) return
  page.value = p
  load()
}

function preview(url) {
  if (url) previewUrl.value = url
}

async function remove(r) {
  if (!confirm('确认删除该试穿记录？')) return
  try {
    await adminApi.deleteTryon(r.id)
    load()
  } catch (e) {
    alert(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
@import './table.css';
.chip {
  display: inline-block;
  background: #f0f5ff;
  color: var(--primary);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  margin-right: 6px;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.big {
  max-width: 90%;
  max-height: 90%;
  border-radius: 8px;
}
</style>
