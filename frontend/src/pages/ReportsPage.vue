<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Download, ExternalLink, FileText, RefreshCw, Sparkles } from '@lucide/vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import {
  compareVideos,
  fetchReportSummary,
  fetchUpReport,
  fetchUpSummaries,
  fetchVideoReport,
  fetchVideoSummaries,
  generateReportSummary,
  reportCsvUrl,
  reportPdfUrl,
} from '../api/client'

const route = useRoute()
const router = useRouter()

const mode = ref('video') // video | compare | global
const detailTab = ref('alerts') // alerts | samples | notes
const loading = ref(true)
const aiLoading = ref(false)
const compareLoading = ref(false)
const error = ref('')
const report = ref(null)
const videoReport = ref(null)
const videos = ref([])
const withAiExport = ref(false)
const compareSelected = ref([])
const compareResult = ref(null)
const ups = ref([])
const upDetail = ref(null)
const upLoading = ref(false)

const sentimentRef = ref(null)
const topicRef = ref(null)
const compareChartRef = ref(null)
let sentimentChart
let topicChart
let compareChart

const labelMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}
const methodMap = {
  bert: '模型',
  lexicon: '词典',
  manual: '人工',
  llm: '大模型',
  unknown: '未标注',
  all: '合计',
}
const severityMap = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
}
const sentimentColor = {
  positive: '#16a34a',
  neutral: '#64748b',
  negative: '#dc2626',
  uncertain: '#d97706',
  unknown: '#94a3b8',
}

const activeBvid = computed(() => String(route.query.bvid || '').trim())

const videoSentiment = computed(() => videoReport.value?.sentiment?.by_label || {})
const videoTotal = computed(() => videoReport.value?.overview?.total_posts ?? 0)

const videoStatLine = computed(() => {
  const s = videoSentiment.value
  const pending = videoReport.value?.sentiment?.pending ?? s.unknown ?? 0
  return [
    `${videoTotal.value} 评`,
    `正 ${s.positive ?? 0}`,
    `中 ${s.neutral ?? 0}`,
    `负 ${s.negative ?? 0}`,
    (s.uncertain ?? 0) > 0 ? `不确定 ${s.uncertain}` : '',
    pending > 0 ? `未标注 ${pending}` : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const sentimentPending = computed(
  () =>
    !!(
      videoReport.value?.sentiment_pending ||
      videoReport.value?.sentiment?.sentiment_pending
    ),
)

/** 口碑结论结构化展示：统计 / 倾向 / 词 / 建议分列，避免整段挤在一行 */
const conclusionCard = computed(() => {
  const report = videoReport.value
  if (!report) return null

  const s = videoSentiment.value
  const total = videoTotal.value
  const unknown = Number(s.unknown ?? report.sentiment?.pending ?? 0)
  const labeled = Math.max(total - unknown, 0)

  const pos = Number(s.positive ?? 0)
  const neu = Number(s.neutral ?? 0)
  const neg = Number(s.negative ?? 0)
  const unc = Number(s.uncertain ?? 0)

  let tone = ''
  let advice = ''
  const bars = []

  if (labeled > 0) {
    const posR = pos / labeled
    const negR = neg / labeled
    if (negR >= 0.45) tone = '整体偏负'
    else if (posR >= 0.45) tone = '整体偏正'
    else if (Math.abs(posR - negR) < 0.12) tone = '褒贬接近、整体偏中性'
    else tone = '情绪分化明显'

    if (!sentimentPending.value) {
      if (negR >= 0.35) {
        advice = '建议关注差评集中点，再决定是否需要回复或调整内容。'
      } else if (posR >= 0.5) {
        advice = '观众反馈偏积极，可提炼好评点用于简介或后续选题。'
      } else {
        advice = '建议结合负面样例与高频词，定位具体槽点后再做内容迭代。'
      }
    }

    const mk = (key, count) => ({
      key,
      label: labelMap[key],
      count,
      pct: Math.round((count / labeled) * 100),
      color: sentimentColor[key],
    })
    bars.push(mk('positive', pos), mk('neutral', neu), mk('negative', neg))
    if (unc > 0) bars.push(mk('uncertain', unc))
  }

  const words = (report.word_cloud || [])
    .slice(0, 6)
    .map((w) => w?.name)
    .filter(Boolean)

  const keywordHits = [
    ...new Set(
      (report.alerts?.items || []).flatMap((a) => a.keywords || []).filter(Boolean),
    ),
  ].slice(0, 8)

  const isAi = report.conclusion_source === 'llm'
  const prose = String(report.conclusion || '').trim()

  return {
    labeled,
    total,
    tone,
    advice: isAi ? '' : advice,
    bars,
    words,
    keywordHits,
    isAi,
    prose,
    showStructured: labeled > 0,
  }
})

function ensureChart(instance, el) {
  if (!el) return null
  if (instance && !instance.isDisposed?.()) {
    if (instance.getDom?.() === el) return instance
    instance.dispose()
  }
  return echarts.init(el)
}

/** 单视频 / 全局共用的情感环形图 */
function sentimentDonutOption(data, total, subtext) {
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>{c} 条（{d}%）',
    },
    legend: {
      bottom: 4,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 14,
      textStyle: { color: '#64748b', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          color: '#475569',
          fontSize: 12,
          formatter: '{b}\n{d}%',
        },
        labelLine: {
          length: 12,
          length2: 8,
          lineStyle: { color: '#e2e8f0' },
        },
        data: data.length
          ? data
          : [{ name: '暂无', value: 1, itemStyle: { color: '#e2e8f0' } }],
      },
    ],
    title: {
      text: String(total),
      subtext,
      left: '50%',
      top: '38%',
      textAlign: 'center',
      textStyle: {
        color: '#0f172a',
        fontSize: 24,
        fontWeight: 700,
        fontFamily: 'JetBrains Mono, monospace',
      },
      subtextStyle: {
        color: '#64748b',
        fontSize: 12,
        fontWeight: 400,
      },
    },
  }
}

