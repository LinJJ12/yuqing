<script setup>
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Play, RotateCcw, Sparkles } from '@lucide/vue'
import {
  fetchSentimentStats,
  previewSentiment,
  runSentiment,
} from '../api/client'

const loading = ref(false)
const message = ref('')
const error = ref('')
const stats = ref(null)
const sample = ref([])
const previewText = ref('三食堂排队太久，窗口太少，希望后勤尽快处理。')
const previewResult = ref(null)
const chartRef = ref(null)
let chart

const labelMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  unknown: '未标注',
}

const bertProgress = computed(() => {
  if (!stats.value?.total) return '0%'
  return `${Math.round((stats.value.bert_done / stats.value.total) * 100)}%`
})

function renderChart() {
  if (!chartRef.value || !stats.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const bert = { positive: 0, neutral: 0, negative: 0 }
  const lexicon = { positive: 0, neutral: 0, negative: 0 }
  for (const row of stats.value.breakdown || []) {
    const bucket = row.method === 'bert' ? bert : lexicon
    if (row.label in bucket) bucket[row.label] += row.count
  }
  chart.setOption({
    color: ['#1e40af', '#93c5fd'],
    tooltip: { trigger: 'axis' },
    legend: { data: ['模型分析', '词典快筛'], textStyle: { color: '#475569' } },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['正面', '中性', '负面'],
      axisLine: { lineStyle: { color: '#bfdbfe' } },
      axisLabel: { color: '#64748b' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#e9eef6' } },
      axisLabel: { color: '#64748b' },
    },
    series: [
      {
        name: '模型分析',
        type: 'bar',
        barMaxWidth: 28,
        data: [bert.positive, bert.neutral, bert.negative],
        itemStyle: { color: '#1e40af', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '词典快筛',
        type: 'bar',
        barMaxWidth: 28,
        data: [lexicon.positive, lexicon.neutral, lexicon.negative],
        itemStyle: { color: '#93c5fd', borderRadius: [4, 4, 0, 0] },
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

async function onRun(onlyPending = true) {
  loading.value = true
  error.value = ''
  message.value = onlyPending
    ? '正在分析待处理帖子（首次可能较慢，请稍候）…'
    : '正在全量重跑情感分析…'
  try {
    const res = await runSentiment({ limit: 1000, only_pending: onlyPending })
    if (!res.ok) {
      error.value = res.error?.message || '分析失败'
      return
    }
    stats.value = res.data.stats
    sample.value = res.data.sample || []
    message.value = `完成：更新 ${res.data.updated} 条，耗时 ${res.data.elapsed_ms} ms`
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

onMounted(async () => {
  try {
    await refreshStats()
  } catch {
    error.value = '无法连接后端'
  }
  window.addEventListener('resize', () => chart?.resize())
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>情感分析</h2>
      </div>
      <p class="hint">
        输出正面 / 中性 / 负面。首次运行可能需要加载模型，请稍候。
      </p>
      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="loading" @click="onRun(true)">
          <Play :size="16" />
          分析待处理
        </button>
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="onRun(false)">
          <RotateCcw :size="16" />
          全量重跑
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
          <div class="kpi-label"><span>进度</span></div>
          <div class="kpi-value">{{ bertProgress }}</div>
        </div>
      </div>
      <div ref="chartRef" class="chart-box" style="margin-top: 0.5rem" />
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
</style>
