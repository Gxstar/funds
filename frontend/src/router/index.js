import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import FundDetailView from '@/views/FundDetailView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/fund/:code',
      name: 'fund-detail',
      component: FundDetailView,
      props: true
    }
  ],
})

export default router