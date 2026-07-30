<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { Cloud, ListTree, RefreshCw } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import { fetchOverview, fetchWordCloud, runTopics } from '../api/client'

const advTab = ref('tfidf')

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
  '#0f766e',
  '#0d9488',
  '#14b8a6',
  '#0284c7',
  '#0369a1',
  '#16a34a',
  '#ca8a04',
  '#dc2626',
  '#334155',
]

function colorFor(name) {
  let h = 0
  for (let i = 0; i < name.length; i += 1) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return palette[h % palette.length]
}

function renderWordCloud(list) {
  if (!cloudRef.value) return
  if (!cloudChart) cloudChart = echarts.init(cloudRef.value)
  const data = (list || []).slice(0, 80).map((w) => ({
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
          width: '100%',
          height: '100%',
          sizeRange: [18, 88],
          rotationRange: [-20, 20],
          rotationStep: 10,
          gridSize: 6,
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
            fontFamily: 'Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif',
            fontWeight: 700,
          },
          emphasis: {
            focus: 'self',
            textStyle: {
              textShadowBlur: 10,
              textShadowColor: 'rgba(15, 118, 110, 0.28)',
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
  const maxVal = Math.max(...values, 1)
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
      grid: { left: 72, right: 36, top: 12, bottom: 12 },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#94a3b8' },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#334155',
          fontWeight: 600,
          width: 60,
          overflow: 'truncate',
        },
      },
      series: [
        {
          type: 'bar',
          data: values.map((v) => ({
            value: v,
            itemStyle: {
              borderRadius: [0, 8, 8, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#0f766e' },
                { offset: 1, color: v / maxVal > 0.7 ? '#2dd4bf' : '#14b8a6' },
              ]),
            },
          })),
          barMaxWidth: 16,
          label: {
            show: true,
            position: 'right',
            color: '#64748b',
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
    <PageHeader title="热点话题" subtitle="词云主视觉 · 词频与主题洞察">
      <template #actions>
        <span class="stat-pill">文档 <b>{{ docCount }}</b></span>
        <span class="stat-pill">词条 <b>{{ words.length }}</b></span>
        <span class="stat-pill" :class="{ on: bertopic.length }">
          主题 <b>{{ bertopic.length }}</b>
        </span>
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
          刷新
        </button>
      </template>
    </PageHeader>

    <p v-if="message" class="ok-text status-line">{{ message }}</p>
    <p v-if="error" class="err status-line">{{ error }}</p>

    <div class="main-grid">
      <section class="panel cloud-panel">
        <div class="panel-head">
          <h3>词云</h3>
          <span class="pill pill-primary">字号越大 · 热度越高</span>
        </div>
        <div v-if="words.length" ref="cloudRef" class="wordcloud-box" />
        <div v-else class="empty-box tall">
          <p>暂无词云。请先到「监测」入库，再点上方分析或刷新。</p>
        </div>
      </section>

      <section class="panel rank-panel">
        <div class="panel-head">
          <h3>词频排行</h3>
          <span class="pill pill-default">前 {{ Math.min(12, words.length) }}</span>
        </div>
        <div v-if="words.length" ref="rankRef" class="rank-chart" />
        <div v-else class="empty-box">
          <p>暂无词频数据。</p>
        </div>
      </section>
    </div>

    <section class="panel adv-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            type="button"
            class="ui-tab"
            :class="{ active: advTab === 'tfidf' }"
            @click="advTab = 'tfidf'"
          >
            关键词权重
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: advTab === 'db' }"
            @click="advTab = 'db'"
          >
            库内标签
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: advTab === 'bertopic' }"
            @click="advTab = 'bertopic'"
          >
            主题聚类
          </button>
        </div>

        <div v-show="advTab === 'tfidf'" class="ui-tabs-body">
          <ul v-if="keywords.length" class="rank-list">
            <li v-for="(item, idx) in keywords.slice(0, 12)" :key="item.topic">
              <span class="idx">{{ idx + 1 }}</span>
              <span class="name">{{ item.topic }}</span>
              <b>{{ Number(item.weight).toFixed?.(3) ?? item.weight }}</b>
            </li>
          </ul>
          <div v-else class="empty-box compact">
            <p>跑一次「仅词频」或「词频 + 主题聚类」后显示。</p>
          </div>
        </div>

        <div v-show="advTab === 'db'" class="ui-tabs-body">
          <div v-if="dbTopics.length" class="topic-chips">
            <span v-for="item in dbTopics" :key="item.topic" class="chip">
              {{ item.topic }}
              <em>{{ item.count }}</em>
            </span>
          </div>
          <div v-else class="empty-box compact">
            <p>库内尚无话题字段。</p>
          </div>
        </div>

        <div v-show="advTab === 'bertopic'" class="ui-tabs-body">
          <div v-if="bertopic.length" class="topic-cards">
            <article v-for="item in bertopic" :key="item.topic_id" class="topic-card">
              <header>
                <b>{{ item.label }}</b>
                <span class="pill pill-default">{{ item.count }} 条</span>
              </header>
              <p>{{ (item.keywords || []).join(' · ') || '无关键词' }}</p>
            </article>
          </div>
          <div v-else class="empty-box compact">
            <p>尚未生成主题。点击「词频 + 主题聚类」（需本机嵌入服务就绪）。</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.status-line {
  margin: 0 0 0.65rem;
}
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  min-height: 32px;
  padding: 0.2rem 0.65rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: #fff;
  color: var(--text-tertiary);
  font-size: 0.78rem;
}
.stat-pill b {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.9rem;
}
.stat-pill.on {
  border-color: rgba(15, 118, 110, 0.3);
  background: rgba(15, 118, 110, 0.06);
  color: var(--color-primary);
}
.stat-pill.on b {
  color: var(--color-primary);
}

.main-grid {
  display: grid;
  grid-template-columns: 1.55fr 0.85fr;
  gap: 0.9rem;
  margin-bottom: 0.9rem;
  align-items: stretch;
}
.main-grid > .panel {
  margin-bottom: 0;
}
.cloud-panel {
  padding-bottom: 0.85rem;
}
.wordcloud-box {
  height: 480px;
  width: 100%;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(ellipse at 30% 20%, rgba(45, 212, 191, 0.12), transparent 55%),
    radial-gradient(ellipse at 80% 80%, rgba(14, 165, 233, 0.1), transparent 50%),
    #f8fafc;
  border: 1px solid var(--color-border);
}
.rank-chart {
  height: 480px;
  width: 100%;
}
.adv-panel {
  padding-top: 0.65rem;
}
.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-width: 36rem;
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
  border-radius: var(--radius-md);
  background: rgba(15, 118, 110, 0.06);
  border: 1px solid rgba(15, 118, 110, 0.16);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
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
  padding: 0.95rem 1rem;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}
.topic-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.45rem;
}
.topic-card b {
  font-size: 0.95rem;
}
.topic-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.55;
}
.empty-box {
  display: grid;
  place-items: center;
  min-height: 160px;
  padding: 1rem;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  text-align: center;
}
.empty-box.tall {
  min-height: 420px;
}
.empty-box.compact {
  min-height: 96px;
}
.empty-box p {
  margin: 0;
  max-width: 18rem;
  line-height: 1.5;
}
@media (max-width: 1100px) {
  .main-grid,
  .topic-cards {
    grid-template-columns: 1fr;
  }
  .wordcloud-box,
  .rank-chart {
    height: 340px;
  }
  .empty-box.tall {
    min-height: 280px;
  }
}
</style>
