<script setup>
import { useRoute } from 'vue-router'
import TabBar from './components/TabBar.vue'

const route = useRoute()
</script>

<template>
  <div class="app-shell">
    <main class="page">
      <RouterView />
    </main>
    <TabBar :current="route.meta.tab" />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding-bottom: 84px; /* 给底部 TabBar 留白 */
}
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}
</style>