function sentimentPieData(byLabel) {
  const order = ['positive', 'neutral', 'negative', 'uncertain', 'unknown']
  return order
    .filter((k) => (byLabel[k] || 0) > 0)
    .map((k) => ({
      name: labelMap[k] || k,
      value: byLabel[k],
      itemStyle: { color: sentimentColor[k] || '#94a3b8' },
    }))
}

function renderVideoSentiment() {
  sentimentChart = ensureChart(sentimentChart, sentimentRef.value)
  if (!sentimentChart || !videoReport.value) return
  const data = sentimentPieData(videoSentiment.value)
  sentimentChart.setOption(sentimentDonutOption(data, videoTotal.value, '评论'), true)
}

function renderGlobalTopics() {
  topicChart = ensureChart(topicChart, topicRef.value)
  if (!topicChart || !report.value) return
  const rows = [...(report.value.overview?.by_topic || [])].slice(0, 8).reverse()
  if (!rows.length) {
    topicChart.clear()
    topicChart.setOption({
      title: {
        text: '暂无话题',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 400 },
      },
    })
    return
  }
  topicChart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 80, right: 28, top: 8, bottom: 8 },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: {
        type: 'category',
        data: rows.map((r) => r.topic),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#64748b', fontSize: 11, width: 64, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          barMaxWidth: 12,
          data: rows.map((r) => r.count),
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#0f766e' },
              { offset: 1, color: '#2dd4bf' },
            ]),
          },
          label: { show: true, position: 'right', color: '#64748b', fontSize: 11 },
        },
      ],
    },
    true,
  )
}

function renderGlobalSentiment() {
  sentimentChart = ensureChart(sentimentChart, sentimentRef.value)
  if (!sentimentChart || !report.value) return
  const rows = report.value.overview?.by_sentiment || report.value.sentiment?.breakdown || []
  const byLabel = {}
  for (const row of rows) {
    const key = row.label
    byLabel[key] = (byLabel[key] || 0) + (row.count || 0)
  }
  const data = sentimentPieData(byLabel)
  const total =
    data.reduce((s, d) => s + d.value, 0) || report.value.overview?.total_posts || 0
  sentimentChart.setOption(sentimentDonutOption(data, total, '评论'), true)
}

async function paintCharts() {
  await nextTick()
  if (mode.value === 'video' && videoReport.value) {
    renderVideoSentiment()
  } else if (mode.value === 'global' && report.value) {
    renderGlobalSentiment()
    renderGlobalTopics()
  } else if (mode.value === 'compare' && compareResult.value) {
    renderCompareChart()
  }
  requestAnimationFrame(() => {
    sentimentChart?.resize()
    topicChart?.resize()
    compareChart?.resize()
  })
}

function onResize() {
  sentimentChart?.resize()
  topicChart?.resize()
  compareChart?.resize()
}

function parseBvidsQuery(raw) {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (!value) return []
  return String(value)
    .split(/[,，\s]+/)
    .map((x) => x.trim())
    .filter(Boolean)
    .slice(0, 8)
}

function syncCompareQuery() {
  const query = { ...route.query }
  delete query.bvid
  if (compareSelected.value.length) query.bvids = compareSelected.value.join(',')
  else delete query.bvids
  router.replace({ query })
}

function isCompareSelected(bvid) {
  return compareSelected.value.includes(bvid)
}

function toggleCompareBvid(bvid) {
  const key = String(bvid || '').trim()
  if (!key) return
  const cur = [...compareSelected.value]
  const idx = cur.indexOf(key)
  if (idx >= 0) cur.splice(idx, 1)
  else if (cur.length >= 8) {
    error.value = '一次最多对比 8 个视频'
    return
  } else cur.push(key)
  compareSelected.value = cur
  error.value = ''
  syncCompareQuery()
}

function sharePct(row, key) {
  const labeled =
    (row.positive || 0) + (row.neutral || 0) + (row.negative || 0) + (row.uncertain || 0)
  if (!labeled) return 0
  return Math.round(((row[key] || 0) / labeled) * 1000) / 10
}

