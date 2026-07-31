<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { RefreshCw } from '@lucide/vue'
import { fetchAlerts, fetchTrends } from '../api/client'
import * as echarts from 'echarts'
import PageHeader from '../components/PageHeader.vue'

const loading = ref(true)
const error = ref('')
const alerts = ref(null)
const prophetHint = ref('')
const severityFilter = ref('all') // all | high | medium | low
const chartRef = ref(null)
let chart

const severityMap = { high: '高风险', medium: '中风险', low: '低风险' }
const severityPill = {
  high: 'pill-danger',
  medium: 'pill-warning',
  low: 'pill-default',
}

const filterTabs = computed(() => {
  const a = alerts.value
  return [
    { value: 'all', label: '全部', count: a?.count ?? a?.items?.length ?? 0 },
    { value: 'high', label: '高风险', count: a?.high ?? 0 },
    { value: 'medium', label: '中风险', count: a?.medium ?? 0 },
    { value: 'low', label: '低风险', count: a?.low ?? 0 },
  ]
})

const filteredItems = computed(() => {
  const items = alerts.value?.items || []
  if (severityFilter.value === 'all') return items
  return items.filter((item) => item.severity === severityFilter.value)
})

function setFilter(value) {
  severityFilter.value = value
}

function renderTrend(series, prophetMeta) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const hasProphet = series.some((s) => s.prophet_yhat != null)
  chart.setOption({
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
      data: series.map((s) => s.day),
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
        data: series.map((s) => (s.is_forecast ? null : s.count)),
        itemStyle: { color: '#e4e4e7', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '滑动平均',
        type: 'line',
        smooth: true,
        data: series.map((s) => (s.is_forecast ? null : s.rolling_mean)),
        itemStyle: { color: '#0f766e' },
        lineStyle: { width: 2.5, color: '#0f766e' },
      },
      ...(hasProphet
        ? [
            {
              name: '智能预测',
              type: 'line',
              smooth: true,
              data: series.map((s) => s.prophet_yhat),
              itemStyle: { color: '#d97706' },
              lineStyle: { width: 2, type: 'dashed', color: '#d97706' },
            },
          ]
        : []),
    ],
  })
  prophetHint.value = prophetMeta?.enabled
    ? `智能预测已启用，向前预测 ${prophetMeta.horizon_days || 7} 天`
    : prophetMeta?.message || ''
}

function onResize() {
  chart?.resize()
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [a, t] = await Promise.all([fetchAlerts(50), fetchTrends(14)])
    if (!a.ok) throw new Error(a.error?.message || '预警加载失败')
    alerts.value = a.data
    if (t.ok) renderTrend(t.data.series || [], t.data.prophet)
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

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
    <PageHeader title="预警中心" subtitle="负面 / 敏感词 · 热度突增">
      <template #actions>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
          <RefreshCw :size="14" />
          刷新
        </button>
      </template>
    </PageHeader>

    <section class="panel">
      <p class="hint" style="margin-top: 0">
        规则：负面情感 / 敏感词命中 + 日环比发帖量突增（≥50%）。敏感词可在「设置」页修改。点击下方卡片或标签可筛选风险等级。
      </p>
      <p v-if="loading" class="muted" style="margin-top: 0.75rem">加载中…</p>
      <p v-else-if="error" class="err" style="margin-top: 0.75rem">{{ error }}</p>
      <div v-else-if="alerts" class="kpi-grid" style="margin-top: 1rem; margin-bottom: 0">
        <button
          type="button"
          class="kpi kpi-btn"
          :class="{ active: severityFilter === 'all' }"
          @click="setFilter('all')"
        >
          <div class="kpi-label"><span>预警数</span></div>
          <div class="kpi-value">{{ alerts.count }}</div>
        </button>
        <button
          type="button"
          class="kpi kpi-btn"
          :class="{ active: severityFilter === 'high' }"
          @click="setFilter('high')"
        >
          <div class="kpi-label"><span>高风险</span></div>
          <div class="kpi-value bad">{{ alerts.high }}</div>
        </button>
        <button
          type="button"
          class="kpi kpi-btn"
          :class="{ active: severityFilter === 'medium' }"
          @click="setFilter('medium')"
        >
          <div class="kpi-label"><span>中风险</span></div>
          <div class="kpi-value warn">{{ alerts.medium }}</div>
        </button>
        <button
          type="button"
          class="kpi kpi-btn"
          :class="{ active: severityFilter === 'low' }"
          @click="setFilter('low')"
        >
          <div class="kpi-label"><span>低风险</span></div>
          <div class="kpi-value">{{ alerts.low }}</div>
        </button>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>热度趋势</h3>
      </div>
      <p v-if="prophetHint" class="hint">{{ prophetHint }}</p>
      <div ref="chartRef" class="chart-box" />
    </section>

    <section v-if="alerts?.items?.length" class="panel list-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            v-for="tab in filterTabs"
            :key="tab.value"
            type="button"
            class="ui-tab"
            :class="{ active: severityFilter === tab.value }"
            role="tab"
            @click="setFilter(tab.value)"
          >
            {{ tab.label }}
            <span class="tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <div class="ui-tabs-body">
          <article
            v-for="item in filteredItems"
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
            </div>
          </article>
          <p v-if="!filteredItems.length" class="hint">
            {{
              severityFilter === 'all'
                ? '暂无预警。'
                : `当前筛选下暂无「${severityMap[severityFilter] || severityFilter}」预警。`
            }}
          </p>
        </div>
      </div>
    </section>
    <section v-else-if="!loading && !error" class="panel">
      <p class="hint">
        暂无预警。建议路径：
        <RouterLink to="/monitor">监测</RouterLink>
        采 BV →
        <RouterLink to="/sentiment">情感</RouterLink>
        跑完 →
        <RouterLink to="/settings">设置</RouterLink>
        核对敏感词。负面评论经情感标注后会出现在此。
      </p>
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

.alert-item {
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--color-border);
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
.alert-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.35rem;
}
.alert-item small {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}
</style>
