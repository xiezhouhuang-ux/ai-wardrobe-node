<script setup>
import { useRouter } from 'vue-router'

defineProps({
  current: { type: String, default: '' },
})

const router = useRouter()

const tabs = [
  { key: 'home', to: '/', icon: '🏠', label: '衣橱' },
  { key: 'calendar', to: '/calendar', icon: '📅', label: '日历' },
  { key: 'tryon', to: '/tryon', icon: '🪄', label: 'AI试穿' },
  { key: 'me', to: '/me', icon: '👤', label: '我的' },
]
</script>

<template>
  <nav class="tabbar">
    <RouterLink
      v-for="t in tabs.slice(0, 2)"
      :key="t.key"
      :to="t.to"
      class="tab"
      :class="{ active: current === t.key }"
    >
      <span class="ico">{{ t.icon }}</span>
      <span class="lbl">{{ t.label }}</span>
    </RouterLink>

    <!-- 中间悬浮上传按钮 -->
    <RouterLink to="/upload" class="fab" :class="{ active: current === 'upload' }" title="上传识别">
      <span class="plus">＋</span>
    </RouterLink>

    <RouterLink
      v-for="t in tabs.slice(2)"
      :key="t.key"
      :to="t.to"
      class="tab"
      :class="{ active: current === t.key }"
    >
      <span class="ico">{{ t.icon }}</span>
      <span class="lbl">{{ t.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  border-top: 1px solid var(--line);
  box-shadow: 0 -4px 16px rgba(20, 30, 60, .06);
  z-index: 40;
}
.tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  color: var(--muted);
  text-decoration: none;
  font-size: 12px;
}
.tab.active { color: var(--accent); }
.tab .ico { font-size: 20px; }
.fab {
  width: 56px; height: 56px;
  margin-top: -28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b8cff, #9d6bff);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; font-weight: 300;
  box-shadow: 0 8px 20px rgba(91, 140, 255, .45);
  text-decoration: none;
}
.fab.active { box-shadow: 0 0 0 4px var(--accent-soft); }
</style>
