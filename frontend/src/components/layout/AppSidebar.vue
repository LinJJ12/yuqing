<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Radar,
  HeartPulse,
  Hash,
  BellRing,
  FileText,
  Bot,
  Settings,
  ChevronsLeft,
  ChevronsRight,
} from '@lucide/vue'

const route = useRoute()
const collapsed = ref(false)

const nav = [
  { to: '/', label: '总览', icon: LayoutDashboard, exact: true },
  { to: '/monitor', label: '监测', icon: Radar },
  { to: '/sentiment', label: '情感', icon: HeartPulse },
  { to: '/topics', label: '话题', icon: Hash },
  { to: '/alerts', label: '预警', icon: BellRing },
  { to: '/reports', label: '报告', icon: FileText },
  { to: '/agent', label: '助手', icon: Bot },
  { to: '/settings', label: '设置', icon: Settings },
]

function isActive(item) {
  if (item.exact) return route.path === '/'
  return route.path === item.to || route.path.startsWith(`${item.to}/`)
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">舆</div>
      <div v-show="!collapsed" class="brand-text">
        <strong>Yuqing</strong>
        <small>观众反馈分析</small>
      </div>
    </div>

    <nav class="nav" aria-label="主导航">
      <RouterLink
        v-for="item in nav"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item) }"
        :title="collapsed ? item.label : undefined"
      >
        <component :is="item.icon" :size="18" :stroke-width="1.75" class="nav-icon" />
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-foot">
      <button
        type="button"
        class="btn btn-ghost btn-sm collapse-btn"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        @click="collapsed = !collapsed"
      >
        <ChevronsLeft v-if="!collapsed" :size="16" />
        <ChevronsRight v-else :size="16" />
        <span v-show="!collapsed">收起</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid var(--color-border);
  background: #fff;
}
.sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}
.brand {
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 1rem;
  border-bottom: 1px solid var(--color-border);
  overflow: hidden;
}
.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: #fff;
  font-weight: 800;
  font-size: 0.85rem;
  line-height: 1;
  background: linear-gradient(145deg, #14b8a6 0%, #0f766e 75%);
}
.brand-text {
  min-width: 0;
  line-height: 1.15;
}
.brand-text strong {
  display: block;
  font-size: 0.9375rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  white-space: nowrap;
}
.brand-text small {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.nav {
  flex: 1;
  min-height: 0;
  padding: 0.75rem 0.6rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  height: 38px;
  padding: 0 0.75rem;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 120ms, color 120ms;
  cursor: pointer;
}
.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.nav-item.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: 650;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 1px;
  background: var(--color-primary);
}
.nav-icon {
  flex-shrink: 0;
  display: block;
}
.nav-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1;
  font-size: 0.875rem;
}
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}
.sidebar.collapsed .nav-item.active::before {
  display: none;
}
.sidebar-foot {
  padding: 0.55rem;
  border-top: 1px solid var(--color-border);
}
.collapse-btn {
  width: 100%;
  justify-content: center;
  border-radius: var(--radius-md);
}

@media (max-width: 800px) {
  .sidebar {
    width: 100% !important;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
  .nav {
    flex-direction: row;
    flex-wrap: wrap;
    overflow: visible;
  }
  .nav-item {
    flex: 0 0 auto;
  }
  .nav-item.active::before {
    display: none;
  }
  .sidebar.collapsed .nav-item {
    padding: 0 0.75rem;
  }
  .collapse-btn {
    display: none;
  }
}
</style>
