<script setup>
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Radar,
  Inbox,
  ScanSearch,
  BellRing,
  FileText,
  Bot,
  Settings,
  PanelLeftClose,
} from '@lucide/vue'
import logoUrl from '../../assets/logo.png'

const SIDEBAR_KEY = 'zhiwei.sidebar.collapsed'

function readCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === '1'
  } catch {
    return false
  }
}

const route = useRoute()
const collapsed = ref(readCollapsed())

watch(collapsed, (value) => {
  try {
    localStorage.setItem(SIDEBAR_KEY, value ? '1' : '0')
  } catch {
    /* ignore */
  }
})

const groups = [
  {
    label: '工作台',
    items: [
      { to: '/overview', label: '总览', icon: LayoutDashboard, exact: true },
      { to: '/reports', label: '报告', icon: FileText },
    ],
  },
  {
    label: '采集',
    items: [
      { to: '/monitor', label: '监测', icon: Radar },
      { to: '/inbox', label: '入库', icon: Inbox },
    ],
  },
  {
    label: '分析',
    items: [
      { to: '/insights', label: '洞察', icon: ScanSearch },
      { to: '/alerts', label: '预警', icon: BellRing },
    ],
  },
  {
    label: '工具',
    items: [
      { to: '/agent', label: '助手', icon: Bot },
      { to: '/settings', label: '设置', icon: Settings },
    ],
  },
]

function isActive(item) {
  if (item.exact) return route.path === item.to
  return route.path === item.to || route.path.startsWith(`${item.to}/`)
}
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div v-show="!collapsed" class="brand-main">
        <img class="brand-logo" :src="logoUrl" alt="知微" />
        <div class="brand-text">
          <strong>知微</strong>
          <small>舆情工作台</small>
        </div>
      </div>
      <button
        type="button"
        class="collapse-btn"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        :title="collapsed ? '展开菜单' : '收起菜单'"
        @click="collapsed = !collapsed"
      >
        <PanelLeftClose v-if="!collapsed" :size="16" :stroke-width="1.75" />
        <img v-else class="brand-logo brand-logo-sm" :src="logoUrl" alt="知微" />
      </button>
    </div>

    <nav class="nav" aria-label="主导航">
      <div v-for="group in groups" :key="group.label" class="nav-group">
        <div v-show="!collapsed" class="nav-group-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item) }"
          :title="collapsed ? item.label : undefined"
        >
          <component :is="item.icon" :size="17" :stroke-width="1.75" class="nav-icon" />
          <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  border-right: 1px solid var(--sidebar-border);
  transition: width 180ms var(--ease-out);
}
.sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}
.brand {
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  padding: 0 0.55rem 0 0.85rem;
  border-bottom: 1px solid var(--sidebar-border);
  overflow: hidden;
}
.brand-main {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
  overflow: hidden;
}
.brand-logo {
  height: 40px;
  width: auto;
  max-width: 118px;
  flex-shrink: 0;
  object-fit: contain;
  display: block;
}
.brand-logo-sm {
  height: 30px;
  width: auto;
  max-width: 36px;
}
.brand-text {
  min-width: 0;
  line-height: 1.15;
}
.brand-text strong {
  display: block;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--sidebar-text-active);
  white-space: nowrap;
}
.brand-text small {
  display: block;
  color: var(--sidebar-text);
  font-size: 0.65rem;
  font-weight: 500;
}
.collapse-btn {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: inline-grid;
  place-items: center;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--sidebar-text);
  cursor: pointer;
  padding: 0;
  transition: background 120ms, color 120ms;
}
.collapse-btn:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-active);
}
.sidebar.collapsed .brand {
  justify-content: center;
  padding: 0;
}
.sidebar.collapsed .collapse-btn:hover .brand-logo-sm {
  filter: brightness(1.05);
}

.nav {
  flex: 1;
  min-height: 0;
  padding: 0.75rem 0.55rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-group-label {
  padding: 0.1rem 0.65rem 0.3rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #94a3b8;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  height: 36px;
  padding: 0 0.65rem;
  border-radius: var(--radius-md);
  color: var(--sidebar-text);
  text-decoration: none;
  transition: background 120ms, color 120ms;
}
.nav-item:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-active);
}
.nav-item.active {
  background: var(--sidebar-active);
  color: var(--color-primary);
  font-weight: 600;
}
.nav-item.active .nav-icon {
  color: var(--color-primary);
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
  font-size: 0.875rem;
  line-height: 1;
}
.sidebar.collapsed .nav {
  padding: 0.55rem 0.4rem;
}
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

@media (max-width: 800px) {
  .sidebar {
    width: 100% !important;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--sidebar-border);
  }
  .brand {
    height: auto;
    min-height: 48px;
    padding: 0.5rem 0.85rem;
  }
  .collapse-btn {
    display: none;
  }
  .nav {
    flex-direction: row;
    flex-wrap: wrap;
    overflow: visible;
    gap: 0.35rem;
  }
  .nav-group {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .nav-group-label {
    display: none;
  }
  .nav-item {
    flex: 0 0 auto;
  }
  .sidebar.collapsed .nav-item {
    padding: 0 0.65rem;
  }
}
</style>
