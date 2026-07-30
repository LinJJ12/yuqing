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
    meta: { title: '舆情监测', subtitle: '导入 JSON / CSV，浏览入库帖子' },
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
    meta: { title: '分析报告', subtitle: '一键汇总当前库内分析结果' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
    meta: { title: '系统设置', subtitle: '健康检查 · 模型与嵌入配置' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
