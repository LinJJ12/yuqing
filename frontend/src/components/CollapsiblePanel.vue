<script setup>
import { ref, watch, nextTick } from 'vue'
import { ChevronDown } from '@lucide/vue'

const props = defineProps({
  title: { type: String, required: true },
  defaultOpen: { type: Boolean, default: false },
  storageKey: { type: String, default: '' },
})

const emit = defineEmits(['toggle'])

function readOpen() {
  if (!props.storageKey) return props.defaultOpen
  try {
    const raw = localStorage.getItem(props.storageKey)
    if (raw === '1') return true
    if (raw === '0') return false
  } catch {
    /* ignore */
  }
  return props.defaultOpen
}

const open = ref(readOpen())

watch(open, async (value) => {
  if (props.storageKey) {
    try {
      localStorage.setItem(props.storageKey, value ? '1' : '0')
    } catch {
      /* ignore */
    }
  }
  await nextTick()
  emit('toggle', value)
})

function toggle() {
  open.value = !open.value
}
</script>

<template>
  <section class="panel is-collapsible" :class="{ 'is-collapsed': !open }">
    <div class="panel-head collapsible-head">
      <button type="button" class="collapse-toggle" :aria-expanded="open" @click="toggle">
        <span class="collapse-title">{{ title }}</span>
        <slot name="badge" />
        <ChevronDown :size="16" class="collapse-chevron" :class="{ open }" />
      </button>
      <div v-if="$slots.actions && open" class="collapse-actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-show="open" class="collapse-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.collapsible-head {
  margin-bottom: 0;
}
.collapse-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  text-align: left;
}
.collapse-title {
  font-size: 0.9375rem;
  font-weight: 650;
  color: var(--text-primary);
}
.collapse-chevron {
  color: var(--text-tertiary);
  transition: transform 160ms var(--ease-out);
  flex-shrink: 0;
}
.collapse-chevron.open {
  transform: rotate(180deg);
}
.collapse-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}
.collapse-body {
  margin-top: 0.75rem;
}
.is-collapsed {
  padding-top: 0.7rem;
  padding-bottom: 0.7rem;
}
</style>
