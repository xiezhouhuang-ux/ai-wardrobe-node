<template>
  <div class="layout">
    <aside class="sider">
      <div class="logo">AI 衣橱 · 后台</div>
      <nav class="menu">
        <router-link to="/dashboard" class="menu-item">
          <span class="ico">▦</span> 数据概览
        </router-link>
        <router-link to="/items" class="menu-item">
          <span class="ico">▤</span> 单品管理
        </router-link>
        <router-link to="/tryon" class="menu-item">
          <span class="ico">◈</span> 试穿记录
        </router-link>
        <router-link to="/outfits" class="menu-item">
          <span class="ico">▥</span> 搭配 / 日历
        </router-link>
        <router-link to="/users" class="menu-item">
          <span class="ico">☺</span> 用户管理
        </router-link>
      </nav>
    </aside>
    <section class="main">
      <header class="topbar">
        <div class="crumb">{{ currentTitle }}</div>
        <div class="user">
          <span class="dot"></span> 管理员
          <button class="logout" @click="logout">退出</button>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const currentTitle = computed(() => route.meta.title || '后台管理')

function logout() {
  localStorage.removeItem('admin_token')
  router.push('/login')
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}
.sider {
  width: 220px;
  background: var(--sider);
  color: #fff;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.menu {
  padding: 12px 0;
  flex: 1;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  color: rgba(255, 255, 255, 0.75);
  transition: all 0.2s;
}
.menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.menu-item.router-link-active {
  background: var(--primary);
  color: #fff;
}
.ico {
  width: 18px;
  text-align: center;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.crumb {
  font-size: 16px;
  font-weight: 500;
}
.user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-2);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #52c41a;
}
.logout {
  margin-left: 8px;
  border: 1px solid var(--border);
  background: #fff;
  padding: 4px 12px;
  border-radius: 4px;
}
.logout:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}
</style>
