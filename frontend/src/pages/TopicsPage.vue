<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { Cloud, ListTree, RefreshCw } from '@lucide/vue'
import { fetchOverview, fetchWordCloud, runTopics } from '../api/client'

const loading = ref(false)
const message = ref('')
const error = ref('')
const result = ref(null)
const cloudRef = ref(null)
const rankRef = ref(null)
let cloudChart
let rankChart

const words = computed(() => result.value?.word_cloud || [])
const keywords = computed(() => result.value?.keywords || [])
const bertopic = computed(() => result.value?.bertopic || [])
const dbTopics = computed(() => result.value?.db_topics || [])
const docCount = computed(() => result.value?.document_count ?? 0)

const palette = [
  '#18181b',
  '#3f3f46',
  '#52525b',
  '#71717a',
  '#16a34a',
  '#dc2626',
  '#d97706',
  '#0f766e',
]

function colorFor(name) {
  let h = 0
  for (let i = 0; i < name.length; i += 1) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return palette[h % palette.length]
}

function renderWordCloud(list) {
  if (!cloudRef.value) return
  if (!cloudChart) cloudChart = echarts.init(cloudRef.value)
  const data = (list || []).slice(0, 60).map((w) => ({
    name: w.name,
    value: Number(w.value) || 1,
    textStyle: { color: colorFor(String(w.name || '')) },
  }))
  cloudChart.setOption(
    {
      tooltip: {
        show: true,
        formatter: (p) => `${p.name}<br/>频次 <b>${p.value}</b>`,
      },
      series: [
        {
          type: 'wordCloud',
          shape: 'circle',
          keepAspect: false,
          left: 'center',
          top: 'center',
          width: '94%',
          height: '92%',
          sizeRange: [14, 64],
          rotationRange: [-45, 45],
          rotationStep: 15,
          gridSize: 8,
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
            fontFamily: 'Plus Jakarta Sans, Noto Sans SC, sans-serif',
            fontWeight: 700,
          },
          emphasis: {
            focus: 'self',
            textStyle: {
              textShadowBlur: 8,
              textShadowColor: 'rgba(24, 24, 27, 0.25)',
            },
          },
          data,
        },
      ],
    },
    true,
  )
}

function renderRank(list) {
  if (!rankRef.value) return
  if (!rankChart) rankChart = echarts.init(rankRef.value)
  const top = (list || []).slice(0, 12)
  const names = top.map((w) => w.name).reverse()
  const values = top.map((w) => w.value).reverse()
  rankChart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          const p = params?.[0]
          return p ? `${p.name}<br/>频次 <b>${p.value}</b>` : ''
        },
      },
      grid: { left: 72, right: 28, top: 8, bottom: 8 },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f4f4f5' } },
        axisLabel: { color: '#a1a1aa' },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#3f3f46',
          fontWeight: 600,
          width: 60,
          overflow: 'truncate',
        },
      },
      series: [
        {
          type: 'bar',
          data: values,
          barMaxWidth: 14,
          itemStyle: {
            borderRadius: [0, 6, 6, 0],
            color: '#18181b',
          },
          label: {
            show: true,
            position: 'right',
            color: '#71717a',
            fontSize: 11,
            fontWeight: 600,
          },
        },
      ],
    },
    true,
  )
}

async function paint(list) {
  await nextTick()
  renderWordCloud(list)
  renderRank(list)
}

