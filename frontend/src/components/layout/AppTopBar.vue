<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { RefreshCw } from '@lucide/vue'

defineProps({
  backendOk: { type: Boolean, default: null },
  refreshing: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh'])

const route = useRoute()
const title = computed(() => route.meta.title || '舆情分析')
</script>

<template>
  <header class="topbar">
    <div class="title-wrap">
      <p class="eyebrow">Yuqing Workspace</p>
      <h1 class="title">{{ title }}</h1>
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
        {{ backendOk === true ? '服务正常' : backendOk === false ? '服务离线' : '检测中' }}
      </span>
      <button
        type="button"
        class="btn btn-ghost btn-icon"
        aria-label="刷新连接状态"
        :disabled="refreshing"
        @click="emit('refresh')"
      >
        <RefreshCw :size="16" :class="{ spin: refreshing }" />
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
  padding: 0 1.6rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px);
}
.title-wrap {
  min-width: 0;
}
.eyebrow {
  margin: 0 0 0.1rem;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.title {
  margin: 0;
  min-width: 0;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
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
