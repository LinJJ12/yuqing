<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { RefreshCw } from '@lucide/vue'
import {
  fetchAlerts,
  fetchPosts,
  fetchReviewPosts,
  fetchTrends,
  llmReviewSentiment,
  overridePostSentiment,
} from '../api/client'
import * as echarts from 'echarts'
import CollapsiblePanel from '../components/CollapsiblePanel.vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import { formatDateTime } from '../lib/datetime'

const PAGE_SIZE = 10
const route = useRoute()
const router = useRouter()
const activeBvid = computed(() => String(route.query.bvid || '').trim())
const scopeOpts = () => (activeBvid.value ? { bvid: activeBvid.value } : {})

function tabFromQuery(tab) {
  const value = Array.isArray(tab) ? tab[0] : tab
  return value === 'review' ? 'review' : 'alerts'
}

const listTab = ref(tabFromQuery(route.query.tab))
const bootLoading = ref(true)
const refreshing = ref(false)
const error = ref('')
const message = ref('')
const alerts = ref(null)
const prophetHint = ref('')
const severityFilter = ref('all') // all | high | medium | low
const listPage = ref(1)
const chartRef = ref(null)
let chart
let lastTrendSeries = []
let lastProphetMeta = null
let refreshSeq = 0

const sentimentFilter = ref('all')
const reviewPage = ref(1)
const reviewPosts = ref([])
const reviewLoading = ref(false)
const reviewBusyId = ref(null)

const severityMap = { high: '高风险', medium: '中风险', low: '低风险' }
const severityPill = {
  high: 'pill-danger',
  medium: 'pill-warning',
  low: 'pill-default',
}

const labelMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}

const methodMap = {
  bert: '模型',
  manual: '人工',
  llm: '大模型',
  lexicon: '词典',
  provided: '导入',
}

const labelOptions = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中性' },
  { value: 'negative', label: '负面' },
  { value: 'uncertain', label: '不确定' },
]

const busy = computed(() => bootLoading.value || refreshing.value)

const listTabs = computed(() => [
  {
    value: 'alerts',
    label: '预警列表',
    count: alerts.value?.count ?? alerts.value?.items?.length ?? 0,
  },
  {
    value: 'review',
    label: '难例改判',
    count: reviewPosts.value.length,
  },
])

const severityTabs = computed(() => {
  const a = alerts.value
  return [
    { value: 'all', label: '全部', count: a?.count ?? a?.items?.length ?? 0 },
    { value: 'high', label: '高风险', count: a?.high ?? 0 },
    { value: 'medium', label: '中风险', count: a?.medium ?? 0 },
    { value: 'low', label: '低风险', count: a?.low ?? 0 },
  ]
})

const filteredAlerts = computed(() => {
  const items = alerts.value?.items || []
  if (severityFilter.value === 'all') return items
  return items.filter((item) => item.severity === severityFilter.value)
})

const alertTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredAlerts.value.length / PAGE_SIZE)),
)
const pagedAlerts = computed(() => {
  const start = (listPage.value - 1) * PAGE_SIZE
  return filteredAlerts.value.slice(start, start + PAGE_SIZE)
})
const alertPageFrom = computed(() =>
  filteredAlerts.value.length ? (listPage.value - 1) * PAGE_SIZE + 1 : 0,
)
const alertPageTo = computed(() =>
  Math.min(filteredAlerts.value.length, listPage.value * PAGE_SIZE),
)

const reviewFilterTabs = computed(() => {
  const items = reviewPosts.value || []
  const countOf = (label) => items.filter((p) => (p.sentiment_label || 'unknown') === label).length
  return [
    { value: 'all', label: '全部', count: items.length },
    { value: 'positive', label: '正面', count: countOf('positive') },
    { value: 'neutral', label: '中性', count: countOf('neutral') },
    { value: 'negative', label: '负面', count: countOf('negative') },
    { value: 'uncertain', label: '不确定', count: countOf('uncertain') },
  ]
})

const filteredReviewPosts = computed(() => {
  const items = reviewPosts.value || []
  if (sentimentFilter.value === 'all') return items
  return items.filter((p) => (p.sentiment_label || 'unknown') === sentimentFilter.value)
})

const reviewTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredReviewPosts.value.length / PAGE_SIZE)),
)
const pagedReviewPosts = computed(() => {
  const start = (reviewPage.value - 1) * PAGE_SIZE
  return filteredReviewPosts.value.slice(start, start + PAGE_SIZE)
})
const reviewPageFrom = computed(() =>
  filteredReviewPosts.value.length ? (reviewPage.value - 1) * PAGE_SIZE + 1 : 0,
)
const reviewPageTo = computed(() =>
  Math.min(filteredReviewPosts.value.length, reviewPage.value * PAGE_SIZE),
)

function setListTab(value) {
  if (listTab.value === value) return
  listTab.value = value
  const query = { ...route.query }
  if (value === 'review') query.tab = 'review'
  else delete query.tab
  router.replace({ query })
}

function setSeverityFilter(value) {
  severityFilter.value = value
  listPage.value = 1
}

function setSentimentFilter(value) {
  sentimentFilter.value = value
  reviewPage.value = 1
}

function goAlertPage(page) {
  const next = Math.min(Math.max(1, page), alertTotalPages.value)
  if (next === listPage.value) return
  listPage.value = next
}

function goReviewPage(page) {
  const next = Math.min(Math.max(1, page), reviewTotalPages.value)
  if (next === reviewPage.value) return
  reviewPage.value = next
}

function sentimentPillClass(label) {
  if (label === 'positive') return 'pill-success'
  if (label === 'negative') return 'pill-danger'
  if (label === 'uncertain') return 'pill-warning'
  return 'pill-default'
}

watch(filteredAlerts, (items) => {
  const maxPage = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  if (listPage.value > maxPage) listPage.value = maxPage
})

watch(filteredReviewPosts, (items) => {
  const maxPage = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  if (reviewPage.value > maxPage) reviewPage.value = maxPage
})

watch(
  () => route.query.tab,
  (tab) => {
    listTab.value = tabFromQuery(tab)
  },
)

function renderTrend(series = lastTrendSeries, prophetMeta = lastProphetMeta) {
  lastTrendSeries = series || []
  lastProphetMeta = prophetMeta
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const hasProphet = lastTrendSeries.some((s) => s.prophet_yhat != null)
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['发帖量', '滑动平均', ...(hasProphet ? ['智能预测'] : [])],
        top: 0,
        left: 'center',
        textStyle: { color: '#52525b' },
      },
      grid: { left: 48, right: 20, top: 48, bottom: 40 },
      xAxis: {
        type: 'category',
        data: lastTrendSeries.map((s) => s.day),
        axisLine: { lineStyle: { color: '#e4e4e7' } },
        axisLabel: { color: '#71717a', margin: 12 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f4f4f5' } },
        axisLabel: { color: '#71717a' },
      },
      series: [
        {
          name: '发帖量',
          type: 'bar',
          barMaxWidth: 22,
          data: lastTrendSeries.map((s) => (s.is_forecast ? null : s.count)),
          itemStyle: { color: '#e4e4e7', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '滑动平均',
          type: 'line',
          smooth: true,
          data: lastTrendSeries.map((s) => (s.is_forecast ? null : s.rolling_mean)),
          itemStyle: { color: '#0f766e' },
          lineStyle: { width: 2.5, color: '#0f766e' },
        },
        ...(hasProphet
          ? [
              {
                name: '智能预测',
                type: 'line',
                smooth: true,
                data: lastTrendSeries.map((s) => s.prophet_yhat),
                itemStyle: { color: '#d97706' },
                lineStyle: { width: 2, type: 'dashed', color: '#d97706' },
              },
            ]
          : []),
      ],
    },
    true,
  )
  prophetHint.value = prophetMeta?.enabled
    ? `智能预测已启用，向前预测 ${prophetMeta.horizon_days || 7} 天`
    : prophetMeta?.message || ''
  requestAnimationFrame(() => chart?.resize())
}

function onResize() {
  chart?.resize()
}

function onChartToggle(open) {
  if (!open) return
  nextTick(() => {
    renderTrend()
    requestAnimationFrame(() => chart?.resize())
  })
}

