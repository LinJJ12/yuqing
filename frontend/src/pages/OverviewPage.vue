<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import * as echarts from 'echarts'
import {
  MessageSquareText,
  Tags,
  ThumbsUp,
  ThumbsDown,
  Activity,
  ExternalLink,
} from '@lucide/vue'
import { fetchOverview, fetchTrends } from '../api/client'

const loading = ref(true)
const error = ref('')
const overview = ref(null)
const trendSeries = ref([])
const clock = ref('')

const sentimentRef = ref(null)
const platformRef = ref(null)
const topicRef = ref(null)
const trendRef = ref(null)
let sentimentChart
let platformChart
let topicChart
let trendChart
let clockTimer

const sentimentMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}

const sentimentColor = {
  positive: '#16a34a',
  neutral: '#64748b',
  negative: '#dc2626',
  uncertain: '#d97706',
  unknown: '#94a3b8',
}

const platformMap = {
  bili: 'B站',
  campus: '样例/导入',
  xhs: '小红书',
  dy: '抖音',
  wb: '微博',
}

const total = computed(() => overview.value?.total_posts ?? 0)
const topicCount = computed(() => overview.value?.by_topic?.length ?? 0)
const analyzedRate = computed(() => {
  if (!total.value) return '0%'
  const labeled = (overview.value?.by_sentiment || [])
    .filter((x) => x.label && x.label !== 'unknown')
    .reduce((s, x) => s + x.count, 0)
  return `${Math.round((labeled / total.value) * 100)}%`
})

function sentimentCount(label) {
  const row = overview.value?.by_sentiment?.find((x) => x.label === label)
  return row?.count ?? 0
}

const positiveCount = computed(() => sentimentCount('positive'))
const negativeCount = computed(() => sentimentCount('negative'))
const neutralCount = computed(() => sentimentCount('neutral'))
const trendTotal = computed(() =>
  trendSeries.value.filter((s) => !s.is_forecast).reduce((a, s) => a + (s.count || 0), 0),
)

function platformLabel(code) {
  return platformMap[code] || code || '—'
}

function videoTitle(post) {
  return post?.raw?.extra?.video_title || ''
}

function tickClock() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  clock.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

const axisText = '#64748b'
const axisLine = '#e2e8f0'
const splitLine = '#f1f5f9'

function ensureChart(instance, el) {
  if (!el) return null
  if (instance && !instance.isDisposed?.()) {
    const dom = instance.getDom?.()
    if (dom === el) return instance
    instance.dispose()
  }
  return echarts.init(el)
}

function renderSentiment() {
  sentimentChart = ensureChart(sentimentChart, sentimentRef.value)
  if (!sentimentChart) return
  const rows = overview.value?.by_sentiment || []
  const data = rows.map((r) => ({
    name: sentimentMap[r.label] || r.label,
    value: r.count,
    itemStyle: { color: sentimentColor[r.label] || '#94a3b8' },
  }))
  sentimentChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        bottom: 0,
        left: 'center',
        textStyle: { color: axisText, fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      series: [
        {
          type: 'pie',
          radius: ['48%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          label: { color: '#334155', fontSize: 11 },
          labelLine: { lineStyle: { color: '#cbd5e1' } },
          data: data.length
            ? data
            : [{ name: '暂无', value: 1, itemStyle: { color: '#e2e8f0' } }],
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '38%',
          style: {
            text: String(total.value),
            fill: '#0f172a',
            fontSize: 26,
            fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace',
            textAlign: 'center',
          },
        },
        {
          type: 'text',
          left: 'center',
          top: '50%',
          style: {
            text: '总量',
            fill: axisText,
            fontSize: 12,
            textAlign: 'center',
          },
        },
      ],
    },
    true,
  )
}

