import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      children: [
        { path: '', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
        { path: 'devices', name: 'Devices', component: () => import('@/views/DeviceList.vue') },
        { path: 'devices/:id', name: 'DeviceDetail', component: () => import('@/views/DeviceDetail.vue') },
        { path: 'reservations', name: 'Reservations', component: () => import('@/views/ReservationList.vue') },
        { path: 'jobs', name: 'Jobs', component: () => import('@/views/JobList.vue') },
        { path: 'jobs/create', name: 'JobCreate', component: () => import('@/views/JobCreate.vue') },
        { path: 'jobs/:id', name: 'JobDetail', component: () => import('@/views/JobDetail.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'Login' }
  }
})

export default router
