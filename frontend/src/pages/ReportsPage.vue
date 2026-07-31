<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Download, ExternalLink, FileText, RefreshCw, Sparkles } from '@lucide/vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import {
  fetchReportSummary,
  fetchVideoReport,
  fetchVideoSummaries,
  generateReportSummary,
  reportCsvUrl,
  reportPdfUrl,
} from '../api/client'

const route = useRoute()
const router = useRouter()

const mode = ref('video') // video | global
const detailTab = ref('alerts') // alerts | samples | notes
const loading = ref(true)
const aiLoading = ref(false)
const error = ref('')
const report = ref(null)
const videoReport = ref(null)
const videos = ref([])
const withAiExport = ref(false)

const sentimentRef = ref(null)
const topicRef = ref(null)
let sentimentChart
let topicChart

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
  }
  requestAnimationFrame(() => {
    sentimentChart?.resize()
    topicChart?.resize()
  })
}

function onResize() {
  sentimentChart?.resize()
  topicChart?.resize()
}

async function loadVideos() {
  const res = await fetchVideoSummaries(50)
  if (res.ok) videos.value = res.data.items || []
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
    // 切模式交给 mode watch 拉数，避免与 loadVideo 重复请求
    if (mode.value !== 'video') {
      mode.value = 'video'
      return
    }
    loadVideo(String(v))
  },
)

watch(mode, (m) => {
  if (m === 'global') {
    sentimentChart?.dispose()
    sentimentChart = null
    refreshGlobal()
  } else {
    topicChart?.dispose()
    topicChart = null
    refresh()
  }
})

onMounted(() => {
  window.addEventListener('resize', onResize)
  refresh()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  sentimentChart?.dispose()
  topicChart?.dispose()
  sentimentChart = null
  topicChart = null
})
</script>

<template>
  <div class="page reports-page">
    <!-- 工具区：视频选择与模式切换同一行 -->
    <template v-if="mode === 'video'">
      <VideoScopePicker :disabled="loading" :allow-empty="false">
        <template #actions>
          <div class="segmented">
            <button type="button" :class="{ active: mode === 'video' }" @click="mode = 'video'">
              单视频口碑
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

    <p v-if="loading" class="panel muted">正在汇总…</p>
    <p v-else-if="error" class="panel err">{{ error }}</p>

    <!-- 单视频报告：聚焦口碑结论，不做库级总览复读 -->
    <template v-else-if="mode === 'video' && videoReport">
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

    <!-- 全局汇总 -->
    <template v-else-if="mode === 'global' && report">
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

@media (max-width: 1000px) {
  .viz-row,
  .sample-grid {
    grid-template-columns: 1fr;
  }
}
</style>
