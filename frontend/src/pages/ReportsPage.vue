<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Download, ExternalLink, FileText, RefreshCw, Sparkles } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
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

function ensureChart(instance, el) {
  if (!el) return null
  if (instance && !instance.isDisposed?.()) {
    if (instance.getDom?.() === el) return instance
    instance.dispose()
  }
  return echarts.init(el)
}

function renderVideoSentiment() {
  sentimentChart = ensureChart(sentimentChart, sentimentRef.value)
  if (!sentimentChart || !videoReport.value) return
  const by = videoSentiment.value
  const order = ['positive', 'neutral', 'negative', 'uncertain', 'unknown']
  const data = order
    .filter((k) => (by[k] || 0) > 0)
    .map((k) => ({
      name: labelMap[k],
      value: by[k],
      itemStyle: { color: sentimentColor[k] },
    }))
  sentimentChart.setOption(
    {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        bottom: 0,
        left: 'center',
        textStyle: { color: '#64748b', fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      series: [
        {
          type: 'pie',
          radius: ['46%', '70%'],
          center: ['50%', '42%'],
          label: { color: '#334155', fontSize: 11 },
          data: data.length
            ? data
            : [{ name: '暂无', value: 1, itemStyle: { color: '#e2e8f0' } }],
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '36%',
          style: {
            text: String(videoTotal.value),
            fill: '#0f172a',
            fontSize: 22,
            fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace',
            textAlign: 'center',
          },
        },
        {
          type: 'text',
          left: 'center',
          top: '48%',
          style: { text: '评论', fill: '#64748b', fontSize: 12, textAlign: 'center' },
        },
      ],
    },
    true,
  )
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
  const order = ['positive', 'neutral', 'negative', 'uncertain', 'unknown']
  const data = order
    .filter((k) => (byLabel[k] || 0) > 0)
    .map((k) => ({
      name: labelMap[k] || k,
      value: byLabel[k],
      itemStyle: { color: sentimentColor[k] || '#94a3b8' },
    }))
  const total = data.reduce((s, d) => s + d.value, 0)
  sentimentChart.setOption(
    {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        bottom: 0,
        left: 'center',
        textStyle: { color: '#64748b', fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      series: [
        {
          type: 'pie',
          radius: ['46%', '70%'],
          center: ['50%', '42%'],
          label: { color: '#334155', fontSize: 11 },
          data: data.length
            ? data
            : [{ name: '暂无', value: 1, itemStyle: { color: '#e2e8f0' } }],
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '36%',
          style: {
            text: String(total || report.value.overview?.total_posts || 0),
            fill: '#0f172a',
            fontSize: 22,
            fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace',
            textAlign: 'center',
          },
        },
        {
          type: 'text',
          left: 'center',
          top: '48%',
          style: { text: '总量', fill: '#64748b', fontSize: 12, textAlign: 'center' },
        },
      ],
    },
    true,
  )
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
    <PageHeader title="分析报告" subtitle="单视频口碑结论与预警样例（库级态势见「总览」）">
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
    </PageHeader>

    <!-- 工具区 -->
    <template v-if="mode === 'video'">
      <VideoScopePicker :disabled="loading" :allow-empty="false" />
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
          <RouterLink to="/sentiment">情感页</RouterLink>
          确认进度。
        </div>
        <div class="conclusion" :class="{ ai: videoReport.conclusion_source === 'llm' }">
          {{ videoReport.conclusion }}
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
        <section class="panel">
          <div class="panel-head">
            <h3>本视频情感</h3>
          </div>
          <div ref="sentimentRef" class="chart" />
        </section>
        <section class="panel">
          <div class="panel-head">
            <h3>本视频高频词</h3>
            <span class="pill pill-default">前 {{ Math.min(18, videoReport.word_cloud?.length || 0) }}</span>
          </div>
          <div v-if="videoReport.word_cloud?.length" class="word-rank">
            <div
              v-for="(w, idx) in videoReport.word_cloud.slice(0, 18)"
              :key="w.name"
              class="word-row"
            >
              <span class="word-idx">{{ idx + 1 }}</span>
              <span class="word-name">{{ w.name }}</span>
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
          <p v-else class="hint">暂无分词结果</p>
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
        <div v-if="report.ai_summary" class="conclusion ai">{{ report.ai_summary }}</div>
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
  padding: 0.85rem 1rem;
  background: rgba(22, 163, 74, 0.06);
  border: 1px solid rgba(22, 163, 74, 0.18);
  border-radius: var(--radius-md);
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  font-size: 0.9rem;
}
.conclusion.ai {
  background: rgba(15, 118, 110, 0.06);
  border-color: rgba(15, 118, 110, 0.2);
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
  grid-template-columns: 0.9fr 1.1fr;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.viz-row > .panel {
  margin-bottom: 0;
}
.chart {
  height: 240px;
  width: 100%;
}

.word-rank {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 240px;
  overflow: auto;
}
.word-row {
  display: grid;
  grid-template-columns: 1.4rem 4.5rem 1fr 2rem;
  gap: 0.45rem;
  align-items: center;
  font-size: 0.8rem;
}
.word-idx {
  font-family: var(--font-mono);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.72rem;
}
.word-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.word-bar-track {
  height: 6px;
  border-radius: 99px;
  background: var(--bg-tertiary);
  overflow: hidden;
}
.word-bar {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #0f766e, #2dd4bf);
}
.word-row b {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-tertiary);
  text-align: right;
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