async function refreshAlertsAndTrend() {
  const scope = scopeOpts()
  const [a, t] = await Promise.all([fetchAlerts(200, scope), fetchTrends(14, scope)])
  if (!a.ok) throw new Error(a.error?.message || '预警加载失败')
  alerts.value = a.data
  if (t.ok) {
    await nextTick()
    renderTrend(t.data.series || [], t.data.prophet)
  } else if (!prophetHint.value) {
    prophetHint.value = t.error?.message || '趋势加载失败'
  }
}

async function refreshReview() {
  reviewLoading.value = true
  try {
    const scope = scopeOpts()
    const settled = await Promise.allSettled([
      fetchReviewPosts(200, scope),
      fetchPosts({ label: 'positive', limit: 40, order: 'fetched', ...scope }),
      fetchPosts({ label: 'neutral', limit: 40, order: 'fetched', ...scope }),
      fetchPosts({ label: 'negative', limit: 40, order: 'fetched', ...scope }),
      fetchPosts({ label: 'uncertain', limit: 40, order: 'fetched', ...scope }),
    ])
    const byId = new Map()
    let anyOk = false
    let firstErr = ''
    for (const item of settled) {
      if (item.status !== 'fulfilled') {
        if (!firstErr) firstErr = item.reason?.message || '难例列表请求失败'
        continue
      }
      if (!item.value?.ok) {
        if (!firstErr) firstErr = item.value?.error?.message || '难例列表加载失败'
        continue
      }
      anyOk = true
      for (const p of item.value.data?.items || []) {
        byId.set(p.id, p)
      }
    }
    if (!anyOk) throw new Error(firstErr || '难例列表加载失败')
    reviewPosts.value = [...byId.values()].sort((a, b) => {
      const ca = Number(a.sentiment_confidence)
      const cb = Number(b.sentiment_confidence)
      const va = Number.isFinite(ca) ? ca : 1
      const vb = Number.isFinite(cb) ? cb : 1
      return va - vb
    })
  } finally {
    reviewLoading.value = false
  }
}

async function refresh() {
  const seq = ++refreshSeq
  const first = bootLoading.value && !alerts.value
  if (first) bootLoading.value = true
  else refreshing.value = true
  error.value = ''
  try {
    const results = await Promise.allSettled([refreshAlertsAndTrend(), refreshReview()])
    if (seq !== refreshSeq) return
    const errors = results
      .filter((r) => r.status === 'rejected')
      .map((r) => r.reason?.message || '加载失败')
    if (errors.length === results.length) {
      error.value = errors[0] || '无法连接后端'
    } else if (errors.length) {
      error.value = errors.join('；')
    }
  } catch (e) {
    if (seq !== refreshSeq) return
    error.value = e.message || '无法连接后端'
  } finally {
    if (seq === refreshSeq) {
      bootLoading.value = false
      refreshing.value = false
    }
  }
}

async function onRefreshReview() {
  error.value = ''
  try {
    await refreshReview()
  } catch (e) {
    error.value = e.message || '难例列表刷新失败'
  }
}

function applyPostUpdate(postId, updated) {
  if (!updated) return
  const idx = reviewPosts.value.findIndex((p) => p.id === postId)
  if (idx >= 0) {
    reviewPosts.value[idx] = updated.id ? updated : { ...reviewPosts.value[idx], ...updated }
  }
  const items = alerts.value?.items
  if (!items) return
  const aIdx = items.findIndex((a) => a.post_id === postId)
  if (aIdx < 0) return
  const cur = items[aIdx]
  items[aIdx] = {
    ...cur,
    sentiment_label: updated.sentiment_label ?? cur.sentiment_label,
    sentiment_method: updated.sentiment_method ?? cur.sentiment_method,
    sentiment_confidence:
      updated.sentiment_confidence != null ? updated.sentiment_confidence : cur.sentiment_confidence,
  }
}

