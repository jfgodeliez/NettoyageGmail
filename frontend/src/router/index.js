import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import GroupDetail from '../views/GroupDetail.vue'
import Review from '../views/Review.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/groups/:id', component: GroupDetail },
    { path: '/review', component: Review },
  ],
})