function renderCompareChart() {
  compareChart = ensureChart(compareChart, compareChartRef.value)
  if (!compareChart || !compareResult.value) return
  const items = (compareResult.value.items || []).filter((x) => !x.missing)
  if (!items.length) {
    compareChart.clear()
    compareChart.setOption({
      title: {
        text: '暂无可对比数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 400 },
      },
    })
    return
  }
  const cats = items.map((x) => {
    const t = (x.video_title || x.bvid || '').trim()
    return t.length > 14 ? `${t.slice(0, 14)}…` : t
  })
  compareChart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['正面', '中性', '负面', '不确定'], bottom: 0 },
      grid: { left: 48, right: 16, top: 28, bottom: 52 },
      xAxis: {
        type: 'category',
        data: cats,
        axisLabel: {
          interval: 0,
          rotate: cats.length > 4 ? 18 : 0,
          color: '#64748b',
          fontSize: 11,
        },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#64748b' },
      },
      series: [
        {
          name: '正面',
          type: 'bar',
          stack: 's',
          barMaxWidth: 36,
          data: items.map((x) => x.positive || 0),
          itemStyle: { color: '#16a34a' },
        },
        {
          name: '中性',
          type: 'bar',
          stack: 's',
          data: items.map((x) => x.neutral || 0),
          itemStyle: { color: '#64748b' },
        },
        {
          name: '负面',
          type: 'bar',
          stack: 's',
          data: items.map((x) => x.negative || 0),
          itemStyle: { color: '#dc2626' },
        },
        {
          name: '不确定',
          type: 'bar',
          stack: 's',
          data: items.map((x) => x.uncertain || 0),
          itemStyle: { color: '#d97706' },
        },
      ],
    },
    true,
  )
}

async function loadVideos() {
  const res = await fetchVideoSummaries(50)
  if (res.ok) videos.value = res.data.items || []
}

async function loadUps() {
  const res = await fetchUpSummaries(40)
  if (res.ok) ups.value = res.data.items || []
}

async function runCompare() {
  if (compareSelected.value.length < 2) {
    error.value = '请至少勾选 2 个不同视频'
    compareResult.value = null
    return
  }
  compareLoading.value = true
  error.value = ''
  try {
    const res = await compareVideos({
      bvids: compareSelected.value,
      with_keywords: true,
      keyword_top_k: 8,
    })
    if (!res.ok) throw new Error(res.error?.message || '对比失败')
    compareResult.value = res.data
  } catch (e) {
    compareResult.value = null
    error.value = e.message || '对比失败'
  } finally {
    compareLoading.value = false
  }
  await paintCharts()
}

async function onSelectUp(mid) {
  const key = String(mid || '').trim()
  if (!key) {
    upDetail.value = null
    return
  }
  upLoading.value = true
  error.value = ''
  try {
    const res = await fetchUpReport(key)
    if (!res.ok) throw new Error(res.error?.message || 'UP 聚合失败')
    upDetail.value = res.data
  } catch (e) {
    upDetail.value = null
    error.value = e.message || 'UP 聚合失败'
  } finally {
    upLoading.value = false
  }
}

function useUpVideosInCompare() {
  const list = (upDetail.value?.videos || [])
    .map((v) => v.bvid)
    .filter(Boolean)
    .slice(0, 8)
  if (list.length < 2) {
    error.value = '该 UP 已入库视频不足 2 个，无法一键对比'
    return
  }
  compareSelected.value = list
  syncCompareQuery()
  runCompare()
}

async function refreshGlobal() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchReportSummary()
    if (!res.ok) throw new Error(res.error?.message || '报告生成失败')
    report.value = res.data
    detailTab.value = 'notes'
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
  await paintCharts()
}

