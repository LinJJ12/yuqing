<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  source: { type: String, default: '' },
})

marked.setOptions({
  gfm: true,
  breaks: true,
})

const html = computed(() => {
  const raw = props.source?.trim()
  if (!raw) return ''
  const parsed = marked.parse(raw, { async: false })
  return DOMPurify.sanitize(parsed, {
    USE_PROFILES: { html: true },
  })
})
</script>

<template>
  <div class="md-content" v-html="html" />
</template>

<style scoped>
.md-content {
  line-height: 1.65;
  color: var(--text-primary);
  word-break: break-word;
}

.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: 1.1em 0 0.45em;
  font-weight: 600;
  line-height: 1.35;
  color: var(--text-primary);
}

.md-content :deep(h1) {
  font-size: 1.25rem;
}
.md-content :deep(h2) {
  font-size: 1.12rem;
}
.md-content :deep(h3) {
  font-size: 1.02rem;
}
.md-content :deep(h4) {
  font-size: 0.95rem;
}

.md-content :deep(p) {
  margin: 0.55em 0;
}

.md-content :deep(ul),
.md-content :deep(ol) {
  margin: 0.45em 0;
  padding-left: 1.35em;
}

.md-content :deep(li) {
  margin: 0.25em 0;
}

.md-content :deep(li > p) {
  margin: 0.2em 0;
}

.md-content :deep(strong) {
  font-weight: 600;
}

.md-content :deep(hr) {
  margin: 1em 0;
  border: none;
  border-top: 1px solid var(--color-border);
}

.md-content :deep(blockquote) {
  margin: 0.65em 0;
  padding: 0.15em 0 0.15em 0.85em;
  border-left: 3px solid var(--color-border-strong);
  color: var(--text-secondary);
}

.md-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.88em;
  padding: 0.1em 0.35em;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
}

.md-content :deep(pre) {
  margin: 0.65em 0;
  padding: 0.75rem 0.85rem;
  overflow-x: auto;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  border: 1px solid var(--color-border);
}

.md-content :deep(pre code) {
  padding: 0;
  background: transparent;
}

.md-content :deep(a) {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.md-content :deep(table) {
  width: 100%;
  margin: 0.65em 0;
  border-collapse: collapse;
  font-size: 0.92em;
}

.md-content :deep(th),
.md-content :deep(td) {
  padding: 0.4em 0.55em;
  border: 1px solid var(--color-border);
  text-align: left;
}

.md-content :deep(th) {
  background: var(--bg-tertiary);
  font-weight: 600;
}

.md-content :deep(> :first-child) {
  margin-top: 0;
}

.md-content :deep(> :last-child) {
  margin-bottom: 0;
}
</style>
