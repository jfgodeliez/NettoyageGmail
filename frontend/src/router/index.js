import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import GroupDetail from '../views/GroupDetail.vue'
import Review from '../views/Review.vue'

const routes = [
  { path: '/login', component: Login, meta: { public: true } },
  { path: '/', component: Dashboard },
  { path: '/groups/:id', component: GroupDetail },
  { path: '/review', component: Review },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  try {
    const { data } = await axios.get('/auth/app-status', { withCredentials: true })
    if (!data.authenticated) return '/login'
  } catch {
    return '/login'
  }
  return true
})

export default router