function renderPlatform() {
  platformChart = ensureChart(platformChart, platformRef.value)
  if (!platformChart) return
  const rows = [...(overview.value?.by_platform || [])].sort((a, b) => b.count - a.count)
  platformChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 16, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => platformLabel(r.platform)),
        axisLine: { lineStyle: { color: axisLine } },
        axisLabel: { color: axisText, fontSize: 11 },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: splitLine } },
        axisLabel: { color: axisText },
      },
      series: [
        {
          type: 'bar',
          barMaxWidth: 36,
          data: rows.map((r) => r.count),
          itemStyle: {
            borderRadius: [4, 4, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#14b8a6' },
              { offset: 1, color: '#0f766e' },
            ]),
          },
        },
      ],
    },
    true,
  )
}

function renderTopics() {
  topicChart = ensureChart(topicChart, topicRef.value)
  if (!topicChart) return
  const rows = [...(overview.value?.by_topic || [])].slice(0, 10).reverse()
  if (!rows.length) {
    topicChart.clear()
    topicChart.setOption({
      title: {
        text: '暂无话题数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 400 },
      },
    })
    return
  }
  topicChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 88, right: 36, top: 12, bottom: 12 },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: splitLine } },
        axisLabel: { color: axisText },
      },
      yAxis: {
        type: 'category',
        data: rows.map((r) => r.topic),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: axisText, fontSize: 11, width: 72, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          barMaxWidth: 14,
          data: rows.map((r) => r.count),
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#0284c7' },
              { offset: 1, color: '#38bdf8' },
            ]),
          },
          label: {
            show: true,
            position: 'right',
            color: '#64748b',
            fontSize: 11,
          },
        },
      ],
    },
    true,
  )
}

function renderTrend() {
  trendChart = ensureChart(trendChart, trendRef.value)
  if (!trendChart) return
  const series = trendSeries.value || []
  if (!series.length) {
    trendChart.clear()
    trendChart.setOption({
      title: {
        text: '暂无趋势数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 400 },
      },
    })
    return
  }
  trendChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['发帖量', '滑动平均'],
        top: 0,
        right: 0,
        textStyle: { color: axisText, fontSize: 11 },
      },
      grid: { left: 44, right: 16, top: 36, bottom: 28 },
      xAxis: {
        type: 'category',
        data: series.map((s) => s.day),
        boundaryGap: false,
        axisLine: { lineStyle: { color: axisLine } },
        axisLabel: { color: axisText, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: splitLine } },
        axisLabel: { color: axisText },
      },
      series: [
        {
          name: '发帖量',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 5,
          data: series.map((s) => (s.is_forecast ? null : s.count)),
          lineStyle: { width: 2.5, color: '#0f766e' },
          itemStyle: { color: '#0f766e' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(15, 118, 110, 0.22)' },
              { offset: 1, color: 'rgba(15, 118, 110, 0.02)' },
            ]),
          },
        },
        {
          name: '滑动平均',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: series.map((s) => (s.is_forecast ? null : s.rolling_mean)),
          lineStyle: { width: 1.5, color: '#0284c7', type: 'dashed' },
          itemStyle: { color: '#0284c7' },
        },
      ],
    },
    true,
  )
}

function renderAll() {
  renderPlatform()
  renderSentiment()
  renderTopics()
  renderTrend()
  requestAnimationFrame(() => {
    platformChart?.resize()
    sentimentChart?.resize()
    topicChart?.resize()
    trendChart?.resize()
  })
}

function onResize() {
  platformChart?.resize()
  sentimentChart?.resize()
  topicChart?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 1000)
  window.addEventListener('resize', onResize)
  try {
    const [o, t] = await Promise.all([fetchOverview(), fetchTrends(14)])
    if (!o.ok) {
      error.value = o.error?.message || '总览加载失败'
      return
    }
    overview.value = o.data
    if (t.ok) trendSeries.value = t.data.series || []
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  } finally {
    loading.value = false
  }
  // 等 loading=false 后图表 DOM 才挂载，再绘制
  await nextTick()
  if (total.value > 0) renderAll()
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  window.removeEventListener('resize', onResize)
  sentimentChart?.dispose()
  platformChart?.dispose()
  topicChart?.dispose()
  trendChart?.dispose()
  sentimentChart = null
  platformChart = null
  topicChart = null
  trendChart = null
})
</script>

