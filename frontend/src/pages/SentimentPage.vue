<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Play, RotateCcw, Sparkles } from '@lucide/vue'
import {
  createAnalysisJob,
  fetchAnalysisJob,
  fetchAnalysisJobs,
  fetchReviewPosts,
  fetchSentimentStats,
  llmReviewSentiment,
  overridePostSentiment,
  previewSentiment,
  runSentiment,
} from '../api/client'

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
  llm: 'LLM',
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
  chart.setOption({
    color: ['#18181b', '#a1a1aa'],
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['模型分析', '词典快筛'],
      top: 0,
      left: 'center',
      textStyle: { color: '#52525b' },
    },
    grid: { left: 48, right: 20, top: 48, bottom: 40 },
    xAxis: {
      type: 'category',
      data: ['正面', '中性', '负面', '不确定'],
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
        name: '模型分析',
        type: 'bar',
        barMaxWidth: 28,
        data: [bert.positive, bert.neutral, bert.negative, bert.uncertain],
        itemStyle: { color: '#18181b', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '词典快筛',
        type: 'bar',
        barMaxWidth: 28,
        data: [lexicon.positive, lexicon.neutral, lexicon.negative, lexicon.uncertain],
        itemStyle: { color: '#a1a1aa', borderRadius: [4, 4, 0, 0] },
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
    const res = await fetchReviewPosts(40)
    if (res.ok) reviewPosts.value = res.data.items || []
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
    if (idx >= 0) reviewPosts.value[idx] = res.data
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
  message.value = `正在 LLM 复判 #${post.id}…`
  try {
    const res = await llmReviewSentiment({ post_id: post.id, apply: true })
    if (!res.ok) {
      error.value = res.error?.message || 'LLM 复判失败'
      return
    }
    const updated = res.data.post || res.data
    const idx = reviewPosts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0 && updated?.id) reviewPosts.value[idx] = updated
    const lab = res.data.sentiment_label
    message.value = `LLM 复判 #${post.id} → ${labelMap[lab] || lab}${res.data.reason ? `（${res.data.reason}）` : ''}`
    await refreshStats()
  } catch (e) {
    error.value = e.message || 'LLM 复判失败'
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

onMounted(async () => {
  try {
    await refreshStats()
    await refreshJobs()
    await refreshReview()
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>情感分析</h2>
      </div>
      <p class="hint">
        默认微博域三分类模型，输出正面 / 中性 / 负面（低置信为不确定）。入库不再写词典情感；采集后会自动排队 BERT。也可提交后台任务异步执行。
      </p>
      <p v-if="staleHint" class="warn-text">{{ staleHint }}</p>
      <div class="actions">
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
      </div>
      <p v-if="message" class="ok-text">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <div v-if="stats" class="kpi-grid" style="margin-top: 1rem">
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
      <div ref="chartRef" class="chart-box" style="margin-top: 0.5rem" />
    </section>

    <section v-if="jobs.length" class="panel">
      <div class="panel-head"><h3>最近任务</h3></div>
      <ul class="stack-list">
        <li v-for="job in jobs" :key="job.id">
          <span>{{ job.kind }} · {{ jobStatusMap[job.status] || job.status }} · {{ job.created_at }}</span>
          <b>{{ job.id.slice(0, 8) }}</b>
        </li>
      </ul>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>单句预览</h3>
      </div>
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
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>难例改判</h3>
        <button type="button" class="btn btn-ghost" :disabled="reviewLoading" @click="refreshReview">
          刷新
        </button>
      </div>
      <p class="hint">
        优先列出不确定 / 低置信评论。可手动改判，或一键 LLM 复判；人工与 LLM 结果不会被后续 BERT 覆盖。
      </p>
      <div v-if="reviewPosts.length" class="post-list">
        <article v-for="item in reviewPosts" :key="item.id" class="post-item">
          <header class="post-meta">
            <b>#{{ item.id }}</b>
            <span class="pill pill-default">
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
              LLM 复判
            </button>
          </div>
        </article>
      </div>
      <p v-else class="hint">{{ reviewLoading ? '加载中…' : '暂无待复核帖子' }}</p>
    </section>

    <section v-if="sample.length" class="panel">
      <div class="panel-head">
        <h3>本次样例</h3>
      </div>
      <div class="post-list">
        <article v-for="item in sample" :key="item.id" class="post-item">
          <header class="post-meta">
            <b>{{ labelMap[item.sentiment_label] || item.sentiment_label }}</b>
            <span class="pill pill-default">{{ item.confidence }}</span>
          </header>
          <p>{{ item.text }}</p>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 0.6rem;
  margin: 0.85rem 0;
  flex-wrap: wrap;
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