async function onManualOverride(post, label) {
  const postId = Number(post.post_id ?? post.id)
  if (!Number.isFinite(postId) || postId <= 0) return
  if (!label || (label === post.sentiment_label && post.sentiment_method === 'manual')) return
  reviewBusyId.value = postId
  error.value = ''
  try {
    const res = await overridePostSentiment(postId, { label, method: 'manual' })
    if (!res.ok) {
      error.value = res.error?.message || '改判失败'
      message.value = ''
      return
    }
    applyPostUpdate(postId, res.data?.id ? res.data : { ...post, ...res.data, id: postId })
    message.value = `已人工改判 #${postId} → ${labelMap[label] || label}`
    try {
      await refreshAlertsAndTrend()
    } catch (e) {
      error.value = `改判已保存，但预警刷新失败：${e.message || e}`
    }
  } catch (e) {
    error.value = e.message || '改判失败'
    message.value = ''
  } finally {
    reviewBusyId.value = null
  }
}

async function onLlmReview(post) {
  const postId = Number(post.post_id ?? post.id)
  if (!Number.isFinite(postId) || postId <= 0) return
  reviewBusyId.value = postId
  error.value = ''
  message.value = `正在智能复判 #${postId}…`
  try {
    const res = await llmReviewSentiment({ post_id: postId, apply: true })
    if (!res.ok) {
      error.value = res.error?.message || '智能复判失败'
      message.value = ''
      return
    }
    const updated = res.data.post || res.data
    applyPostUpdate(postId, updated?.id ? updated : { ...updated, id: postId })
    const lab = res.data.sentiment_label || updated?.sentiment_label
    message.value = `智能复判 #${postId} → ${labelMap[lab] || lab}${res.data.reason ? `（${res.data.reason}）` : ''}`
    try {
      await refreshAlertsAndTrend()
    } catch (e) {
      error.value = `复判已保存，但预警刷新失败：${e.message || e}`
    }
  } catch (e) {
    error.value = e.message || '智能复判失败'
    message.value = ''
  } finally {
    reviewBusyId.value = null
  }
}

