import { createRouter, createWebHashHistory } from 'vue-router'

/**
 * Electron 生产模式用 file:// 加载页面，必须用 hash 历史。
 * 登录通过主页左下角「登录」按钮弹出 Element Plus 弹窗完成，无需独立登录页。
 */
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('@/views/index.vue'),
    },
    {
      path: '/login',
      redirect: { name: 'chat' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: { name: 'chat' },
    },
  ],
})

export default router
