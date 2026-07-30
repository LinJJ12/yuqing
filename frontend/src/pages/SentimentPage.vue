<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Play, RotateCcw, Sparkles } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import {
  createAnalysisJob,
  fetchAnalysisJob,
  fetchAnalysisJobs,
  fetchPosts,
  fetchReviewPosts,
  fetchSentimentStats,
  llmReviewSentiment,
  overridePostSentiment,
  previewSentiment,
  runSentiment,
} from '../api/client'

const toolTab = ref('review')
const sentimentFilter = ref('all') // all | positive | neutral | negative | uncertain

const loading = ref(false)
const jobLoading = ref(false)
const message = ref('')
const error = ref('')
const stats = ref(null)
const sample = ref([])
const jobs = ref([])
const reviewPosts = ref([])
const reviewLoading = ref(false)
const reviewBusyId = ref(null)
const previewText = ref('这期剪辑节奏不错，但中段广告有点长，希望能改进。')
const previewResult = ref(null)
const chartRef = ref(null)
let chart
let pollTimer = null

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

const filteredSample = computed(() => {
  const items = sample.value || []
  if (sentimentFilter.value === 'all') return items
  return items.filter((p) => (p.sentiment_label || 'unknown') === sentimentFilter.value)
})

function setSentimentFilter(value) {
  sentimentFilter.value = value
}

function sentimentPillClass(label) {
  if (label === 'positive') return 'pill-success'
  if (label === 'negative') return 'pill-danger'
  if (label === 'uncertain') return 'pill-warning'
  return 'pill-default'
}

async function refreshJobs() {
  const res = await fetchAnalysisJobs(8)
  if (res.ok) jobs.value = res.data.items || []
}

async function onAsyncJob(kind = 'sentiment') {
  jobLoading.value = true
  error.value = ''
  message.value = '已提交后台任务…'
  try {
    const res = await createAnalysisJob({
      kind,
      limit: 5000,
      only_pending: true,
      use_bertopic: true,
    })
    if (!res.ok) {
      error.value = res.error?.message || '任务创建失败'
      jobLoading.value = false
      return
    }
    const jobId = res.data.id
    message.value = `任务 ${jobId.slice(0, 8)}… 已排队`
    await refreshJobs()
    clearInterval(pollTimer)
    pollTimer = setInterval(async () => {
      const detail = await fetchAnalysisJob(jobId)
      if (!detail.ok) return
      await refreshJobs()
      if (detail.data.status === 'succeeded') {
        clearInterval(pollTimer)
        pollTimer = null
        message.value = `后台任务完成（${kind}）`
        await refreshStats()
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

function renderChart() {
  if (!chartRef.value || !stats.value) return
  if (!chart) chart = echarts.init(chartRef.value)
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
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['模型分析', '词典快筛'],
      top: 0,
      left: 'center',
      textStyle: { color: '#64748b' },
    },
    grid: { left: 48, right: 20, top: 48, bottom: 40 },
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
        barMaxWidth: 28,
        data: cats.map((k) => ({
          value: bert[k],
          itemStyle: { color: colors[k], borderRadius: [4, 4, 0, 0] },
        })),
      },
      {
        name: '词典快筛',
        type: 'bar',
        barMaxWidth: 28,
        data: cats.map((k) => ({
          value: lexicon[k],
          itemStyle: { color: soft[k], borderRadius: [4, 4, 0, 0] },
        })),
      },
    ],
  })
}

async function refreshStats() {
  const res = await fetchSentimentStats()
  if (res.ok) {
    stats.value = res.data
    renderChart()
  }
}

async function refreshReview() {
  reviewLoading.value = true
  try {
    const settled = await Promise.allSettled([
      fetchReviewPosts(80),
      fetchPosts({ label: 'positive', limit: 30, order: 'fetched' }),
      fetchPosts({ label: 'neutral', limit: 30, order: 'fetched' }),
      fetchPosts({ label: 'negative', limit: 30, order: 'fetched' }),
      fetchPosts({ label: 'uncertain', limit: 30, order: 'fetched' }),
    ])
    const byId = new Map()
    for (const item of settled) {
      if (item.status !== 'fulfilled' || !item.value?.ok) continue
      for (const p of item.value.data?.items || []) {
        byId.set(p.id, p)
      }
    }
    reviewPosts.value = [...byId.values()].sort((a, b) => {
      const ca = Number(a.sentiment_confidence)
      const cb = Number(b.sentiment_confidence)
      const va = Number.isFinite(ca) ? ca : 1
      const vb = Number.isFinite(cb) ? cb : 1
      return va - vb
    })
  } catch (e) {
    error.value = e.message || '加载评论失败'
  } finally {
    reviewLoading.value = false
  }
}

async function onManualOverride(post, label) {
  if (!label || (label === post.sentiment_label && post.sentiment_method === 'manual')) return
  reviewBusyId.value = post.id
  error.value = ''
  try {
    const res = await overridePostSentiment(post.id, { label, method: 'manual' })
    if (!res.ok) {
      error.value = res.error?.message || '改判失败'
      return
    }
    const idx = reviewPosts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0) reviewPosts.value[idx] = res.data?.id ? res.data : { ...post, ...res.data }
    message.value = `已人工改判 #${post.id} → ${labelMap[label] || label}`
    await refreshStats()
  } catch (e) {
    error.value = e.message || '改判失败'
  } finally {
    reviewBusyId.value = null
  }
}