function openInReview(postId) {
  if (!postId) return
  const post = reviewPosts.value.find((p) => p.id === postId)
  setListTab('review')
  if (!post) {
    message.value = `帖子 #${postId} 不在当前难例列表（多为高置信负面）；可直接在预警项改判`
    return
  }
  const label = post.sentiment_label || 'unknown'
  if (sentimentFilter.value !== 'all' && sentimentFilter.value !== label) {
    sentimentFilter.value = 'all'
  }
  nextTick(() => {
    const idx = filteredReviewPosts.value.findIndex((p) => p.id === postId)
    if (idx >= 0) reviewPage.value = Math.floor(idx / PAGE_SIZE) + 1
    nextTick(() => {
      document.getElementById(`review-post-${postId}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    })
  })
}

watch(activeBvid, () => {
  listPage.value = 1
  reviewPage.value = 1
  message.value = ''
  error.value = ''
  // 避免切视频时短暂展示上一视频的预警/难例
  alerts.value = null
  reviewPosts.value = []
  lastTrendSeries = []
  lastProphetMeta = null
  prophetHint.value = ''
  chart?.clear()
  bootLoading.value = true
  refresh()
})

onMounted(() => {
  refresh()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div class="page">
    <VideoScopePicker :disabled="busy">
      <template #actions>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="busy" @click="refresh">
          <RefreshCw :size="14" />
          刷新
        </button>
      </template>
    </VideoScopePicker>

    <p v-if="message" class="ok-text" style="margin: 0 0 0.5rem">{{ message }}</p>
    <p v-if="error" class="err" style="margin: 0 0 0.5rem">{{ error }}</p>
    <p v-if="bootLoading" class="muted">加载中…</p>
    <p v-else-if="refreshing" class="hint" style="margin: 0 0 0.5rem">刷新中…</p>

    <div v-if="alerts" class="kpi-grid kpi-compact">
      <button
        type="button"
        class="kpi kpi-btn"
        :class="{ active: listTab === 'alerts' && severityFilter === 'all' }"
        @click="setListTab('alerts'); setSeverityFilter('all')"
      >
        <div class="kpi-label"><span>预警数</span></div>
        <div class="kpi-value">{{ alerts.count }}</div>
      </button>
      <button
        type="button"
        class="kpi kpi-btn"
        :class="{ active: listTab === 'alerts' && severityFilter === 'high' }"
        @click="setListTab('alerts'); setSeverityFilter('high')"
      >
        <div class="kpi-label"><span>高风险</span></div>
        <div class="kpi-value bad">{{ alerts.high }}</div>
      </button>
      <button
        type="button"
        class="kpi kpi-btn"
        :class="{ active: listTab === 'alerts' && severityFilter === 'medium' }"
        @click="setListTab('alerts'); setSeverityFilter('medium')"
      >
        <div class="kpi-label"><span>中风险</span></div>
        <div class="kpi-value warn">{{ alerts.medium }}</div>
      </button>
      <button
        type="button"
        class="kpi kpi-btn"
        :class="{ active: listTab === 'review' }"
        @click="setListTab('review')"
      >
        <div class="kpi-label"><span>待改判</span></div>
        <div class="kpi-value">{{ reviewPosts.length }}</div>
      </button>
    </div>

    <CollapsiblePanel
      title="热度趋势"
      storage-key="yuqing.alerts.chart.v2"
      :default-open="true"
      @toggle="onChartToggle"
    >
      <p v-if="prophetHint" class="hint" style="margin-top: 0">{{ prophetHint }}</p>
      <div ref="chartRef" class="chart-box chart-compact" />
    </CollapsiblePanel>

    <section class="panel list-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            v-for="tab in listTabs"
            :key="tab.value"
            type="button"
            class="ui-tab"
            :class="{ active: listTab === tab.value }"
            role="tab"
            @click="setListTab(tab.value)"
          >
            {{ tab.label }}
            <span class="tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <div v-show="listTab === 'alerts'" class="ui-tabs-body">
          <div class="segmented severity-filter" role="tablist">
            <button
              v-for="tab in severityTabs"
              :key="tab.value"
              type="button"
              :class="{ active: severityFilter === tab.value }"
              @click="setSeverityFilter(tab.value)"
            >
              {{ tab.label }}
              <em>{{ tab.count }}</em>
            </button>
          </div>

          <p v-if="filteredAlerts.length" class="hint pager-range">
            显示 {{ alertPageFrom }}–{{ alertPageTo }} / {{ filteredAlerts.length }} ·
            有帖子的预警可直接改判，改完后若不再触发会从列表消失
          </p>

          <div v-if="pagedAlerts.length" class="alert-list">
            <article
              v-for="item in pagedAlerts"
              :key="item.id"
              class="alert-item"
              :class="item.severity"
            >
              <header class="alert-head">
                <div class="alert-title-row">
                  <b class="alert-title">{{ item.title }}</b>
                  <span class="pill" :class="severityPill[item.severity] || 'pill-default'">
                    {{ severityMap[item.severity] || item.severity }}
                  </span>
                  <span
                    v-if="item.sentiment_label"
                    class="pill"
                    :class="sentimentPillClass(item.sentiment_label)"
                  >
                    {{ labelMap[item.sentiment_label] || item.sentiment_label }}
                  </span>
                  <span v-if="item.sentiment_method" class="pill pill-default">
                    {{ methodMap[item.sentiment_method] || item.sentiment_method }}
                  </span>
                </div>
                <time class="alert-time">{{ formatDateTime(item.created_at) }}</time>
              </header>
              <p class="alert-msg">{{ item.message }}</p>
              <footer class="alert-foot">
                <div class="alert-meta-line">
                  <small v-if="item.keywords?.length" class="alert-kw">
                    关键词：{{ item.keywords.join('、') }}
                  </small>
                  <div class="alert-links">
                    <RouterLink
                      v-if="item.bvid"
                      class="link-out"
                      :to="{ path: '/reports', query: { bvid: item.bvid } }"
                    >
                      看口碑
                    </RouterLink>
                    <a
                      v-if="item.source_url"
                      class="link-out"
                      :href="item.source_url"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      原评
                    </a>
                    <button
                      v-if="item.post_id"
                      type="button"
                      class="link-out link-btn"
                      @click="openInReview(item.post_id)"
                    >
                      到难例
                    </button>
                  </div>
                </div>
                <div v-if="item.post_id" class="review-actions">
                  <select
                    class="input review-select"
                    :value="item.sentiment_label || ''"
                    :disabled="reviewBusyId === item.post_id"
                    @change="onManualOverride(item, $event.target.value)"
                  >
                    <option disabled value="">改判为…</option>
                    <option v-for="opt in labelOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    :disabled="reviewBusyId === item.post_id"
                    @click="onLlmReview(item)"
                  >
                    智能复判
                  </button>
                </div>
                <p v-else class="hint alert-no-post">量级预警，无需改判</p>
              </footer>
            </article>
          </div>
          <p v-else class="hint">
            <template v-if="bootLoading">加载中…</template>
            <template v-else-if="!alerts">暂无数据，请点击刷新。</template>
            <template v-else-if="!alerts.items?.length">
              暂无预警。建议路径：
              <RouterLink to="/monitor">监测</RouterLink>
              采 BV →
              <RouterLink to="/insights">洞察</RouterLink>
              跑完 → 再回到此页核对。
            </template>
            <template v-else>
              当前筛选下暂无「{{ severityMap[severityFilter] || severityFilter }}」预警。
            </template>
          </p>

          <div v-if="filteredAlerts.length > PAGE_SIZE" class="pager">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="listPage <= 1"
              @click="goAlertPage(listPage - 1)"
            >
              上一页
            </button>
            <span class="pager-info">第 {{ listPage }} / {{ alertTotalPages }} 页</span>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="listPage >= alertTotalPages"
              @click="goAlertPage(listPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>

        <div v-show="listTab === 'review'" class="ui-tabs-body">
          <div class="toolbar" style="margin-bottom: 0.65rem">
            <p class="hint" style="margin: 0">
              低置信难例集中改判；预警列表里关联帖子也可直接改。人工与智能复判不会被后续模型覆盖。
            </p>
            <button
              type="button"
              class="btn btn-ghost btn-sm"
              :disabled="reviewLoading"
              @click="onRefreshReview"
            >
              刷新
            </button>
          </div>

          <div class="segmented sentiment-filter" role="tablist">
            <button
              v-for="tab in reviewFilterTabs"
              :key="tab.value"
              type="button"
              :class="{ active: sentimentFilter === tab.value }"
              @click="setSentimentFilter(tab.value)"
            >
              {{ tab.label }}
              <em>{{ tab.count }}</em>
            </button>
          </div>

          <p v-if="filteredReviewPosts.length" class="hint pager-range">
            显示 {{ reviewPageFrom }}–{{ reviewPageTo }} / {{ filteredReviewPosts.length }}
          </p>

          <div v-if="pagedReviewPosts.length" class="post-list alert-list">
            <article
              v-for="item in pagedReviewPosts"
              :id="`review-post-${item.id}`"
              :key="item.id"
              class="alert-item review-item"
            >
              <header class="alert-head">
                <div class="alert-title-row">
                  <b class="alert-title">#{{ item.id }}</b>
                  <span class="pill" :class="sentimentPillClass(item.sentiment_label)">
                    {{ labelMap[item.sentiment_label] || item.sentiment_label || '未标注' }}
                  </span>
                  <span class="pill pill-default">
                    {{ methodMap[item.sentiment_method] || item.sentiment_method || '—' }}
                  </span>
                  <em v-if="item.sentiment_confidence != null" class="alert-conf">
                    置信 {{ item.sentiment_confidence }}
                  </em>
                </div>
              </header>
              <p class="alert-msg">{{ item.text }}</p>
              <footer class="alert-foot alert-foot-actions">
                <div class="review-actions">
                  <select
                    class="input review-select"
                    :value="item.sentiment_label || ''"
                    :disabled="reviewBusyId === item.id"
                    @change="onManualOverride(item, $event.target.value)"
                  >
                    <option disabled value="">改判为…</option>
                    <option v-for="opt in labelOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    :disabled="reviewBusyId === item.id"
                    @click="onLlmReview(item)"
                  >
                    智能复判
                  </button>
                </div>
              </footer>
            </article>
          </div>
          <p v-else class="hint">
            {{
              bootLoading || reviewLoading
                ? '加载中…'
                : sentimentFilter === 'all'
                  ? '暂无待浏览帖子。请先在洞察页跑批分析。'
                  : `当前筛选下暂无「${labelMap[sentimentFilter]}」帖子`
            }}
          </p>

          <div v-if="filteredReviewPosts.length > PAGE_SIZE" class="pager">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="reviewPage <= 1"
              @click="goReviewPage(reviewPage - 1)"
            >
              上一页
            </button>
            <span class="pager-info">第 {{ reviewPage }} / {{ reviewTotalPages }} 页</span>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="reviewPage >= reviewTotalPages"
              @click="goReviewPage(reviewPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.kpi-btn {
  width: 100%;
  text-align: left;
  cursor: pointer;
  font: inherit;
  transition: border-color 120ms, box-shadow 120ms;
}
.kpi-btn:hover {
  border-color: var(--color-border-strong);
}
.kpi-btn.active {
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.25);
  background: rgba(15, 118, 110, 0.04);
}

.list-panel {
  padding-top: 0.65rem;
}
.pager-range {
  margin: 0 0 0.65rem;
}
.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  padding: 0 0.3rem;
  margin-left: 0.2rem;
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

.severity-filter,
.sentiment-filter {
  margin-bottom: 0.85rem;
  flex-wrap: wrap;
}
.severity-filter em,
.sentiment-filter em {
  font-style: normal;
  margin-left: 0.2rem;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-family: var(--font-mono);
}
.severity-filter button.active em,
.sentiment-filter button.active em {
  color: var(--color-primary);
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.alert-item {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.8rem 0.95rem 0.8rem 1rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  border-left: 3px solid var(--color-border-strong);
  transition: border-color 140ms var(--ease-out), box-shadow 140ms var(--ease-out),
    background 140ms var(--ease-out);
}
.alert-item:hover {
  background: #fff;
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-sm);
}
.alert-item.high {
  border-left-color: var(--color-destructive);
  background: rgba(220, 38, 38, 0.035);
}
.alert-item.high:hover {
  background: rgba(220, 38, 38, 0.05);
}
.alert-item.medium {
  border-left-color: var(--color-warning);
  background: rgba(217, 119, 6, 0.035);
}
.alert-item.medium:hover {
  background: rgba(217, 119, 6, 0.05);
}
.alert-item.low {
  border-left-color: var(--color-primary);
}
.alert-item.high .alert-title {
  color: var(--color-destructive);
}
.alert-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem 0.75rem;
}
.alert-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.4rem;
  min-width: 0;
}
.alert-title {
  font-weight: 650;
  color: var(--text-primary);
  font-size: 0.9rem;
}
.alert-time,
.alert-conf {
  font-style: normal;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  white-space: nowrap;
}
.alert-msg {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.6;
  word-break: break-word;
  font-size: 0.9rem;
}
.alert-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 0.85rem;
  padding-top: 0.35rem;
  border-top: 1px dashed var(--color-border);
  margin-top: 0.1rem;
}
.alert-foot-actions {
  justify-content: flex-end;
}
.alert-meta-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.85rem;
  min-width: 0;
  flex: 1 1 12rem;
}
.alert-kw {
  color: var(--text-tertiary);
  font-size: 0.78rem;
}
.alert-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
}
.link-out {
  color: var(--color-accent);
  font-size: 0.8rem;
  text-decoration: none;
  font-weight: 500;
}
.link-out:hover {
  text-decoration: underline;
  color: var(--color-primary);
}
.link-btn {
  appearance: none;
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
}
.review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  flex: 0 0 auto;
  margin-left: auto;
}
.alert-foot-actions .review-actions {
  margin-left: 0;
}
.review-select {
  width: 7.5rem;
  min-height: 1.9rem;
  padding: 0.2rem 0.45rem;
  font-size: 0.8rem;
}
.alert-no-post {
  margin: 0 0 0 auto;
  font-size: 0.78rem;
}

@media (max-width: 640px) {
  .alert-foot {
    flex-direction: column;
    align-items: stretch;
  }
  .review-actions,
  .alert-no-post {
    margin-left: 0;
  }
  .review-select {
    flex: 1;
    width: auto;
  }
}
</style>
