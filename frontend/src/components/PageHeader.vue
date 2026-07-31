<script setup>
defineProps({
  /** 与顶栏重复时可省略，仅保留操作区 */
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <header v-if="title || $slots.actions" class="page-header" :class="{ 'actions-only': !title }">
    <div v-if="title" class="page-header-text">
      <h2 class="page-header-title">{{ title }}</h2>
      <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>
