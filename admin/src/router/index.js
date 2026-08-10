import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layout/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '概览' } },
      { path: 'items', name: 'items', component: () => import('../views/Items.vue'), meta: { title: '单品管理' } },
      { path: 'tryon', name: 'tryon', component: () => import('../views/Tryon.vue'), meta: { title: '试穿记录' } },
      { path: 'outfits', name: 'outfits', component: () => import('../views/Outfits.vue'), meta: { title: '搭配/日历' } },
      { path: 'users', name: 'users', component: () => import('../views/Users.vue'), meta: { title: '用户管理' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('admin_token')
  if (!to.meta.public && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }
})

export default router
