<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { Play, RotateCcw, Sparkles } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import CollapsiblePanel from '../components/CollapsiblePanel.vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import {
  createAnalysisJob,
  fetchAnalysisJob,
  fetchAnalysisJobs,
  fetchSentimentStats,
  previewSentiment,
  runSentiment,
} from '../api/client'
import { formatDateTime } from '../lib/datetime'

const PAGE_SIZE = 20
const route = useRoute()
const activeBvid = computed(() => String(route.query.bvid || '').trim())
const scopeOpts = () => (activeBvid.value ? { bvid: activeBvid.value } : {})

const toolTab = ref('preview')
const sentimentFilter = ref('all')
const samplePage = ref(1)

const loading = ref(false)
const jobLoading = ref(false)
const message = ref('')
const error = ref('')
const stats = ref(null)
const sample = ref([])
const jobs = ref([])
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
  chart.setOption(
    {
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
    },
    true,
  )
  requestAnimationFrame(() => chart?.resize())
}

async function refreshStats() {
  const res = await fetchSentimentStats(scopeOpts())
  if (res.ok) {
    stats.value = res.data
    await nextTick()
    renderChart()
  } else {
    error.value = res.error?.message || '统计加载失败'
  }
}

async function onRun(onlyPending = true) {
  loading.value = true
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
      error.value = res.error?.message || '分析失败'
      return
    }
    stats.value = res.data.stats
    sample.value = res.data.sample || []
    if (sample.value.length) toolTab.value = 'sample'
    message.value = `完成：更新 ${res.data.updated} 条，耗时 ${res.data.elapsed_ms} ms。难例请到预警页改判。`
    await nextTick()
    renderChart()
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

async function reloadScoped() {
  try {
    await refreshStats()
  } catch {
    error.value = '无法连接后端'
  }
}

watch(activeBvid, () => {
  sample.value = []
  message.value = activeBvid.value
    ? `已切换到视频 ${activeBvid.value}`
    : '已切换到全部视频'
  reloadScoped()
})

function onResize() {
  chart?.resize()
}

function onChartToggle(open) {
  if (!open) return
  nextTick(() => {
    renderChart()
    requestAnimationFrame(() => chart?.resize())
  })
}

onMounted(async () => {
  try {
    await refreshStats()
    await refreshJobs()
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
    <PageHeader title="情感分析" subtitle="正面 / 中性 / 负面 · 跑批与分布">
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

    <VideoScopePicker :disabled="loading || jobLoading" />

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
    </div>

    <p class="hint review-jump">
      难例改判与预警列表已合并到
      <RouterLink :to="{ path: '/alerts', query: { ...(activeBvid ? { bvid: activeBvid } : {}), tab: 'review' } }">
        预警中心
      </RouterLink>
      ，改完可直接切「预警列表」核对。
    </p>

    <CollapsiblePanel
      title="情感分布"
      storage-key="yuqing.sentiment.chart.v2"
      :default-open="true"
      @toggle="onChartToggle"
    >
      <div ref="chartRef" class="chart-box chart-compact" />
    </CollapsiblePanel>

    <section class="panel tools-panel">
      <div class="ui-tabs">
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
              <span>{{ job.kind }} · {{ jobStatusMap[job.status] || job.status }} · {{ formatDateTime(job.created_at) }}</span>
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
          <div v-if="pagedSample.length" class="post-list review-scroll">
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
    </section>
  </div>
</template>

<style scoped>
.review-jump {
  margin: 0 0 0.85rem;
}
.tools-panel {
  padding-top: 0.65rem;
}
.sentiment-filter {
  margin-bottom: 0.85rem;
  flex-wrap: wrap;
}
.review-scroll {
  max-height: min(40vh, 22rem);
  overflow: auto;
  padding-right: 0.15rem;
}
.preview-box {
  margin-top: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