async function onLlmReview(post) {
  reviewBusyId.value = post.id
  error.value = ''
  message.value = `正在智能复判 #${post.id}…`
  try {
    const res = await llmReviewSentiment({ post_id: post.id, apply: true })
    if (!res.ok) {
      error.value = res.error?.message || '智能复判失败'
      return
    }
    const updated = res.data.post || res.data
    const idx = reviewPosts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0 && updated?.id) reviewPosts.value[idx] = updated
    const lab = res.data.sentiment_label
    message.value = `智能复判 #${post.id} → ${labelMap[lab] || lab}${res.data.reason ? `（${res.data.reason}）` : ''}`
    await refreshStats()
  } catch (e) {
    error.value = e.message || '智能复判失败'
  } finally {
    reviewBusyId.value = null
  }
}

async function onRun(onlyPending = true) {
  loading.value = true
  error.value = ''
  message.value = onlyPending
    ? '正在分析待处理帖子（首次可能较慢，请稍候）…'
    : '正在全量重跑情感分析…'
  try {
    const res = await runSentiment({ limit: 5000, only_pending: onlyPending })
    if (!res.ok) {
      error.value = res.error?.message || '分析失败'
      return
    }
    stats.value = res.data.stats
    sample.value = res.data.sample || []
    message.value = `完成：更新 ${res.data.updated} 条，耗时 ${res.data.elapsed_ms} ms`
    renderChart()
    await refreshReview()
  } catch (e) {
    error.value = e?.response?.data?.error?.message || e.message || '请求失败'
  } finally {
    loading.value = false
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

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  try {
    await refreshStats()
    await refreshJobs()
    await refreshReview()
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="page">
    <PageHeader title="情感分析" subtitle="正面 / 中性 / 负面 · 低置信为不确定">
      <template #actions>
        <button type="button" class="btn btn-primary" :disabled="loading || jobLoading" @click="onRun(true)">
          <Play :size="16" />
          分析待处理
        </button>
        <button type="button" class="btn btn-secondary" :disabled="loading || jobLoading" @click="onRun(false)">
          <RotateCcw :size="16" />
          全量重跑
        </button>
        <button type="button" class="btn btn-secondary" :disabled="loading || jobLoading" @click="onAsyncJob('sentiment')">
          <Sparkles :size="16" />
          后台任务
        </button>
      </template>
    </PageHeader>

    <p v-if="staleHint" class="warn-text" style="margin-top: 0; margin-bottom: 0.75rem">{{ staleHint }}</p>
    <p v-if="message" class="ok-text" style="margin: 0 0 0.5rem">{{ message }}</p>
    <p v-if="error" class="err" style="margin: 0 0 0.5rem">{{ error }}</p>

    <div v-if="stats" class="kpi-grid">
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
    </div>

    <section class="panel">
      <div class="panel-head">
        <h3>情感分布</h3>
      </div>
      <div ref="chartRef" class="chart-box" />
    </section>

    <section class="panel tools-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            type="button"
            class="ui-tab"
            :class="{ active: toolTab === 'review' }"
            @click="toolTab = 'review'"
          >
            难例改判
          </button>
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

        <div v-show="toolTab === 'review'" class="ui-tabs-body">
          <div class="toolbar" style="margin-bottom: 0.65rem">
            <p class="hint" style="margin: 0">
              按情感切换浏览；人工与智能复判结果不会被后续模型覆盖。
            </p>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="reviewLoading" @click="refreshReview">
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

          <div v-if="filteredReviewPosts.length" class="post-list">
            <article v-for="item in filteredReviewPosts" :key="item.id" class="post-item">
              <header class="post-meta">
                <b>#{{ item.id }}</b>
                <span class="pill" :class="sentimentPillClass(item.sentiment_label)">
                  {{ labelMap[item.sentiment_label] || item.sentiment_label || '未标注' }}
                </span>
                <span class="pill pill-default">
                  {{ methodMap[item.sentiment_method] || item.sentiment_method || '—' }}
                </span>
                <em v-if="item.sentiment_confidence != null">置信 {{ item.sentiment_confidence }}</em>
              </header>
              <p>{{ item.text }}</p>
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
                  class="btn btn-secondary"
                  :disabled="reviewBusyId === item.id"
                  @click="onLlmReview(item)"
                >
                  智能复判
                </button>
              </div>
            </article>
          </div>
          <p v-else class="hint">
            {{
              reviewLoading
                ? '加载中…'
                : sentimentFilter === 'all'
                  ? '暂无待浏览帖子'
                  : `当前筛选下暂无「${labelMap[sentimentFilter]}」帖子`
            }}
          </p>
        </div>

        <div v-show="toolTab === 'preview'" class="ui-tabs-body">
          <textarea v-model="previewText" class="textarea" rows="3" />
          <button type="button" class="btn btn-primary" style="margin-top: 0.65rem" :disabled="loading" @click="onPreview">
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
              <span>{{ job.kind }} · {{ jobStatusMap[job.status] || job.status }} · {{ job.created_at }}</span>
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
          <div v-if="filteredSample.length" class="post-list">
            <article v-for="item in filteredSample" :key="item.id" class="post-item">
              <header class="post-meta">
                <b>{{ labelMap[item.sentiment_label] || item.sentiment_label }}</b>
                <span class="pill pill-default">{{ item.confidence }}</span>
              </header>
              <p>{{ item.text }}</p>
            </article>
          </div>
          <p v-else class="hint">当前筛选下暂无样例。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tools-panel {
  padding-top: 0.65rem;
}
.sentiment-filter {
  margin-bottom: 0.85rem;
  flex-wrap: wrap;
}
.sentiment-filter em {
  font-style: normal;
  margin-left: 0.2rem;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-family: var(--font-mono);
}
.sentiment-filter button.active em {
  color: var(--color-primary);
}
.preview-box {
  margin-top: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
.review-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.55rem;
  align-items: center;
}
.review-select {
  max-width: 9rem;
  min-height: 2.1rem;
}
</style>