async function loadWords() {
  const [w, o] = await Promise.all([fetchWordCloud(60), fetchOverview()])
  if (w.ok) {
    result.value = {
      ...(result.value || {}),
      word_cloud: w.data.word_cloud,
      document_count: w.data.document_count,
      db_topics: o.ok ? o.data.by_topic || [] : result.value?.db_topics || [],
    }
    await paint(w.data.word_cloud)
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
    await paint(res.data.word_cloud)
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

function onResize() {
  cloudChart?.resize()
  rankChart?.resize()
}

onMounted(async () => {
  try {
    await loadWords()
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  cloudChart?.dispose()
  rankChart?.dispose()
  cloudChart = null
  rankChart = null
})
</script>

<template>
  <div class="page topics-page">
    <section class="panel hero">
      <div class="hero-top">
        <div>
          <h2>热点话题</h2>
          <p class="hint">词云为主视觉，辅以词频排行与主题聚类。</p>
        </div>
        <div class="hero-stats">
          <div class="stat">
            <span>文档</span>
            <b>{{ docCount }}</b>
          </div>
          <div class="stat">
            <span>词条</span>
            <b>{{ words.length }}</b>
          </div>
          <div class="stat">
            <span>主题</span>
            <b>{{ bertopic.length }}</b>
          </div>
        </div>
      </div>
      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="loading" @click="onRun(true)">
          <Cloud :size="16" />
          {{ loading ? '分析中…' : '词频 + 主题聚类' }}
        </button>
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="onRun(false)">
          <ListTree :size="16" />
          仅词频
        </button>
        <button type="button" class="btn btn-ghost" :disabled="loading" @click="loadWords">
          <RefreshCw :size="16" />
          刷新词云
        </button>
      </div>
      <p v-if="message" class="ok-text status-line">{{ message }}</p>
      <p v-if="error" class="err status-line">{{ error }}</p>
    </section>

    <section class="panel cloud-hero">
      <div class="panel-head">
        <h3>词云</h3>
        <span class="pill pill-primary">字号 / 颜色 ≈ 热度</span>
      </div>
      <div v-if="words.length" ref="cloudRef" class="wordcloud-box" />
      <div v-else class="empty-box tall">
        <p>暂无词云。请先到「监测」入库，再点上方分析或刷新。</p>
      </div>
    </section>

    <div class="main-grid">
      <section class="panel">
        <div class="panel-head">
          <h3>词频排行</h3>
          <span class="pill pill-default">Top {{ Math.min(12, words.length) }}</span>
        </div>
        <div v-if="words.length" ref="rankRef" class="rank-chart" />
        <div v-else class="empty-box">
          <p>暂无词频数据。</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h3>TF-IDF 关键词</h3>
        </div>
        <ul v-if="keywords.length" class="rank-list">
          <li v-for="(item, idx) in keywords.slice(0, 12)" :key="item.topic">
            <span class="idx">{{ idx + 1 }}</span>
            <span class="name">{{ item.topic }}</span>
            <b>{{ Number(item.weight).toFixed?.(3) ?? item.weight }}</b>
          </li>
        </ul>
        <div v-else class="empty-box">
          <p>跑一次「仅词频」或「词频 + 主题聚类」后显示。</p>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h3>库内话题标签</h3>
        <span class="pill pill-default">{{ dbTopics.length }}</span>
      </div>
      <div v-if="dbTopics.length" class="topic-chips">
        <span v-for="item in dbTopics" :key="item.topic" class="chip">
          {{ item.topic }}
          <em>{{ item.count }}</em>
        </span>
      </div>
      <div v-else class="empty-box compact">
        <p>库内尚无话题字段。</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>主题聚类</h3>
        <span class="pill" :class="bertopic.length ? 'pill-primary' : 'pill-default'">
          {{ bertopic.length ? `${bertopic.length} 个主题` : '未生成' }}
        </span>
      </div>
      <div v-if="bertopic.length" class="topic-cards">
        <article v-for="item in bertopic" :key="item.topic_id" class="topic-card">
          <header>
            <b>{{ item.label }}</b>
            <span class="pill pill-default">{{ item.count }} 条</span>
          </header>
          <p>{{ (item.keywords || []).join(' · ') || '无关键词' }}</p>
        </article>
      </div>
      <div v-else class="empty-box">
        <p>尚未生成主题。点击「词频 + 主题聚类」（需 Ollama 嵌入就绪）。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
}
.hero h2 {
  margin-bottom: 0.25rem;
}
.hero-stats {
  display: flex;
  gap: 0.55rem;
}
.stat {
  min-width: 4.5rem;
  padding: 0.45rem 0.7rem;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  text-align: center;
}
.stat span {
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.stat b {
  display: block;
  margin-top: 0.15rem;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  color: var(--color-primary);
}
.actions {
  display: flex;
  gap: 0.55rem;
  margin-top: 0.9rem;
  flex-wrap: wrap;
}
.status-line {
  margin-top: 0.65rem;
}
.cloud-hero {
  margin-bottom: 0.85rem;
}
.wordcloud-box {
  height: 420px;
  width: 100%;
  border-radius: var(--radius-lg);
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
}
.main-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}
.main-grid > .panel {
  margin-bottom: 0;
  height: 100%;
}
.rank-chart {
  height: 320px;
  width: 100%;
}
.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.rank-list li {
  display: grid;
  grid-template-columns: 1.4rem 1fr auto;
  gap: 0.55rem;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border);
}
.rank-list li:last-child {
  border-bottom: none;
}
.rank-list .idx {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary);
}
.rank-list .name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.rank-list b {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-tertiary);
}
.topic-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  font-size: 0.86rem;
  font-weight: 600;
}
.chip em {
  font-style: normal;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-primary);
}
.topic-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}
.topic-card {
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  border: 1px solid var(--color-border);
}
.topic-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.4rem;
}
.topic-card b {
  font-size: 0.92rem;
}
.topic-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.86rem;
  line-height: 1.5;
}
.empty-box {
  display: grid;
  place-items: center;
  min-height: 160px;
  padding: 1rem;
  border-radius: 12px;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  text-align: center;
}
.empty-box.tall {
  min-height: 280px;
}
.empty-box.compact {
  min-height: 96px;
}
.empty-box p {
  margin: 0;
  max-width: 18rem;
  line-height: 1.5;
}
@media (max-width: 1000px) {
  .main-grid,
  .topic-cards {
    grid-template-columns: 1fr;
  }
  .wordcloud-box {
    height: 320px;
  }
  .rank-chart {
    height: 280px;
  }
}
</style>
