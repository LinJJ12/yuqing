<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { Cloud, ListTree, Play, RefreshCw, RotateCcw, Sparkles } from '@lucide/vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import {
  createAnalysisJob,
  fetchAnalysisJob,
  fetchAnalysisJobs,
  fetchOverview,
  fetchSentimentStats,
  fetchWordCloud,
  previewSentiment,
  runSentiment,
  runTopics,
} from '../api/client'
import { formatDateTime } from '../lib/datetime'

const PAGE_SIZE = 10
const route = useRoute()
const router = useRouter()
const activeBvid = computed(() => String(route.query.bvid || '').trim())
const scopeOpts = () => (activeBvid.value ? { bvid: activeBvid.value } : {})

function viewFromQuery(tab) {
  const value = Array.isArray(tab) ? tab[0] : tab
  if (value === 'topics' || value === 'tools') return value
  return 'sentiment'
}

const viewTab = ref(viewFromQuery(route.query.tab))
const toolTab = ref('preview')
const advTab = ref('tfidf')
const sentimentFilter = ref('all')
const samplePage = ref(1)

const sentimentLoading = ref(false)
const jobLoading = ref(false)
const topicRunMode = ref(null)
const message = ref('')
const error = ref('')
const stats = ref(null)
const sample = ref([])
const jobs = ref([])
const previewText = ref('这期剪辑节奏不错，但中段广告有点长，希望能改进。')
const previewResult = ref(null)
const topicResult = ref(null)

const sentimentChartRef = ref(null)
const sentimentPieRef = ref(null)
const cloudRef = ref(null)
const rankRef = ref(null)
const advPanelRef = ref(null)
let sentimentChart
let sentimentPie
let cloudChart
let rankChart
let pollTimer = null

const busy = computed(
  () => sentimentLoading.value || jobLoading.value || topicRunMode.value != null,
)
const words = computed(() => topicResult.value?.word_cloud || [])
const keywords = computed(() => topicResult.value?.keywords || [])
const bertopic = computed(() => topicResult.value?.bertopic || [])
const dbTopics = computed(() => topicResult.value?.db_topics || [])
const docCount = computed(() => topicResult.value?.document_count ?? 0)

const sentimentShares = computed(() => {
  const counts = { positive: 0, neutral: 0, negative: 0, uncertain: 0 }
  for (const row of stats.value?.breakdown || []) {
    if (row.label in counts) counts[row.label] += Number(row.count) || 0
  }
  const labeled = Object.values(counts).reduce((s, n) => s + n, 0)
  const tone = {
    positive: { label: '正面', tone: 'ok' },
    neutral: { label: '中性', tone: '' },
    negative: { label: '负面', tone: 'bad' },
    uncertain: { label: '不确定', tone: 'warn' },
  }
  return ['positive', 'neutral', 'negative', 'uncertain'].map((key) => {
    const count = counts[key]
    const pct = labeled ? Math.round((count / labeled) * 1000) / 10 : 0
    return { key, count, pct, ...tone[key] }
  })
})

const sourceSummary = computed(() => {
  const order = ['bert', 'manual', 'llm', 'lexicon', 'provided', 'none']
  const labels = {
    bert: { name: '模型分析', hint: 'BERT 自动标注' },
    manual: { name: '人工改判', hint: '在预警中心手动改过' },
    llm: { name: '智能复判', hint: '大模型复判结果' },
    lexicon: { name: '词典快筛', hint: '规则词典粗标' },
    provided: { name: '导入自带', hint: '文件导入时已有标签' },
    none: { name: '尚未标注', hint: '还没跑情感分析' },
  }
  const counts = {}
  for (const row of stats.value?.breakdown || []) {
    const key = row.method || 'none'
    counts[key] = (counts[key] || 0) + (Number(row.count) || 0)
  }
  if ((stats.value?.pending || 0) > 0 && !counts.none) {
    // pending 已在 KPI；breakdown 里可能没有 none
  }
  const total = Object.values(counts).reduce((s, n) => s + n, 0) || stats.value?.total || 0
  return order
    .filter((key) => (counts[key] || 0) > 0)
    .map((key) => ({
      key,
      count: counts[key],
      pct: total ? Math.round((counts[key] / total) * 1000) / 10 : 0,
      ...labels[key],
    }))
})

const labelMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}

const labelOptions = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中性' },
  { value: 'negative', label: '负面' },
  { value: 'uncertain', label: '不确定' },
]

