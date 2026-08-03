<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { LogOut, RefreshCw } from '@lucide/vue'

defineProps({
  backendOk: { type: Boolean, default: null },
  refreshing: { type: Boolean, default: false },
  username: { type: String, default: '' },
  loggingOut: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh', 'logout'])

const route = useRoute()
const title = computed(() => route.meta.title || '知微')
const subtitle = computed(() => route.meta.subtitle || '')
</script>

<template>
  <header class="topbar">
    <div class="title-wrap">
      <div class="crumb">
        <span class="crumb-root">知微</span>
        <span class="crumb-sep" aria-hidden="true">/</span>
        <span class="crumb-current">{{ title }}</span>
      </div>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
    <div class="actions">
      <span
        class="pill"
        :class="
          backendOk === true
            ? 'pill-success'
            : backendOk === false
              ? 'pill-danger'
              : 'pill-warning'
        "
      >
        <span class="dot" aria-hidden="true" />
        {{ backendOk === true ? '服务正常' : backendOk === false ? '服务离线' : '检测中' }}
      </span>
      <span v-if="username" class="user-chip" :title="username">{{ username }}</span>
      <button
        type="button"
        class="btn btn-ghost btn-icon"
        aria-label="刷新连接状态"
        :disabled="refreshing"
        @click="emit('refresh')"
      >
        <RefreshCw :size="15" :class="{ spin: refreshing }" />
      </button>
      <button
        type="button"
        class="btn btn-ghost btn-sm logout-btn"
        :disabled="loggingOut"
        @click="emit('logout')"
      >
        <LogOut :size="14" />
        <span>{{ loggingOut ? '退出中' : '退出' }}</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  height: var(--topbar-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
}
.title-wrap {
  min-width: 0;
}
.crumb {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
  font-size: 0.875rem;
  line-height: 1.2;
}
.crumb-root {
  color: var(--text-tertiary);
  font-weight: 500;
}
.crumb-sep {
  color: var(--color-border-strong);
}
.crumb-current {
  color: var(--text-primary);
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.subtitle {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}
.user-chip {
  max-width: 7rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
}
.logout-btn {
  gap: 0.35rem;
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
