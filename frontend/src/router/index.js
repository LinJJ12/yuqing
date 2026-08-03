import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../lib/auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../pages/HomePage.vue'),
    meta: { layout: 'public', title: '知微' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../pages/LoginPage.vue'),
    meta: { layout: 'public', title: '登录' },
  },
  {
    path: '/overview',
    name: 'overview',
    component: () => import('../pages/OverviewPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '总览',
      subtitle: '帖子量 · 话题与情感快照',
    },
  },
  {
    path: '/monitor',
    name: 'monitor',
    component: () => import('../pages/MonitorPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '舆情监测',
      subtitle: 'B 站评论采集 · 文件导入',
    },
  },
  {
    path: '/inbox',
    name: 'inbox',
    component: () => import('../pages/InboxPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '入库浏览',
      subtitle: '按平台筛选 · 翻页查看',
    },
  },
  {
    path: '/insights',
    name: 'insights',
    component: () => import('../pages/InsightsPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '洞察',
      subtitle: '情感分布 · 词云话题 · 跑批',
    },
  },
  {
    path: '/sentiment',
    redirect: (to) => ({
      path: '/insights',
      query: { ...to.query, tab: 'sentiment' },
    }),
  },
  {
    path: '/topics',
    redirect: (to) => ({
      path: '/insights',
      query: { ...to.query, tab: 'topics' },
    }),
  },
  {
    path: '/alerts',
    name: 'alerts',
    component: () => import('../pages/AlertsPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '预警中心',
      subtitle: '预警列表 · 难例改判 · 热度趋势',
    },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('../pages/ReportsPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '分析报告',
      subtitle: '全局汇总 · 单视频口碑',
    },
  },
  {
    path: '/agent',
    name: 'agent',
    component: () => import('../pages/AgentPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '智能助手',
      subtitle: '全局问答 · 单视频观众反馈',
    },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
    meta: {
      layout: 'app',
      requiresAuth: true,
      title: '系统设置',
      subtitle: '就绪检查 · 敏感词 · 设备信息',
    },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const needsAuth = to.matched.some(
    (record) => record.meta.requiresAuth || record.meta.layout === 'app',
  )
  if (needsAuth && !isAuthenticated()) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
  if (to.name === 'login' && isAuthenticated()) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : ''
    // 仅允许站内相对路径，拒绝 //evil 协议相对 URL
    const safe =
      redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : ''
    return safe || '/overview'
  }
  return true
})