const jobStatusMap = {
  queued: '排队中',
  running: '运行中',
  succeeded: '成功',
  failed: '失败',
}

const bertProgress = computed(() => {
  if (!stats.value?.total) return '0%'
  const done = stats.value.model_stale ? 0 : stats.value.bert_done
  return `${Math.round((done / stats.value.total) * 100)}%`
})

const staleHint = computed(() => {
  if (!stats.value?.model_stale) return ''
  return `检测到情感模型已更换（当前 ${stats.value.model_id || ''}），点「分析待处理」或「全量重跑」即可用新模型覆盖旧标签。`
})

const filteredSample = computed(() => {
  const items = sample.value || []
  if (sentimentFilter.value === 'all') return items
  return items.filter((p) => (p.sentiment_label || 'unknown') === sentimentFilter.value)
})

const sampleTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredSample.value.length / PAGE_SIZE)),
)
const pagedSample = computed(() => {
  const start = (samplePage.value - 1) * PAGE_SIZE
  return filteredSample.value.slice(start, start + PAGE_SIZE)
})

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

function setViewTab(value) {
  if (viewTab.value === value) return
  viewTab.value = value
  const query = { ...route.query }
  if (value === 'sentiment') delete query.tab
  else query.tab = value
  router.replace({ query })
}

function setSentimentFilter(value) {
  sentimentFilter.value = value
  samplePage.value = 1
}

function goSamplePage(page) {
  const next = Math.min(Math.max(1, page), sampleTotalPages.value)
  if (next === samplePage.value) return
  samplePage.value = next
}

watch(filteredSample, (items) => {
  const maxPage = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  if (samplePage.value > maxPage) samplePage.value = maxPage
})

watch(
  () => route.query.tab,
  (tab) => {
    viewTab.value = viewFromQuery(tab)
  },
)

watch(viewTab, async (tab) => {
  await nextTick()
  if (tab === 'sentiment') {
    renderSentimentCharts()
  } else if (tab === 'topics') {
    await paintTopics(words.value)
  }
})

async function refreshJobs() {
  const res = await fetchAnalysisJobs(8)
  if (res.ok) jobs.value = res.data.items || []
}

async function onAsyncJob(kind = 'pipeline') {
  jobLoading.value = true
  error.value = ''
  message.value = '已提交后台任务…'
  try {
    const res = await createAnalysisJob({
      kind,
      limit: 5000,
      only_pending: true,
      use_bertopic: true,
      ...scopeOpts(),
    })
    if (!res.ok) {
      error.value = res.error?.message || '任务创建失败'
      jobLoading.value = false
      return
    }
    const jobId = res.data.id
    message.value = `任务 ${jobId.slice(0, 8)}… 已排队`
    await refreshJobs()
    setViewTab('tools')
    toolTab.value = 'jobs'
    clearInterval(pollTimer)
    pollTimer = setInterval(async () => {
      const detail = await fetchAnalysisJob(jobId)
      if (!detail.ok) return
      await refreshJobs()
      if (detail.data.status === 'succeeded') {
        clearInterval(pollTimer)
        pollTimer = null
        message.value = `后台任务完成（${kind}）`
        await Promise.all([refreshStats(), loadWords()])
        jobLoading.value = false
      } else if (detail.data.status === 'failed') {
        clearInterval(pollTimer)
        pollTimer = null
        error.value = detail.data.error_message || '后台任务失败'
        jobLoading.value = false
      }
    }, 1500)
  } catch (e) {
    error.value = e.message || '任务提交失败'
    jobLoading.value = false
  }
}

function renderSentimentCharts() {
  renderSentimentBar()
  renderSentimentPie()
}