async function loadVideo(bvid) {
  const key = (bvid || '').trim()
  if (!key) {
    videoReport.value = null
    error.value = '请选择或填写视频号'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await fetchVideoReport(key)
    if (!res.ok) throw new Error(res.error?.message || '视频报告失败')
    videoReport.value = res.data
    detailTab.value = (res.data.alerts?.total || 0) > 0 ? 'alerts' : 'samples'
  } catch (e) {
    videoReport.value = null
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
  await paintCharts()
}

async function refresh() {
  await loadVideos()
  if (mode.value === 'global') {
    await refreshGlobal()
    return
  }
  if (mode.value === 'compare') {
    loading.value = true
    try {
      await loadUps()
      if (compareSelected.value.length >= 2) await runCompare()
      else {
        compareResult.value = null
        error.value = ''
      }
    } finally {
      loading.value = false
    }
    return
  }
  const bvid = activeBvid.value || videos.value[0]?.bvid || ''
  if (bvid) {
    if (!activeBvid.value) {
      await router.replace({ query: { ...route.query, bvid } })
      return
    }
    await loadVideo(bvid)
  } else {
    videoReport.value = null
    loading.value = false
    error.value = ''
  }
}

async function onAiSummary() {
  aiLoading.value = true
  error.value = ''
  try {
    const res = await generateReportSummary({ with_ai: true })
    if (!res.ok) throw new Error(res.error?.message || '摘要失败')
    report.value = res.data
    mode.value = 'global'
    if (res.data?.ai && !res.data.ai.summary) {
      error.value = res.data.ai.message || '智能摘要不可用'
    }
  } catch (e) {
    error.value = e.message || '智能摘要失败'
  } finally {
    aiLoading.value = false
  }
  await paintCharts()
}

async function onVideoAiConclusion() {
  const key = (videoReport.value?.bvid || activeBvid.value || '').trim()
  if (!key) {
    error.value = '请先选择或填写视频号'
    return
  }
  aiLoading.value = true
  error.value = ''
  try {
    const res = await fetchVideoReport(key, { with_ai: true })
    if (!res.ok) throw new Error(res.error?.message || '智能口碑失败')
    videoReport.value = res.data
    if (res.data?.ai && !res.data.ai.summary) {
      error.value = res.data.ai.message || '智能口碑不可用'
    }
  } catch (e) {
    error.value = e.message || '智能口碑失败'
  } finally {
    aiLoading.value = false
  }
}

function openExport(kind) {
  const url =
    kind === 'pdf'
      ? reportPdfUrl({ with_ai: withAiExport.value })
      : reportCsvUrl({ with_ai: withAiExport.value })
  window.open(url, '_blank')
}

function severityClass(level) {
  if (level === 'high') return 'sev-high'
  if (level === 'medium') return 'sev-mid'
  return 'sev-low'
}

watch(
  () => route.query.bvid,
  (v, prev) => {
    if (!v || String(v) === String(prev || '')) return
    if (mode.value !== 'video') {
      mode.value = 'video'
      return
    }
    loadVideo(String(v))
  },
)

watch(
  () => route.query.bvids,
  (v) => {
    if (mode.value !== 'compare') return
    const next = parseBvidsQuery(v)
    const same =
      next.length === compareSelected.value.length &&
      next.every((x, i) => x === compareSelected.value[i])
    if (!same) compareSelected.value = next
  },
)

watch(mode, (m) => {
  if (m === 'global') {
    sentimentChart?.dispose()
    topicChart?.dispose()
    compareChart?.dispose()
    sentimentChart = null
    topicChart = null
    compareChart = null
    refreshGlobal()
  } else if (m === 'compare') {
    sentimentChart?.dispose()
    topicChart?.dispose()
    sentimentChart = null
    topicChart = null
    const fromQ = parseBvidsQuery(route.query.bvids)
    if (fromQ.length) compareSelected.value = fromQ
    refresh()
  } else {
    topicChart?.dispose()
    compareChart?.dispose()
    topicChart = null
    compareChart = null
    refresh()
  }
})

onMounted(() => {
  window.addEventListener('resize', onResize)
  const fromQ = parseBvidsQuery(route.query.bvids)
  if (fromQ.length >= 2) {
    compareSelected.value = fromQ
    mode.value = 'compare'
  } else {
    refresh()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  sentimentChart?.dispose()
  topicChart?.dispose()
  compareChart?.dispose()
  sentimentChart = null
  topicChart = null
  compareChart = null
})
</script>

<template>
  <div class="page reports-page">
    <!-- 工具区 -->
    <template v-if="mode === 'video'">
      <VideoScopePicker :disabled="loading" :allow-empty="false">
        <template #actions>
          <div class="segmented">
            <button type="button" :class="{ active: mode === 'video' }" @click="mode = 'video'">
              单视频口碑
            </button>
            <button type="button" :class="{ active: mode === 'compare' }" @click="mode = 'compare'">
              多视频对比
            </button>
            <button type="button" :class="{ active: mode === 'global' }" @click="mode = 'global'">
              全局导出
            </button>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
            <RefreshCw :size="14" />
            刷新
          </button>
        </template>
      </VideoScopePicker>
      <p v-if="!videos.length && !loading" class="hint scope-empty">
        暂无视频评论。请到「监测」粘贴视频链接采集后再回来查看口碑。
      </p>
    </template>

    <div v-else-if="mode === 'compare'" class="compare-bar">
      <div class="segmented">
        <button type="button" :class="{ active: mode === 'video' }" @click="mode = 'video'">
          单视频口碑
        </button>
        <button type="button" :class="{ active: mode === 'compare' }" @click="mode = 'compare'">
          多视频对比
        </button>
        <button type="button" :class="{ active: mode === 'global' }" @click="mode = 'global'">
          全局导出
        </button>
      </div>
      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="compareLoading || compareSelected.length < 2"
        @click="runCompare"
      >
        开始对比（{{ compareSelected.length }}/8）
      </button>
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        :disabled="loading || compareLoading"
        @click="refresh"
      >
        <RefreshCw :size="14" />
        刷新
      </button>
    </div>

    <div v-else class="export-bar">
      <label class="check">
        <input v-model="withAiExport" type="checkbox" />
        导出时附带智能摘要
      </label>
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        :disabled="aiLoading || loading"
        @click="onAiSummary"
      >
        <Sparkles :size="14" />
        智能摘要
      </button>
      <button type="button" class="btn btn-secondary btn-sm" @click="openExport('csv')">
        <Download :size="14" />
        导出表格
      </button>
      <button type="button" class="btn btn-primary btn-sm" @click="openExport('pdf')">
        <FileText :size="14" />
        导出文档
      </button>
      <div class="export-actions">
        <div class="segmented">
          <button type="button" :class="{ active: mode === 'video' }" @click="mode = 'video'">
            单视频口碑
          </button>
          <button type="button" :class="{ active: mode === 'compare' }" @click="mode = 'compare'">
            多视频对比
          </button>
          <button type="button" :class="{ active: mode === 'global' }" @click="mode = 'global'">
            全局导出
          </button>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
          <RefreshCw :size="14" />
          刷新
        </button>
      </div>
    </div>

    <p v-if="error" class="panel err">{{ error }}</p>
    <p v-if="loading && mode === 'video'" class="panel muted">正在汇总…</p>
    <p v-else-if="loading && mode === 'global'" class="panel muted">正在汇总…</p>

    <!-- 单视频报告：聚焦口碑结论，不做库级总览复读 -->
    <template v-if="mode === 'video' && videoReport && !loading">
      <section class="panel report-hero">
        <div class="hero-top">
          <div class="hero-text">
            <h3>{{ videoReport.video_title || videoReport.generated_for }}</h3>
            <p class="hero-meta">
              <span>{{ videoReport.bvid }}</span>
              <span class="stat-line">{{ videoStatLine }}</span>
              <a
                v-if="videoReport.source_url"
                :href="videoReport.source_url"
                target="_blank"
                rel="noopener"
                class="ext"
              >
                打开视频
                <ExternalLink :size="13" />
              </a>
            </p>
          </div>
          <div class="hero-actions">
            <span
              class="pill"
              :class="videoReport.conclusion_source === 'llm' ? 'pill-primary' : 'pill-success'"
            >
              {{ videoReport.conclusion_source === 'llm' ? '智能观众反馈' : '规则摘要' }}
            </span>
            <RouterLink
              v-if="videoReport.bvid"
              class="btn btn-ghost btn-sm"
              :to="{ path: '/agent', query: { bvid: videoReport.bvid } }"
            >
              用助手解读
            </RouterLink>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="aiLoading || !(videoReport.overview?.total_posts > 0)"
              @click="onVideoAiConclusion"
            >
              <Sparkles :size="14" />
              {{ aiLoading ? '生成中…' : '智能重写' }}
            </button>
          </div>
        </div>
        <div v-if="sentimentPending" class="pending-banner">
          情感分析尚未完成（BERT
          {{ videoReport.sentiment?.bert_done ?? 0 }}/{{ videoReport.sentiment?.total ?? videoTotal }}）。
          口碑结论仅供参考，请先到
          <RouterLink to="/insights">洞察页</RouterLink>
          确认进度。
        </div>
        <div
          v-if="conclusionCard"
          class="conclusion"
          :class="{ ai: conclusionCard.isAi }"
        >
          <template v-if="conclusionCard.showStructured">
            <div class="conclusion-head">
              <strong class="conclusion-tone">{{ conclusionCard.tone }}</strong>
              <span class="conclusion-base">
                基于已标注 {{ conclusionCard.labeled }} 条（共 {{ conclusionCard.total }}）
              </span>
            </div>
            <div class="conclusion-bars" role="list">
              <div
                v-for="b in conclusionCard.bars"
                :key="b.key"
                class="sent-chip"
                role="listitem"
                :style="{ '--sent': b.color }"
              >
                <span class="sent-dot" aria-hidden="true" />
                <span class="sent-name">{{ b.label }}</span>
                <b>{{ b.count }}</b>
                <em>{{ b.pct }}%</em>
              </div>
            </div>
            <div v-if="conclusionCard.words.length" class="conclusion-row">
              <span class="row-label">高频词</span>
              <div class="tag-row">
                <span v-for="w in conclusionCard.words" :key="w" class="word-tag">{{ w }}</span>
              </div>
            </div>
            <div v-if="conclusionCard.keywordHits.length" class="conclusion-row">
              <span class="row-label warn">敏感词</span>
              <div class="tag-row">
                <span
                  v-for="w in conclusionCard.keywordHits"
                  :key="w"
                  class="word-tag warn"
                >{{ w }}</span>
              </div>
            </div>
            <p v-if="conclusionCard.advice" class="conclusion-advice">{{ conclusionCard.advice }}</p>
            <p v-if="conclusionCard.isAi && conclusionCard.prose" class="conclusion-prose">
              {{ conclusionCard.prose }}
            </p>
          </template>
          <p v-else class="conclusion-prose alone">{{ conclusionCard.prose }}</p>
        </div>
        <details
          v-if="
            videoReport.conclusion_source === 'llm' &&
            videoReport.rule_conclusion &&
            videoReport.rule_conclusion !== videoReport.conclusion
          "
          class="rule-snap"
        >
          <summary>查看规则摘要</summary>
          <p>{{ videoReport.rule_conclusion }}</p>
        </details>
      </section>

      <div class="viz-row">
        <section class="panel viz-panel">
          <div class="panel-head">
            <h3>本视频情感</h3>
            <span class="pill pill-default">占比</span>
          </div>
          <div ref="sentimentRef" class="chart chart-fill" />
        </section>
        <section class="panel viz-panel">
          <div class="panel-head">
            <h3>本视频高频词</h3>
            <span class="pill pill-default">
              前 {{ Math.min(10, videoReport.word_cloud?.length || 0) }}
            </span>
          </div>
          <div v-if="videoReport.word_cloud?.length" class="word-rank">
            <div
              v-for="(w, idx) in videoReport.word_cloud.slice(0, 10)"
              :key="w.name"
              class="word-row"
            >
              <span class="word-idx">{{ idx + 1 }}</span>
              <span class="word-name" :title="w.name">{{ w.name }}</span>
              <div class="word-bar-track">
                <div
                  class="word-bar"
                  :style="{
                    width:
                      (w.value / (videoReport.word_cloud[0]?.value || 1)) * 100 + '%',
                  }"
                />
              </div>
              <b>{{ w.value }}</b>
            </div>
          </div>
          <p v-else class="hint empty-hint">暂无分词结果</p>
        </section>
      </div>

      <section class="panel detail-panel">
        <div class="ui-tabs">
          <div class="ui-tabs-nav">
            <button
              type="button"
              class="ui-tab"
              :class="{ active: detailTab === 'alerts' }"
              @click="detailTab = 'alerts'"
            >
              预警评论
              <span class="tab-count">{{ videoReport.alerts?.total ?? 0 }}</span>
            </button>
            <button
              type="button"
              class="ui-tab"
              :class="{ active: detailTab === 'samples' }"
              @click="detailTab = 'samples'"
            >
              评论样例
              <span class="tab-count">{{ videoReport.sample_posts?.length || 0 }}</span>
            </button>
            <button
              type="button"
              class="ui-tab"
              :class="{ active: detailTab === 'notes' }"
              @click="detailTab = 'notes'"
            >
              说明
            </button>
          </div>

          <div v-show="detailTab === 'alerts'" class="ui-tabs-body">
            <div v-if="videoReport.alerts?.items?.length" class="alert-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th style="width: 12%">级别</th>
                    <th>内容</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in videoReport.alerts.items.slice(0, 12)" :key="a.id">
                    <td>
                      <span class="sev" :class="severityClass(a.severity)">
                        {{ severityMap[a.severity] || a.severity }}
                      </span>
                    </td>
                    <td class="alert-msg">{{ a.message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="hint">无明显负面 / 敏感命中。</p>
          </div>

          <div v-show="detailTab === 'samples'" class="ui-tabs-body">
            <div v-if="videoReport.sample_posts?.length" class="sample-grid">
              <article v-for="p in videoReport.sample_posts" :key="p.id" class="sample-card">
                <header>
                  <span
                    class="pill"
                    :class="
                      p.sentiment_label === 'negative'
                        ? 'pill-danger'
                        : p.sentiment_label === 'positive'
                          ? 'pill-success'
                          : 'pill-default'
                    "
                  >
                    {{ labelMap[p.sentiment_label] || p.sentiment_label || '—' }}
                  </span>
                  <span class="muted">{{ p.author || '匿名' }} · 赞 {{ p.likes }}</span>
                  <a
                    v-if="p.source_url"
                    :href="p.source_url"
                    target="_blank"
                    rel="noopener"
                    class="ext"
                  >原评</a>
                </header>
                <p>{{ p.text }}</p>
              </article>
            </div>
            <p v-else class="hint">暂无样例。</p>
          </div>

          <div v-show="detailTab === 'notes'" class="ui-tabs-body">
            <ul class="notes">
              <li v-for="(n, i) in videoReport.notes || []" :key="i">{{ n }}</li>
            </ul>
          </div>
        </div>
      </section>
    </template>

    <!-- 多视频对比 -->
    <template v-if="mode === 'compare'">
      <section class="panel compare-picker">
        <div class="panel-head">
          <h3>选择要对比的视频</h3>
          <span class="muted">勾选 2～8 个已入库 BV，可深链 <code>?bvids=BV1,BV2</code></span>
        </div>
        <p v-if="!videos.length" class="hint">暂无视频。请先到监测页采集。</p>
        <div v-else class="compare-pick-list">
          <label v-for="v in videos" :key="v.bvid" class="compare-pick-item">
            <input
              type="checkbox"
              :checked="isCompareSelected(v.bvid)"
              :disabled="!isCompareSelected(v.bvid) && compareSelected.length >= 8"
              @change="toggleCompareBvid(v.bvid)"
            />
            <span class="pick-title">{{ v.video_title || v.bvid }}</span>
            <span class="pick-meta">
              {{ v.bvid }} · {{ v.comment_count }} 评 · 正{{ v.positive }} / 负{{ v.negative }}
            </span>
          </label>
        </div>

        <div v-if="ups.length" class="up-block">
          <div class="panel-head tight">
            <h4>按 UP 聚合（需采集写入 mid）</h4>
          </div>
          <div class="up-row">
            <select
              class="input"
              :disabled="upLoading"
              @change="onSelectUp($event.target.value)"
            >
              <option value="">选择 UP…</option>
              <option v-for="u in ups" :key="u.mid" :value="u.mid">
                {{ u.owner_name || u.mid }}（{{ u.video_count }} 稿 / {{ u.comment_count }} 评）
              </option>
            </select>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="!upDetail || (upDetail.videos || []).length < 2"
              @click="useUpVideosInCompare"
            >
              用该 UP 视频对比
            </button>
          </div>
          <p v-if="upDetail" class="hint">
            {{ upDetail.owner_name || upDetail.mid }}：已入库
            {{ upDetail.video_count }} 个视频。
          </p>
        </div>
      </section>

      <p v-if="compareLoading" class="panel muted">正在对比…</p>

      <template v-else-if="compareResult">
        <section class="panel">
          <div class="panel-head">
            <h3>情感对比</h3>
            <span class="muted">
              有效 {{ compareResult.present }} · 缺失 {{ compareResult.missing }}
            </span>
          </div>
          <div ref="compareChartRef" class="chart compare-chart" />
        </section>

        <section class="panel">
          <div class="panel-head"><h3>明细</h3></div>
          <div class="alert-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>视频</th>
                  <th>评论</th>
                  <th>正面</th>
                  <th>中性</th>
                  <th>负面</th>
                  <th>不确定</th>
                  <th>高频词</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in compareResult.items" :key="row.bvid">
                  <td>
                    <div class="cmp-title">{{ row.video_title || row.bvid }}</div>
                    <div class="muted">
                      {{ row.bvid }}
                      <span v-if="row.missing" class="badge-miss">未入库</span>
                      <a
                        v-if="row.source_url && !row.missing"
                        :href="row.source_url"
                        target="_blank"
                        rel="noopener"
                        class="ext"
                      >打开</a>
                    </div>
                  </td>
                  <td>{{ row.comment_count }}</td>
                  <td>{{ row.positive }}（{{ sharePct(row, 'positive') }}%）</td>
                  <td>{{ row.neutral }}（{{ sharePct(row, 'neutral') }}%）</td>
                  <td>{{ row.negative }}（{{ sharePct(row, 'negative') }}%）</td>
                  <td>{{ row.uncertain }}</td>
                  <td class="kw-cell">
                    <template v-if="(row.keywords || []).length">
                      <span
                        v-for="w in row.keywords.slice(0, 6)"
                        :key="w.name"
                        class="kw-chip"
                      >{{ w.name }}</span>
                    </template>
                    <span v-else class="muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </template>

    <!-- 全局汇总 -->
    <template v-if="mode === 'global' && report && !loading">
      <section class="panel report-hero">
        <h3>{{ report.generated_for }}</h3>
        <div v-if="report.ai_summary" class="conclusion ai">
          <p class="conclusion-prose alone">{{ report.ai_summary }}</p>
        </div>
      </section>

      <div class="kpi-grid report-kpi">
        <div class="kpi">
          <div class="kpi-label"><span>帖子总量</span></div>
          <div class="kpi-value">{{ report.overview?.total_posts ?? 0 }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>情感已分析</span></div>
          <div class="kpi-value ok">{{ report.sentiment?.bert_done ?? 0 }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>预警</span></div>
          <div class="kpi-value">{{ report.alerts?.total ?? 0 }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>高风险</span></div>
          <div class="kpi-value bad">{{ report.alerts?.high ?? 0 }}</div>
        </div>
      </div>

      <div class="viz-row">
        <section class="panel">
          <div class="panel-head"><h3>情感结构</h3></div>
          <div ref="sentimentRef" class="chart" />
        </section>
        <section class="panel">
          <div class="panel-head"><h3>话题排行</h3></div>
          <div ref="topicRef" class="chart" />
        </section>
      </div>

      <section class="panel detail-panel">
        <div class="ui-tabs">
          <div class="ui-tabs-nav">
            <button
              type="button"
              class="ui-tab"
              :class="{ active: detailTab === 'notes' }"
              @click="detailTab = 'notes'"
            >
              说明
            </button>
            <button
              type="button"
              class="ui-tab"
              :class="{ active: detailTab === 'breakdown' }"
              @click="detailTab = 'breakdown'"
            >
              情感明细
            </button>
          </div>
          <div v-show="detailTab === 'notes'" class="ui-tabs-body">
            <ul class="notes">
              <li v-for="(n, i) in report.notes || []" :key="i">{{ n }}</li>
            </ul>
          </div>
          <div v-show="detailTab === 'breakdown'" class="ui-tabs-body">
            <ul class="stack-list">
              <li v-for="row in report.sentiment?.breakdown || []" :key="row.label + row.method">
                <span>
                  {{ labelMap[row.label] || row.label }}（{{ methodMap[row.method] || row.method }}）
                </span>
                <b>{{ row.count }}</b>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.scope-empty {
  margin: -0.35rem 0 0.75rem;
}
.export-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  margin: 0 0 0.75rem;
  padding: 0.35rem 0;
  min-height: 2rem;
}
.export-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
  margin-left: auto;
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-right: 0.25rem;
}

.stat-line {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.report-hero h3 {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 650;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.hero-meta {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}
.pending-banner {
  margin: 0.75rem 0 0;
  padding: 0.65rem 0.85rem;
  border-radius: var(--radius-md);
  background: rgba(217, 119, 6, 0.1);
  border: 1px solid rgba(217, 119, 6, 0.35);
  color: #92400e;
  font-size: 0.88rem;
  line-height: 1.45;
}
.conclusion {
  margin: 0.75rem 0 0;
  padding: 1rem 1.1rem 1.05rem;
  background: rgba(22, 163, 74, 0.05);
  border: 1px solid rgba(22, 163, 74, 0.16);
  border-left: 3px solid rgba(22, 163, 74, 0.55);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.conclusion.ai {
  background: rgba(15, 118, 110, 0.05);
  border-color: rgba(15, 118, 110, 0.18);
  border-left-color: rgba(15, 118, 110, 0.55);
}
.conclusion-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.45rem 0.85rem;
}
.conclusion-tone {
  font-size: 1rem;
  font-weight: 650;
  letter-spacing: 0.01em;
  color: var(--text-primary);
}
.conclusion-base {
  font-size: 0.78rem;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}
.conclusion-bars {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.sent-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--sent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--sent) 22%, transparent);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.sent-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--sent);
  flex-shrink: 0;
}
.sent-name {
  color: var(--text-secondary);
}
.sent-chip b {
  font-weight: 650;
  color: var(--text-primary);
}
.sent-chip em {
  font-style: normal;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.conclusion-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.55rem;
}
.row-label {
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}
.row-label.warn {
  color: #b45309;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.word-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-sm, 6px);
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  font-size: 0.78rem;
  color: var(--text-secondary);
}
.word-tag.warn {
  background: rgba(217, 119, 6, 0.08);
  border-color: rgba(217, 119, 6, 0.28);
  color: #92400e;
}
.conclusion-advice {
  margin: 0;
  padding-top: 0.55rem;
  border-top: 1px dashed rgba(22, 163, 74, 0.22);
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--text-secondary);
}
.conclusion.ai .conclusion-advice {
  border-top-color: rgba(15, 118, 110, 0.22);
}
.conclusion-prose {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.65;
  white-space: pre-wrap;
  color: var(--text-primary);
  max-width: 72ch;
}
.conclusion-prose.alone {
  max-width: none;
}
.conclusion.ai .conclusion-prose:not(.alone) {
  padding-top: 0.55rem;
  border-top: 1px dashed rgba(15, 118, 110, 0.22);
  color: var(--text-secondary);
}
.rule-snap {
  margin-top: 0.55rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.84rem;
  color: var(--text-secondary);
}
.rule-snap summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--text-primary);
}
.rule-snap p {
  margin: 0.45rem 0 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.viz-row {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
  align-items: stretch;
}
.viz-row > .panel {
  margin-bottom: 0;
}
.viz-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.viz-panel .panel-head {
  flex-shrink: 0;
}
.chart {
  height: 280px;
  width: 100%;
}
.chart-fill {
  flex: 1;
  min-height: 280px;
}

.word-rank {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0;
  min-height: 280px;
  padding: 0.15rem 0 0.1rem;
}
.word-row {
  display: grid;
  grid-template-columns: 1.4rem minmax(3.5rem, 5rem) 1fr 2rem;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.8125rem;
  flex: 1;
}
.word-idx {
  font-family: var(--font-mono);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.75rem;
  text-align: center;
}
.word-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.word-bar-track {
  height: 8px;
  border-radius: 99px;
  background: #f1f5f9;
  overflow: hidden;
}
.word-bar {
  height: 100%;
  border-radius: 99px;
  background: var(--color-primary);
  opacity: 0.85;
}
.word-row b {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-align: right;
}
.empty-hint {
  display: grid;
  place-items: center;
  flex: 1;
  min-height: 240px;
  margin: 0;
}

.detail-panel {
  padding-top: 0.65rem;
}
.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  padding: 0 0.3rem;
  margin-left: 0.15rem;
  border-radius: 99px;
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  font-size: 0.7rem;
  font-weight: 600;
}
.ui-tab.active .tab-count {
  background: rgba(15, 118, 110, 0.12);
  color: var(--color-primary);
}

