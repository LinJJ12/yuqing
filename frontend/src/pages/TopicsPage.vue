<script setup>
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Cloud, ListTree } from '@lucide/vue'
import { fetchWordCloud, runTopics } from '../api/client'

const loading = ref(false)
const message = ref('')
const error = ref('')
const result = ref(null)
const cloudRef = ref(null)
let chart

function renderCloud(words) {
  if (!cloudRef.value) return
  if (!chart) chart = echarts.init(cloudRef.value)
  const palette = ['#1e40af', '#3b82f6', '#059669', '#d97706', '#64748b']
  chart.setOption({
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        data: (words || []).slice(0, 30).map((w, i) => ({
          name: w.name,
          value: w.value,
          symbolSize: Math.max(18, Math.min(70, w.value * 6)),
          category: 0,
          itemStyle: { color: palette[i % palette.length] },
        })),
        categories: [{ name: '词' }],
        label: { show: true, color: '#0f172a' },
        force: { repulsion: 80, edgeLength: 40 },
        lineStyle: { opacity: 0 },
      },
    ],
  })
}

async function loadWords() {
  const res = await fetchWordCloud(40)
  if (res.ok) {
    result.value = {
      ...(result.value || {}),
      word_cloud: res.data.word_cloud,
      document_count: res.data.document_count,
    }
    await nextTick()
    renderCloud(res.data.word_cloud)
  }
}

async function onRun(useBertopic = true) {
  loading.value = true
  error.value = ''
  message.value = useBertopic
    ? '正在提取词频并做主题聚类…'
    : '正在提取词频 / 关键词…'
  try {
    const res = await runTopics({ limit: 2000, use_bertopic: useBertopic })
    if (!res.ok) {
      error.value = res.error?.message || '主题分析失败'
      return
    }
    result.value = res.data
    message.value = `完成：文档 ${res.data.document_count} 条，耗时 ${res.data.elapsed_ms} ms`
    if (res.data.bertopic_error) {
      message.value += '（主题聚类已回退到词频）'
    }
    await nextTick()
    renderCloud(res.data.word_cloud)
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await loadWords()
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', () => chart?.resize())
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>热点话题</h2>
      </div>
      <p class="hint">词频词云 + 关键词提取；可选主题聚类。数据不足时会自动回退到词频。</p>
      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="loading" @click="onRun(true)">
          <Cloud :size="16" />
          词频 + 主题聚类
        </button>
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="onRun(false)">
          <ListTree :size="16" />
          仅词频
        </button>
      </div>
      <p v-if="message" class="ok-text">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <div ref="cloudRef" class="chart-box cloud" />
    </section>

    <div v-if="result" class="topic-cols">
      <section class="panel">
        <div class="panel-head"><h3>TF-IDF 关键词</h3></div>
        <ul class="stack-list">
          <li v-for="item in result.keywords || []" :key="item.topic">
            <span>{{ item.topic }}</span>
            <b>{{ item.weight }}</b>
          </li>
        </ul>
        <p v-if="!(result.keywords || []).length" class="hint">暂无</p>
      </section>

      <section class="panel">
        <div class="panel-head"><h3>主题聚类</h3></div>
        <article v-for="item in result.bertopic || []" :key="item.topic_id" class="topic-card">
          <header>
            <b>{{ item.label }}</b>
            <span class="pill pill-default">{{ item.count }} 条</span>
          </header>
          <p>{{ (item.keywords || []).join(' · ') }}</p>
        </article>
        <p v-if="!(result.bertopic || []).length" class="hint">尚未生成或数据不足</p>
      </section>

      <section class="panel">
        <div class="panel-head"><h3>库内话题标签</h3></div>
        <ul class="stack-list">
          <li v-for="item in result.db_topics || []" :key="item.topic">
            <span>{{ item.topic }}</span>
            <b>{{ item.count }}</b>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 0.6rem;
  margin: 0.85rem 0;
  flex-wrap: wrap;
}
.cloud {
  height: 320px;
  margin-top: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}
.topic-cols {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}
.topic-card {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--bg-tertiary);
}
.topic-card:last-child {
  border-bottom: none;
}
.topic-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: center;
}
.topic-card p {
  margin: 0.35rem 0 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
@media (max-width: 1000px) {
  .topic-cols {
    grid-template-columns: 1fr;
  }
}
</style>