<template>
  <div class="page overview-screen">
    <header class="screen-head">
      <div>
        <h2 class="screen-title">知微可视化总览</h2>
        <p class="screen-sub">采集量 · 情感结构 · 话题热度 · 入库动态</p>
      </div>
      <div class="screen-meta">
        <span class="live-dot" aria-hidden="true" />
        <span>{{ clock }}</span>
      </div>
    </header>

    <div v-if="loading" class="screen-card">
      <div class="skeleton" style="width: 40%; margin-bottom: 0.75rem" />
      <div class="skeleton" style="width: 70%" />
    </div>
    <p v-else-if="error" class="screen-card err">{{ error }}</p>

    <template v-else-if="total === 0">
      <section class="screen-card first-run">
        <h3>开始第一次演示</h3>
        <p class="first-run-lead">
          库内还没有帖子。按下面三步即可跑通「采集 → 情感 → 口碑」。
        </p>
        <ol class="first-run-steps">
          <li>
            <b>监测：贴 BV 采集评论</b>
            <p>打开监测页，粘贴 B 站视频链接或 BV 号，开始采集并入库。</p>
            <RouterLink class="btn btn-primary btn-sm" to="/monitor">去监测</RouterLink>
          </li>
          <li>
            <b>情感：确认分析完成</b>
            <p>采集后会自动排队情感分析；也可在情感页手动跑批。</p>
            <RouterLink class="btn btn-secondary btn-sm" to="/sentiment">去情感</RouterLink>
          </li>
          <li>
            <b>报告：看单视频口碑</b>
            <p>情感跑完后，在报告页查看该视频的口碑结论与样例评论。</p>
            <RouterLink class="btn btn-secondary btn-sm" to="/reports">去报告</RouterLink>
          </li>
        </ol>
        <p class="hint">
          演示前可先到
          <RouterLink to="/settings">设置</RouterLink>
          检查情感模型缓存与 B 站 Cookie 是否就绪。
        </p>
      </section>
    </template>

    <template v-else>
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-top">
            <span>帖子总量</span>
            <MessageSquareText :size="15" />
          </div>
          <div class="kpi-num">{{ total }}</div>
          <div class="kpi-foot">已标注 {{ analyzedRate }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-top">
            <span>话题数</span>
            <Tags :size="15" />
          </div>
          <div class="kpi-num">{{ topicCount }}</div>
          <div class="kpi-foot">库内标签聚合</div>
        </div>
        <div class="kpi-card accent-pos">
          <div class="kpi-top">
            <span>正面</span>
            <ThumbsUp :size="15" />
          </div>
          <div class="kpi-num pos">{{ positiveCount }}</div>
          <div class="kpi-foot">中性 {{ neutralCount }}</div>
        </div>
        <div class="kpi-card accent-neg">
          <div class="kpi-top">
            <span>负面</span>
            <ThumbsDown :size="15" />
          </div>
          <div class="kpi-num neg">{{ negativeCount }}</div>
          <div class="kpi-foot">需关注口碑风险</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-top">
            <span>近 14 日</span>
            <Activity :size="15" />
          </div>
          <div class="kpi-num sm">{{ trendTotal }}</div>
          <div class="kpi-foot">趋势区间发帖量</div>
        </div>
      </div>

      <div class="viz-grid">
        <section class="screen-card">
          <div class="card-head">
            <h3>数据来源</h3>
            <span>平台对比</span>
          </div>
          <div ref="platformRef" class="chart" />
        </section>

        <section class="screen-card">
          <div class="card-head">
            <h3>情感结构</h3>
            <span>占比环形图</span>
          </div>
          <div ref="sentimentRef" class="chart" />
        </section>

        <section class="screen-card">
          <div class="card-head">
            <h3>话题热度</h3>
            <span>前 10</span>
          </div>
          <div ref="topicRef" class="chart chart-tall" />
        </section>
      </div>

      <div class="bottom-grid">
        <section class="screen-card">
          <div class="card-head">
            <h3>入库趋势</h3>
            <span>近 14 日 · 滑动平均</span>
          </div>
          <div ref="trendRef" class="chart chart-trend" />
        </section>

        <section class="screen-card feed-card">
          <div class="card-head">
            <h3>最近入库</h3>
            <span>实时动态</span>
          </div>
          <div v-if="overview.recent_posts?.length" class="feed">
            <article
              v-for="post in overview.recent_posts.slice(0, 8)"
              :key="post.id"
              class="feed-item"
            >
              <header>
                <b>{{ post.topic || '未分类' }}</b>
                <span>{{ platformLabel(post.platform) }}</span>
                <em
                  :style="{
                    color: sentimentColor[post.sentiment_label] || '#64748b',
                  }"
                >
                  {{ sentimentMap[post.sentiment_label] || post.sentiment_label || '—' }}
                </em>
              </header>
              <p v-if="videoTitle(post)" class="feed-sub">{{ videoTitle(post) }}</p>
              <p class="feed-text">{{ post.text }}</p>
              <footer>
                <time>{{ post.fetched_at || post.published_at }}</time>
                <a
                  v-if="post.source_url"
                  :href="post.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink :size="12" />
                  原帖
                </a>
              </footer>
            </article>
          </div>
          <div v-else class="empty">还没有帖子。请打开「监测」采集。</div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.first-run {
  max-width: 40rem;
  padding: 1.25rem 1.35rem 1.4rem;
}
.first-run h3 {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
}
.first-run-lead {
  margin: 0 0 1rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}
