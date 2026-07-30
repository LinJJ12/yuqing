import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'overview',
    component: () => import('../pages/OverviewPage.vue'),
    meta: { title: '总览', subtitle: '帖子量 · 话题与情感快照' },
  },
  {
    path: '/monitor',
    name: 'monitor',
    component: () => import('../pages/MonitorPage.vue'),
    meta: { title: '舆情监测', subtitle: 'B 站评论采集 · 文件导入 · 浏览入库' },
  },
  {
    path: '/sentiment',
    name: 'sentiment',
    component: () => import('../pages/SentimentPage.vue'),
    meta: { title: '情感分析', subtitle: '正面 / 中性 / 负面' },
  },
  {
    path: '/topics',
    name: 'topics',
    component: () => import('../pages/TopicsPage.vue'),
    meta: { title: '热点话题', subtitle: '词云 · 关键词 · 主题聚类' },
  },
  {
    path: '/alerts',
    name: 'alerts',
    component: () => import('../pages/AlertsPage.vue'),
    meta: { title: '预警中心', subtitle: '负面/敏感词 · 热度突增' },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('../pages/ReportsPage.vue'),
    meta: { title: '分析报告', subtitle: '全局汇总 · 单视频口碑' },
  },
  {
    path: '/agent',
    name: 'agent',
    component: () => import('../pages/AgentPage.vue'),
    meta: { title: '智能助手', subtitle: '全局问答 · 单视频观众反馈' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
    meta: { title: '系统设置', subtitle: '就绪检查 · 敏感词 · 设备信息' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