function renderSentimentBar() {
  if (!sentimentChartRef.value || !stats.value) return
  if (!sentimentChart) sentimentChart = echarts.init(sentimentChartRef.value)
  const bert = { positive: 0, neutral: 0, negative: 0, uncertain: 0 }
  const lexicon = { positive: 0, neutral: 0, negative: 0, uncertain: 0 }
  for (const row of stats.value.breakdown || []) {
    const bucket = row.method === 'bert' ? bert : lexicon
    if (row.label in bucket) bucket[row.label] += row.count
  }
  const colors = {
    positive: '#16a34a',
    neutral: '#0f766e',
    negative: '#dc2626',
    uncertain: '#d97706',
  }
  const soft = {
    positive: '#86efac',
    neutral: '#5eead4',
    negative: '#fca5a5',
    uncertain: '#fcd34d',
  }
  const cats = ['positive', 'neutral', 'negative', 'uncertain']
  sentimentChart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['模型分析', '词典快筛'],
        top: 0,
        left: 'center',
        textStyle: { color: '#64748b' },
      },
      grid: { left: 48, right: 20, top: 48, bottom: 36 },
      xAxis: {
        type: 'category',
        data: ['正面', '中性', '负面', '不确定'],
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#64748b', margin: 12 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#64748b' },
      },
      series: [
        {
          name: '模型分析',
          type: 'bar',
          barMaxWidth: 32,
          data: cats.map((k) => ({
            value: bert[k],
            itemStyle: { color: colors[k], borderRadius: [4, 4, 0, 0] },
          })),
        },
        {
          name: '词典快筛',
          type: 'bar',
          barMaxWidth: 32,
          data: cats.map((k) => ({
            value: lexicon[k],
            itemStyle: { color: soft[k], borderRadius: [4, 4, 0, 0] },
          })),
        },
      ],
    },
    true,
  )
  requestAnimationFrame(() => sentimentChart?.resize())
}

function renderSentimentPie() {
  if (!sentimentPieRef.value || !stats.value) return
  if (!sentimentPie) sentimentPie = echarts.init(sentimentPieRef.value)
  const colors = {
    positive: '#16a34a',
    neutral: '#0f766e',
    negative: '#dc2626',
    uncertain: '#d97706',
  }
  const data = sentimentShares.value
    .filter((s) => s.count > 0)
    .map((s) => ({
      name: s.label,
      value: s.count,
      itemStyle: { color: colors[s.key] },
    }))
  sentimentPie.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br/>{c} 条（{d}%）',
      },
      legend: {
        bottom: 0,
        left: 'center',
        textStyle: { color: '#64748b' },
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            color: '#475569',
            formatter: '{b}\n{d}%',
          },
          data: data.length
            ? data
            : [{ name: '暂无标注', value: 1, itemStyle: { color: '#e4e4e7' } }],
        },
      ],
    },
    true,
  )
  requestAnimationFrame(() => sentimentPie?.resize())
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
  const top = (list || []).slice(0, 10)
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

async function paintTopics(list) {
  await nextTick()
  renderWordCloud(list)
  renderRank(list)
  requestAnimationFrame(() => {
    cloudChart?.resize()
    rankChart?.resize()
  })
}

async function refreshStats() {
  const res = await fetchSentimentStats(scopeOpts())
  if (res.ok) {
    stats.value = res.data
    await nextTick()
    if (viewTab.value === 'sentiment') renderSentimentCharts()
  } else {
    error.value = res.error?.message || '情感统计加载失败'
  }
}

async function loadWords() {
  const scope = scopeOpts()
  const [w, o] = await Promise.all([
    fetchWordCloud(60, scope),
    activeBvid.value ? Promise.resolve({ ok: false }) : fetchOverview(),
  ])
  if (w.ok) {
    topicResult.value = {
      ...(topicResult.value || {}),
      word_cloud: w.data.word_cloud,
      document_count: w.data.document_count,
      db_topics: o.ok
        ? o.data.by_topic || []
        : activeBvid.value
          ? []
          : topicResult.value?.db_topics || [],
      bvid: activeBvid.value || null,
    }
    if (viewTab.value === 'topics') await paintTopics(w.data.word_cloud)
  }
}

async function onRunSentiment(onlyPending = true) {
  sentimentLoading.value = true
  error.value = ''
  message.value = onlyPending
    ? '正在分析待处理帖子（首次可能较慢，请稍候）…'
    : '正在全量重跑情感分析…'
  try {
    const res = await runSentiment({
      limit: 5000,
      only_pending: onlyPending,
      ...scopeOpts(),
    })
    if (!res.ok) {
      error.value = res.error?.message || '情感分析失败'
      return
    }
    stats.value = res.data.stats
    sample.value = res.data.sample || []
    setViewTab('sentiment')
    if (sample.value.length) {
      toolTab.value = 'sample'
    }
    message.value = `情感完成：更新 ${res.data.updated} 条，耗时 ${res.data.elapsed_ms} ms。难例请到预警页改判。`
    await nextTick()
    renderSentimentCharts()
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    sentimentLoading.value = false
  }
}

