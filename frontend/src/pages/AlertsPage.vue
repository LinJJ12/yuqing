<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from '@lucide/vue'
import { fetchAlerts, fetchTrends } from '../api/client'
import * as echarts from 'echarts'

const loading = ref(true)
const error = ref('')
const alerts = ref(null)
const chartRef = ref(null)
let chart

const severityMap = { high: '高', medium: '中', low: '低' }
const severityPill = {
  high: 'pill-danger',
  medium: 'pill-warning',
  low: 'pill-default',
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [a, t] = await Promise.all([fetchAlerts(50), fetchTrends(14)])
    if (!a.ok) throw new Error(a.error?.message || '预警加载失败')
    alerts.value = a.data
    if (t.ok) renderTrend(t.data.series || [])
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

function renderTrend(series) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['发帖量', '滑动平均'], textStyle: { color: '#475569' } },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: series.map((s) => s.day),
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
        name: '发帖量',
        type: 'bar',
        barMaxWidth: 22,
        data: series.map((s) => s.count),
        itemStyle: { color: '#93c5fd', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: '滑动平均',
        type: 'line',
        smooth: true,
        data: series.map((s) => s.rolling_mean),
        itemStyle: { color: '#1e40af' },
        lineStyle: { width: 2.5 },
      },
    ],
  })
}

onMounted(() => {
  refresh()
  window.addEventListener('resize', () => chart?.resize())
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>预警中心</h2>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
          <RefreshCw :size="14" />
          刷新
        </button>
      </div>
      <p class="hint">规则：负面情感 / 敏感词命中 + 日环比发帖量突增（≥50%）。</p>
      <p v-if="loading" class="muted" style="margin-top: 0.75rem">加载中…</p>
      <p v-else-if="error" class="err" style="margin-top: 0.75rem">{{ error }}</p>
      <div v-else-if="alerts" class="kpi-grid" style="margin-top: 1rem; margin-bottom: 0">
        <div class="kpi">
          <div class="kpi-label"><span>预警数</span></div>
          <div class="kpi-value">{{ alerts.count }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>高</span></div>
          <div class="kpi-value bad">{{ alerts.high }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>中</span></div>
          <div class="kpi-value warn">{{ alerts.medium }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label"><span>低</span></div>
          <div class="kpi-value">{{ alerts.low }}</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><h3>热度趋势</h3></div>
      <div ref="chartRef" class="chart-box" />
    </section>

    <section v-if="alerts?.items?.length" class="panel">
      <div class="panel-head"><h3>预警列表</h3></div>
      <article
        v-for="item in alerts.items"
        :key="item.id"
        class="alert-item"
        :class="item.severity"
      >
        <header class="post-meta">
          <b>{{ item.title }}</b>
          <span class="pill" :class="severityPill[item.severity] || 'pill-default'">
            {{ severityMap[item.severity] || item.severity }}
          </span>
          <em>{{ item.created_at }}</em>
        </header>
        <p>{{ item.message }}</p>
        <small v-if="item.keywords?.length">关键词：{{ item.keywords.join('、') }}</small>
      </article>
    </section>
    <section v-else-if="!loading && !error" class="panel">
      <p class="hint">暂无预警。可先到「情感」页完成分析，或导入含负面内容的样例。</p>
    </section>
  </div>
</template>

<style scoped>
.alert-item {
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--bg-tertiary);
}
.alert-item:last-child {
  border-bottom: none;
}
.alert-item.high b {
  color: var(--color-destructive);
}
.alert-item p {
  margin: 0.35rem 0;
  color: var(--text-secondary);
}
.alert-item small {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}
</style>