.first-run-steps {
  margin: 0 0 1rem;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.first-run-steps li {
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
}
.first-run-steps b {
  display: block;
  margin-bottom: 0.25rem;
}
.first-run-steps p {
  margin: 0 0 0.55rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.45;
}
.overview-screen {
  color: var(--text-primary);
}

.screen-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 0.9rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border);
}
.screen-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}
.screen-sub {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}
.screen-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-tertiary);
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #16a34a;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.kpi-card {
  position: relative;
  padding: 0.9rem 1rem;
  border-radius: var(--radius-lg);
  background: #fff;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-panel);
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-primary);
}
.kpi-card.accent-pos::before {
  background: #16a34a;
}
.kpi-card.accent-neg::before {
  background: #dc2626;
}
.kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-tertiary);
  font-size: 0.78rem;
  margin-bottom: 0.45rem;
}
.kpi-num {
  font-family: var(--font-mono);
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--text-primary);
}
.kpi-num.sm {
  font-size: 1.35rem;
}
.kpi-num.pos {
  color: #16a34a;
}
.kpi-num.neg {
  color: #dc2626;
}
.kpi-foot {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: var(--text-tertiary);
}

.viz-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1.15fr;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.bottom-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 0.75rem;
}

.screen-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  padding: 0.85rem 0.95rem 0.7rem;
  min-width: 0;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}
.card-head h3 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 650;
  color: var(--text-primary);
}
.card-head span {
  font-size: 0.72rem;
  color: var(--text-tertiary);
}

.chart {
  height: 260px;
  width: 100%;
}
.chart-tall,
.chart-trend {
  height: 280px;
}

.empty {
  display: grid;
  place-items: center;
  min-height: 180px;
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.feed {
  max-height: 280px;
  overflow: auto;
}
.feed-item {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--color-border);
}
.feed-item:last-child {
  border-bottom: none;
}
.feed-item header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
  margin-bottom: 0.25rem;
  font-size: 0.78rem;
}
.feed-item header b {
  color: var(--text-primary);
}
.feed-item header span {
  color: var(--text-tertiary);
}
.feed-item header em {
  font-style: normal;
  font-weight: 600;
}
.feed-sub {
  margin: 0 0 0.2rem;
  font-size: 0.72rem;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.feed-text {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feed-item footer {
  margin-top: 0.35rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.72rem;
  color: var(--text-tertiary);
}
.feed-item footer a {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--color-primary);
  text-decoration: none;
}
.feed-item footer a:hover {
  text-decoration: underline;
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .viz-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 800px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .screen-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
