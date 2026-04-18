import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/chat',
      children: [
        {
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/ChatView.vue'),
          meta: { title: '智能问答', icon: 'ChatDotRound' }
        },
        {
          path: 'documents',
          name: 'Documents',
          component: () => import('@/views/DocumentsView.vue'),
          meta: { title: '知识库管理', icon: 'Document' }
        },
        {
          path: 'interview',
          name: 'Interview',
          component: () => import('@/views/InterviewView.vue'),
          meta: { title: '模拟面试', icon: 'User' }
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: '系统设置', icon: 'Setting' }
        }
      ]
    }
  ]
})

export default router
