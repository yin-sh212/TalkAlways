import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/Overview'  // 根路径重定向到 Overview
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path:'/Overview',
    name: 'Overview',
    component: () => import('@/views/Overview.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
    meta: { requiresAuth: true, keepAlive: true }
  },
  {
   path: '/alarm',
   name: 'Alarm',
   component: () => import('@/views/Alarm.vue'),
   meta: { requiresAuth: true, keepAlive: true }
  },
  {
   path: '/workspace',
   name: 'Workspace',
   component: () => import('@/views/Workspace.vue'),
   meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  const token = userStore.token

  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login' })
  }
  else if (to.name === 'Login' && token) {
    next({ name: 'Home' })
  }
  else {
    next()
  }
})

export default router
