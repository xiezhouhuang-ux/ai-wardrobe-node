<template>
  <div class="page">
    <div class="table-card">
      <table class="table">
        <thead>
          <tr>
            <th>日期</th>
            <th>用户</th>
            <th>搭配单品</th>
            <th>备注</th>
            <th style="width: 100px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in list" :key="o.date">
            <td>{{ o.date }}</td>
            <td class="mono">{{ o.openid }}</td>
            <td>
              <span v-for="it in o.items || []" :key="it.id" class="chip">
                {{ it.name || it.category }}
              </span>
              <span v-if="!o.items || !o.items.length">-</span>
            </td>
            <td>{{ o.note || '-' }}</td>
            <td>
              <button class="link danger" @click="remove(o)">删除</button>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '../api'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)

const pages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

async function load() {
  const res = await adminApi.outfits(page.value, size.value)
  list.value = res.list || []
  total.value = res.total || 0
}

function go(p) {
  if (p < 1 || p > pages.value) return
  page.value = p
  load()
}

async function remove(o) {
  if (!confirm(`确认删除 ${o.date} 的搭配？`)) return
  try {
    await adminApi.deleteOutfit(o.date)
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
</style>
