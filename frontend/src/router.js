import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './pages/HomePage.vue'
import UploadPage from './pages/UploadPage.vue'
import ConfirmPage from './pages/ConfirmPage.vue'
import PreviewPage from './pages/PreviewPage.vue'
import ItemDetailPage from './pages/ItemDetailPage.vue'
import CalendarPage from './pages/CalendarPage.vue'
import TryonPage from './pages/TryonPage.vue'
import MePage from './pages/MePage.vue'

const routes = [
  { path: '/', name: 'home', component: HomePage, meta: { tab: 'home' } },
  { path: '/upload', name: 'upload', component: UploadPage, meta: { tab: 'upload' } },
  { path: '/confirm', name: 'confirm', component: ConfirmPage, meta: { tab: 'upload' } },
  { path: '/preview', name: 'preview', component: PreviewPage, meta: { tab: 'upload' } },
  { path: '/item/:id', name: 'item', component: ItemDetailPage, meta: { tab: 'home' } },
  { path: '/calendar', name: 'calendar', component: CalendarPage, meta: { tab: 'calendar' } },
  { path: '/tryon', name: 'tryon', component: TryonPage, meta: { tab: 'tryon' } },
  { path: '/me', name: 'me', component: MePage, meta: { tab: 'me' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