.alert-table-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.alert-msg {
  white-space: normal !important;
  line-height: 1.45;
  color: var(--text-secondary);
}
.sev {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
}
.sev-high {
  background: rgba(220, 38, 38, 0.08);
  color: #dc2626;
}
.sev-mid {
  background: rgba(217, 119, 6, 0.1);
  color: #d97706;
}
.sev-low {
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

.sample-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}
.sample-card {
  padding: 0.7rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
}
.sample-card header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
  margin-bottom: 0.35rem;
}
.sample-card p {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.ext {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 600;
}
.ext:hover {
  text-decoration: underline;
}
.notes {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--text-secondary);
  line-height: 1.65;
}
.hint {
  margin: 0.5rem 0 0;
}

.compare-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.85rem;
}
.compare-picker .panel-head.tight {
  margin-top: 1rem;
}
.compare-picker h4 {
  margin: 0;
  font-size: 0.92rem;
}
.compare-pick-list {
  display: grid;
  gap: 0.45rem;
  max-height: 280px;
  overflow: auto;
  margin-top: 0.55rem;
}
.compare-pick-item {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.55rem;
  row-gap: 0.1rem;
  align-items: start;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
}
.compare-pick-item input {
  grid-row: 1 / span 2;
  margin-top: 0.2rem;
}
.pick-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.pick-meta {
  grid-column: 2;
  color: var(--text-tertiary);
  font-size: 0.78rem;
}
.up-block {
  margin-top: 0.85rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}
.up-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.up-row .input {
  min-width: 220px;
  flex: 1;
}
.compare-chart {
  min-height: 320px;
}
.cmp-title {
  font-weight: 600;
}
.badge-miss {
  margin-left: 0.35rem;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  background: rgba(220, 38, 38, 0.08);
  color: #dc2626;
  font-size: 0.72rem;
  font-weight: 700;
}
.kw-cell {
  max-width: 220px;
}
.kw-chip {
  display: inline-block;
  margin: 0.1rem 0.2rem 0.1rem 0;
  padding: 0.1rem 0.35rem;
  border-radius: 99px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.72rem;
}

@media (max-width: 1000px) {
  .viz-row,
  .sample-grid {
    grid-template-columns: 1fr;
  }
}
</style>