async function onRunTopics(useBertopic = true) {
  topicRunMode.value = useBertopic ? 'bertopic' : 'freq'
  error.value = ''
  message.value = useBertopic
    ? '正在提取词频并做主题聚类…'
    : '正在提取词频 / 关键词…'
  try {
    const res = await runTopics({
      limit: 2000,
      use_bertopic: useBertopic,
      ...scopeOpts(),
    })
    if (!res.ok) {
      error.value = res.error?.message || '主题分析失败'
      return
    }
    topicResult.value = res.data
    const kwCount = (res.data.keywords || []).length
    const topicCount = (res.data.bertopic || []).length
    setViewTab('topics')
    if (useBertopic) {
      advTab.value = topicCount ? 'bertopic' : 'tfidf'
      message.value = topicCount
        ? `话题完成：文档 ${res.data.document_count} 条，主题 ${topicCount} 个，关键词 ${kwCount} 个（${res.data.elapsed_ms} ms）`
        : `话题完成：文档 ${res.data.document_count} 条，关键词 ${kwCount} 个（${res.data.elapsed_ms} ms）`
      if (res.data.bertopic_error) {
        message.value += '（主题聚类已回退到词频）'
      }
    } else {
      advTab.value = 'tfidf'
      message.value = `词频完成：文档 ${res.data.document_count} 条，词条 ${(res.data.word_cloud || []).length}，关键词 ${kwCount} 个（${res.data.elapsed_ms} ms）`
    }
    await paintTopics(res.data.word_cloud)
    await nextTick()
    advPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    topicRunMode.value = null
  }
}

async function onPreview() {
  error.value = ''
  try {
    const res = await previewSentiment(previewText.value)
    if (!res.ok) {
      error.value = res.error?.message || '预览失败'
      return
    }
    previewResult.value = res.data
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '预览失败'
  }
}

async function reloadScoped() {
  error.value = ''
  try {
    await Promise.all([refreshStats(), loadWords()])
  } catch {
    error.value = '无法连接后端'
  }
}

function onResize() {
  sentimentChart?.resize()
  sentimentPie?.resize()
  cloudChart?.resize()
  rankChart?.resize()
}

watch(activeBvid, () => {
  sample.value = []
  message.value = activeBvid.value
    ? `已切换到视频 ${activeBvid.value}`
    : '已切换到全部视频'
  sentimentChart?.clear()
  sentimentPie?.clear()
  cloudChart?.clear()
  rankChart?.clear()
  reloadScoped()
})

