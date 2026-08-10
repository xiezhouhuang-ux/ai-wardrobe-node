<template>
  <div class="dashboard">
    <div class="cards">
      <div class="stat" v-for="c in cards" :key="c.key">
        <div class="stat-label">{{ c.label }}</div>
        <div class="stat-value">{{ c.value }}</div>
      </div>
    </div>
    <div class="panel">
      <h3>欢迎使用 AI 衣橱后台</h3>
      <p>左侧菜单可管理全部用户的衣橱单品、AI 试穿记录与搭配日历。</p>
      <ul>
        <li><b>单品管理</b>：查看 / 搜索 / 删除所有用户的服装单品。</li>
        <li><b>试穿记录</b>：查看所有用户的 AI 试穿结果图。</li>
        <li><b>搭配 / 日历</b>：查看用户的每日穿搭安排。</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '../api'

const stats = ref({ users: 0, items: 0, tryons: 0, outfits: 0 })
const loading = ref(false)

const cards = ref([])

function buildCards() {
  cards.value = [
    { key: 'users', label: '用户数', value: stats.value.users },
    { key: 'items', label: '单品数', value: stats.value.items },
    { key: 'tryons', label: '试穿数', value: stats.value.tryons },
    { key: 'outfits', label: '搭配数', value: stats.value.outfits },
  ]
}

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await adminApi.stats()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
    buildCards()
  }
})
</script>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat {
  background: var(--card);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.stat-label {
  color: var(--text-2);
  font-size: 14px;
  margin-bottom: 12px;
}
.stat-value {
  font-size: 30px;
  font-weight: 600;
  color: var(--primary);
}
.panel {
  background: var(--card);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.panel h3 {
  margin-top: 0;
}
.panel li {
  margin-bottom: 8px;
  color: #595959;
}
</style>