onMounted(async () => {
  try {
    await Promise.all([refreshStats(), loadWords(), refreshJobs()])
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  sentimentChart?.dispose()
  sentimentPie?.dispose()
  cloudChart?.dispose()
  rankChart?.dispose()
  sentimentChart = null
  sentimentPie = null
  cloudChart = null
  rankChart = null
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="page insights-page">
    <VideoScopePicker :disabled="busy">
      <template #actions>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="busy"
          @click="onRunSentiment(true)"
        >
          <Play :size="14" />
          {{ sentimentLoading ? '情感分析中…' : '分析待处理' }}
        </button>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="busy"
          @click="onRunTopics(true)"
        >
          <Cloud :size="14" />
          {{ topicRunMode === 'bertopic' ? '聚类中…' : '词频 + 主题' }}
        </button>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="busy"
          @click="onRunSentiment(false)"
        >
          <RotateCcw :size="14" />
          情感全量
        </button>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="busy"
          @click="onRunTopics(false)"
        >
          <ListTree :size="14" />
          {{ topicRunMode === 'freq' ? '提取中…' : '仅词频' }}
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm"
          :disabled="busy"
          @click="onAsyncJob('pipeline')"
        >
          <Sparkles :size="14" />
          后台流水线
        </button>
      </template>
    </VideoScopePicker>

    <p v-if="staleHint" class="warn-text status-line">{{ staleHint }}</p>
    <p v-if="message" class="ok-text status-line">{{ message }}</p>
    <p v-if="error" class="err status-line">{{ error }}</p>

    <div v-if="stats" class="kpi-grid kpi-compact">
      <div class="kpi">
        <div class="kpi-label"><span>总量</span></div>
        <div class="kpi-value">{{ stats.total }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>已分析</span></div>
        <div class="kpi-value ok">{{ stats.bert_done }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>待处理</span></div>
        <div class="kpi-value warn">{{ stats.pending }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>不确定</span></div>
        <div class="kpi-value">{{ stats.uncertain ?? 0 }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>进度</span></div>
        <div class="kpi-value">{{ bertProgress }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>词条</span></div>
        <div class="kpi-value">{{ words.length }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label"><span>主题</span></div>
        <div class="kpi-value">{{ bertopic.length }}</div>
      </div>
    </div>

    <p class="hint review-jump">
      难例改判与预警列表在
      <RouterLink
        :to="{ path: '/alerts', query: { ...(activeBvid ? { bvid: activeBvid } : {}), tab: 'review' } }"
      >
        预警中心
      </RouterLink>
      ；本页只负责跑批与看洞察。
    </p>

    <section class="panel view-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            type="button"
            class="ui-tab"
            :class="{ active: viewTab === 'sentiment' }"
            @click="setViewTab('sentiment')"
          >
            情感分布
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: viewTab === 'topics' }"
            @click="setViewTab('topics')"
          >
            词云话题
            <em v-if="words.length" class="tab-count">{{ words.length }}</em>
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: viewTab === 'tools' }"
            @click="setViewTab('tools')"
          >
            工具
          </button>
        </div>

        <div v-show="viewTab === 'sentiment'" class="ui-tabs-body sentiment-body">
          <div v-if="stats" class="share-grid">
            <article
              v-for="item in sentimentShares"
              :key="item.key"
              class="share-card"
              :class="item.tone"
            >
              <div class="share-label">{{ item.label }}</div>
              <div class="share-pct">{{ item.pct }}<small>%</small></div>
              <div class="share-count">{{ item.count }} 条</div>
              <div class="share-bar">
                <i :style="{ width: `${Math.min(item.pct, 100)}%` }" />
              </div>
            </article>
          </div>

          <div class="sentiment-grid">
            <section class="panel chart-panel">
              <div class="panel-head">
                <h3>占比结构</h3>
                <span class="pill pill-primary">环形图</span>
              </div>
              <div ref="sentimentPieRef" class="chart-box sentiment-chart" />
            </section>
            <section class="panel chart-panel">
              <div class="panel-head">
                <h3>模型与词典</h3>
                <span class="pill pill-default">同标签下谁标的多</span>
              </div>
              <div ref="sentimentChartRef" class="chart-box sentiment-chart" />
            </section>
          </div>

          <section class="panel method-panel">
            <div class="panel-head">
              <h3>标签从哪来</h3>
              <span class="pill pill-default">按来源汇总</span>
            </div>
            <p class="hint source-lead">
              上面四张卡看「好评/差评多少」；这里看「这些标签是谁打的」。
            </p>
            <ul v-if="sourceSummary.length" class="source-list">
              <li v-for="item in sourceSummary" :key="item.key">
                <div>
                  <b>{{ item.name }}</b>
                  <span>{{ item.hint }}</span>
                </div>
                <em>{{ item.pct }}%</em>
                <strong>{{ item.count }}</strong>
              </li>
            </ul>
            <p v-else class="hint">还没有标注结果。点「分析待处理」开始跑批。</p>
            <p class="hint method-hint">
              进度 {{ bertProgress }} · 待处理 {{ stats?.pending ?? 0 }} · 不确定
              {{ stats?.uncertain ?? 0 }}。拿不准的难例去
              <RouterLink
                :to="{
                  path: '/alerts',
                  query: { ...(activeBvid ? { bvid: activeBvid } : {}), tab: 'review' },
                }"
              >
                预警中心
              </RouterLink>
              改判。
            </p>
          </section>
        </div>

        <div v-show="viewTab === 'topics'" class="ui-tabs-body topics-body">
          <div class="topics-toolbar">
            <span class="stat-pill">文档 <b>{{ docCount }}</b></span>
            <span class="stat-pill">词条 <b>{{ words.length }}</b></span>
            <span class="stat-pill" :class="{ on: bertopic.length }">
              主题 <b>{{ bertopic.length }}</b>
            </span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="busy" @click="loadWords">
              <RefreshCw :size="14" />
              刷新词云
            </button>
          </div>

          <div class="main-grid">
            <section class="panel cloud-panel">
              <div class="panel-head">
                <h3>词云</h3>
                <span class="pill pill-primary">字号越大 · 热度越高</span>
              </div>
              <div v-if="words.length" ref="cloudRef" class="wordcloud-box" />
              <div v-else class="empty-box tall">
                <p>暂无词云。请先监测入库，再点上方「词频 + 主题」或刷新。</p>
              </div>
            </section>

            <section class="panel rank-panel">
              <div class="panel-head">
                <h3>词频排行</h3>
                <span class="pill pill-default">前 {{ Math.min(10, words.length) }}</span>
              </div>
              <div v-if="words.length" ref="rankRef" class="rank-chart" />
              <div v-else class="empty-box">
                <p>暂无词频数据。</p>
              </div>
            </section>
          </div>

          <section ref="advPanelRef" class="panel adv-panel">
            <div class="ui-tabs">
              <div class="ui-tabs-nav" role="tablist">
                <button
                  type="button"
                  class="ui-tab"
                  :class="{ active: advTab === 'tfidf' }"
                  @click="advTab = 'tfidf'"
                >
                  关键词权重
                  <em v-if="keywords.length" class="tab-count">{{ keywords.length }}</em>
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
                  <em v-if="bertopic.length" class="tab-count">{{ bertopic.length }}</em>
                </button>
              </div>

              <div v-show="advTab === 'tfidf'" class="ui-tabs-body">
                <ul v-if="keywords.length" class="rank-list">
                  <li v-for="(item, idx) in keywords.slice(0, 10)" :key="item.topic">
                    <span class="idx">{{ idx + 1 }}</span>
                    <span class="name">{{ item.topic }}</span>
                    <b>{{ Number(item.weight).toFixed?.(3) ?? item.weight }}</b>
                  </li>
                </ul>
                <div v-else class="empty-box compact">
                  <p>跑一次「仅词频」或「词频 + 主题」后显示。</p>
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
                  <p>尚未生成主题。点击「词频 + 主题」（需本机嵌入服务就绪）。</p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div v-show="viewTab === 'tools'" class="ui-tabs-body">
          <div class="ui-tabs nested-tabs">
            <div class="ui-tabs-nav" role="tablist">
              <button
                type="button"
                class="ui-tab"
                :class="{ active: toolTab === 'preview' }"
                @click="toolTab = 'preview'"
              >
                单句预览
              </button>
              <button
                type="button"
                class="ui-tab"
                :class="{ active: toolTab === 'jobs' }"
                @click="toolTab = 'jobs'"
              >
                最近任务
              </button>
              <button
                v-if="sample.length"
                type="button"
                class="ui-tab"
                :class="{ active: toolTab === 'sample' }"
                @click="toolTab = 'sample'"
              >
                本次样例
              </button>
            </div>

            <div v-show="toolTab === 'preview'" class="ui-tabs-body">
              <textarea v-model="previewText" class="textarea" rows="3" />
              <button
                type="button"
                class="btn btn-primary"
                style="margin-top: 0.65rem"
                :disabled="busy"
                @click="onPreview"
              >
                <Sparkles :size="16" />
                预测
              </button>
              <p v-if="previewResult" class="preview-box">
                <span class="pill pill-primary">
                  {{ labelMap[previewResult.sentiment_label] || previewResult.sentiment_label }}
                </span>
                · 置信度 {{ previewResult.confidence }}
                · {{ previewResult.elapsed_ms }} ms
                <template v-if="previewResult.scores">
                  <br />
                  分数：正 {{ previewResult.scores.positive }} /
                  中 {{ previewResult.scores.neutral }} /
                  负 {{ previewResult.scores.negative }}
                </template>
              </p>
            </div>

            <div v-show="toolTab === 'jobs'" class="ui-tabs-body">
              <ul v-if="jobs.length" class="stack-list">
                <li v-for="job in jobs" :key="job.id">
                  <span>
                    {{ job.kind }} · {{ jobStatusMap[job.status] || job.status }} ·
                    {{ formatDateTime(job.created_at) }}
                  </span>
                  <b>{{ job.id.slice(0, 8) }}</b>
                </li>
              </ul>
              <p v-else class="hint">暂无后台任务。</p>
            </div>

            <div v-show="toolTab === 'sample' && sample.length" class="ui-tabs-body">
              <div class="segmented sentiment-filter" style="margin-bottom: 0.75rem">
                <button
                  type="button"
                  :class="{ active: sentimentFilter === 'all' }"
                  @click="setSentimentFilter('all')"
                >
                  全部
                </button>
                <button
                  v-for="opt in labelOptions"
                  :key="'s-' + opt.value"
                  type="button"
                  :class="{ active: sentimentFilter === opt.value }"
                  @click="setSentimentFilter(opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
              <div v-if="pagedSample.length" class="post-list">
                <article v-for="item in pagedSample" :key="item.id" class="post-item">
                  <header class="post-meta">
                    <b>{{ labelMap[item.sentiment_label] || item.sentiment_label }}</b>
                    <span class="pill pill-default">{{ item.confidence }}</span>
                  </header>
                  <p>{{ item.text }}</p>
                </article>
              </div>
              <p v-else class="hint">当前筛选下暂无样例。</p>

              <div v-if="filteredSample.length > PAGE_SIZE" class="pager">
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="samplePage <= 1"
                  @click="goSamplePage(samplePage - 1)"
                >
                  上一页
                </button>
                <span class="pager-info">第 {{ samplePage }} / {{ sampleTotalPages }} 页</span>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="samplePage >= sampleTotalPages"
                  @click="goSamplePage(samplePage + 1)"
                >
                  下一页
                </button>
              </div>
            </div>
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
.review-jump {
  margin: 0 0 0.85rem;
}
.view-panel {
  padding-top: 0.65rem;
}
.sentiment-body {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.share-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
}
.share-card {
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
}
.share-label {
  font-size: 0.78rem;
  color: var(--text-tertiary);
  font-weight: 600;
}
.share-pct {
  margin-top: 0.25rem;
  font-size: 1.65rem;
  font-weight: 750;
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1.1;
}
.share-pct small {
  font-size: 0.85rem;
  margin-left: 0.1rem;
  color: var(--text-tertiary);
}
.share-count {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.share-bar {
  margin-top: 0.65rem;
  height: 6px;
  border-radius: 99px;
  background: var(--bg-tertiary);
  overflow: hidden;
}
.share-bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: var(--color-primary);
}
.share-card.ok .share-pct,
.share-card.ok .share-bar i {
  color: #16a34a;
  background: #16a34a;
}
.share-card.ok .share-pct {
  background: transparent;
}
.share-card.bad .share-pct {
  color: #dc2626;
}
.share-card.bad .share-bar i {
  background: #dc2626;
}
.share-card.warn .share-pct {
  color: #d97706;
}
.share-card.warn .share-bar i {
  background: #d97706;
}
.sentiment-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 0.85rem;
  align-items: stretch;
}
.sentiment-grid > .panel,
.method-panel {
  margin-bottom: 0;
}
.chart-panel .panel-head,
.method-panel .panel-head {
  margin-bottom: 0.35rem;
}
.sentiment-chart {
  height: 320px;
  min-height: 320px;
}
.source-lead {
  margin: 0 0 0.65rem;
}
.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.source-list li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.65rem 0.75rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: #fff;
}
.source-list b {
  display: block;
  font-size: 0.9rem;
  color: var(--text-primary);
}
.source-list span {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.78rem;
  color: var(--text-tertiary);
}
.source-list em {
  font-style: normal;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.source-list strong {
  font-family: var(--font-mono);
  font-size: 1rem;
  color: var(--text-primary);
  min-width: 2.5rem;
  text-align: right;
}
.method-hint {
  margin: 0.75rem 0 0;
}
.tab-count {
  font-style: normal;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-left: 0.15rem;
}
.topics-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
  margin-bottom: 0.75rem;
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
  height: 420px;
  width: 100%;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(ellipse at 30% 20%, rgba(45, 212, 191, 0.12), transparent 55%),
    radial-gradient(ellipse at 80% 80%, rgba(14, 165, 233, 0.1), transparent 50%),
    #f8fafc;
  border: 1px solid var(--color-border);
}
.rank-chart {
  height: 420px;
  width: 100%;
}
.adv-panel {
  padding-top: 0.65rem;
  scroll-margin-top: 1rem;
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
  min-height: 360px;
}
.empty-box.compact {
  min-height: 96px;
}
.empty-box p {
  margin: 0;
  max-width: 18rem;
  line-height: 1.5;
}
.nested-tabs {
  margin-top: 0.15rem;
}
.sentiment-filter {
  flex-wrap: wrap;
}
.preview-box {
  margin-top: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
@media (max-width: 1100px) {
  .main-grid,
  .topic-cards,
  .sentiment-grid,
  .share-grid {
    grid-template-columns: 1fr;
  }
  .wordcloud-box,
  .rank-chart,
  .sentiment-chart {
    height: 280px;
    min-height: 280px;
  }
  .empty-box.tall {
    min-height: 240px;
  }
}
</style>
