<script setup>
/**
 * 总览：沿用本站已验证图表样式
 * - 趋势：预警页「灰柱 + 青绿折线」
 * - 情感：洞察页环形图
 */
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
  ArrowRight,
} from '@lucide/vue'
import { fetchOverview, fetchTrends } from '../api/client'
import { formatDateTime } from '../lib/datetime'

const loading = ref(true)
const error = ref('')
const overview = ref(null)
const trendSeries = ref([])

const trendRef = ref(null)
const sentimentRef = ref(null)
const platformRef = ref(null)
let trendChart
let sentimentChart
let platformChart

const sentimentMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}

const sentimentColor = {
  positive: '#16a34a',
  neutral: '#0f766e',
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
  return overview.value?.by_sentiment?.find((x) => x.label === label)?.count ?? 0
}

const positiveCount = computed(() => sentimentCount('positive'))
const negativeCount = computed(() => sentimentCount('negative'))
const neutralCount = computed(() => sentimentCount('neutral'))
const trendTotal = computed(() =>
  trendSeries.value.filter((s) => !s.is_forecast).reduce((a, s) => a + (s.count || 0), 0),
)

const sentimentShares = computed(() => {
  const counts = { positive: 0, neutral: 0, negative: 0, uncertain: 0 }
  for (const row of overview.value?.by_sentiment || []) {
    if (row.label in counts) counts[row.label] += Number(row.count) || 0
  }
  return ['positive', 'neutral', 'negative', 'uncertain']
    .map((key) => ({
      key,
      label: sentimentMap[key],
      count: counts[key],
    }))
    .filter((s) => s.count > 0)
})

const topTopics = computed(() => {
  const rows = [...(overview.value?.by_topic || [])].slice(0, 5)
  const max = Math.max(...rows.map((r) => r.count), 1)
  return rows.map((r) => ({
    ...r,
    pct: Math.round((r.count / max) * 100),
  }))
})

const recentPosts = computed(() => overview.value?.recent_posts?.slice(0, 8) || [])

function platformLabel(code) {
  return platformMap[code] || code || '—'
}

function videoTitle(post) {
  return post?.raw?.extra?.video_title || ''
}

function ensureChart(instance, el) {
  if (!el) return null
  if (instance && !instance.isDisposed?.()) {
    if (instance.getDom?.() === el) return instance
    instance.dispose()
  }
  return echarts.init(el)
}

/** 与预警页同款：灰柱 + 青绿滑动平均 */
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
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['发帖量', '滑动平均'],
        top: 0,
        left: 'center',
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { color: '#52525b', fontSize: 11 },
      },
      grid: { left: 40, right: 12, top: 28, bottom: 28 },
      xAxis: {
        type: 'category',
        data: series.map((s) => s.day),
        axisLine: { lineStyle: { color: '#e4e4e7' } },
        axisLabel: { color: '#71717a', margin: 8, fontSize: 11 },
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
      ],
    },
    true,
  )
}

/** 与洞察页同款环形图 */
function renderSentiment() {
  sentimentChart = ensureChart(sentimentChart, sentimentRef.value)
  if (!sentimentChart) return
  const data = sentimentShares.value.map((s) => ({
    name: s.label,
    value: s.count,
    itemStyle: { color: sentimentColor[s.key] },
  }))
  sentimentChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br/>{c} 条（{d}%）',
      },
      legend: {
        bottom: 0,
        left: 'center',
        itemWidth: 10,
        itemHeight: 8,
        textStyle: { color: '#64748b', fontSize: 11 },
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '64%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 5,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            color: '#475569',
            fontSize: 11,
            formatter: '{b}\n{d}%',
          },
          data: data.length
            ? data
            : [{ name: '暂无标注', value: 1, itemStyle: { color: '#e4e4e7' } }],
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
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 36, right: 8, top: 18, bottom: 28, containLabel: false },
      xAxis: {
        type: 'category',
        data: rows.map((r) => platformLabel(r.platform)),
        axisLine: { lineStyle: { color: '#e4e4e7' } },
        axisTick: { show: false },
        axisLabel: { color: '#71717a', interval: 0, fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f4f4f5' } },
        axisLabel: { color: '#71717a', fontSize: 11 },
      },
      series: [
        {
          type: 'bar',
          barMaxWidth: 36,
          barCategoryGap: '50%',
          data: rows.map((r) => r.count),
          itemStyle: {
            color: '#0f766e',
            borderRadius: [4, 4, 0, 0],
          },
          label: {
            show: true,
            position: 'top',
            color: '#64748b',
            fontSize: 10,
            fontWeight: 600,
          },
        },
      ],
    },
    true,
  )
}

function renderAll() {
  renderTrend()
  renderSentiment()
  renderPlatform()
  requestAnimationFrame(() => {
    trendChart?.resize()
    sentimentChart?.resize()
    platformChart?.resize()
    requestAnimationFrame(() => platformChart?.resize())
  })
}

function onResize() {
  trendChart?.resize()
  sentimentChart?.resize()
  platformChart?.resize()
}

onMounted(async () => {
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
  await nextTick()
  if (total.value > 0) renderAll()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  sentimentChart?.dispose()
  platformChart?.dispose()
  trendChart = null
  sentimentChart = null
  platformChart = null
})
</script>

<template>
  <div class="page overview-page" :class="{ 'is-filled': total > 0 && !loading && !error }">
    <div v-if="loading" class="panel">
      <div class="skeleton" style="width: 40%; margin-bottom: 0.75rem" />
      <div class="skeleton" style="width: 70%" />
    </div>
    <p v-else-if="error" class="panel err">{{ error }}</p>

    <template v-else-if="total === 0">
      <section class="panel first-run">
        <h3>开始第一次演示</h3>
        <p class="first-run-lead">
          库内还没有帖子。按下面三步即可跑通「采集 → 洞察 → 口碑」。
        </p>
        <ol class="first-run-steps">
          <li>
            <b>监测：贴 BV 采集评论</b>
            <p>打开监测页，粘贴 B 站视频链接或 BV 号，开始采集并入库。</p>
            <RouterLink class="btn btn-primary btn-sm" to="/monitor">去监测</RouterLink>
            <RouterLink class="btn btn-secondary btn-sm" to="/inbox" style="margin-left: 0.45rem">
              看入库
            </RouterLink>
          </li>
          <li>
            <b>洞察：跑批情感与词云</b>
            <p>采集后会自动排队情感分析；也可在洞察页手动跑批并看分布/词云。</p>
            <RouterLink class="btn btn-secondary btn-sm" to="/insights">去洞察</RouterLink>
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
      <div class="overview-body">
        <div class="kpi-grid kpi-compact">
          <div class="kpi">
            <div class="kpi-label">
              <span>帖子总量</span>
              <MessageSquareText :size="14" />
            </div>
            <div class="kpi-value">{{ total }}</div>
            <p class="kpi-foot">已标注 {{ analyzedRate }}</p>
          </div>
          <div class="kpi">
            <div class="kpi-label">
              <span>话题数</span>
              <Tags :size="14" />
            </div>
            <div class="kpi-value">{{ topicCount }}</div>
            <p class="kpi-foot">库内标签聚合</p>
          </div>
          <div class="kpi">
            <div class="kpi-label">
              <span>正面</span>
              <ThumbsUp :size="14" />
            </div>
            <div class="kpi-value ok">{{ positiveCount }}</div>
            <p class="kpi-foot">中性 {{ neutralCount }}</p>
          </div>
          <div class="kpi">
            <div class="kpi-label">
              <span>负面</span>
              <ThumbsDown :size="14" />
            </div>
            <div class="kpi-value bad">{{ negativeCount }}</div>
            <p class="kpi-foot">需关注口碑风险</p>
          </div>
          <div class="kpi">
            <div class="kpi-label">
              <span>近 14 日</span>
              <Activity :size="14" />
            </div>
            <div class="kpi-value">{{ trendTotal }}</div>
            <p class="kpi-foot">区间发帖量</p>
          </div>
        </div>

        <div class="main-row">
          <section class="panel fill-panel">
            <div class="panel-head">
              <h3>情感分布</h3>
              <RouterLink class="panel-link" to="/insights">
                去洞察
                <ArrowRight :size="13" />
              </RouterLink>
            </div>
            <div ref="sentimentRef" class="chart chart-fill" />
          </section>
          <div class="main-side">
            <section class="panel fill-panel">
              <div class="panel-head">
                <h3>数据来源</h3>
                <span class="panel-meta">按平台</span>
              </div>
              <div ref="platformRef" class="chart chart-fill" />
            </section>
            <section class="panel fill-panel">
              <div class="panel-head">
                <h3>话题热度</h3>
                <span class="panel-meta">Top {{ topTopics.length }}</span>
              </div>
              <ul v-if="topTopics.length" class="rank-list">
                <li v-for="(item, idx) in topTopics" :key="item.topic">
                  <span class="rank-idx">{{ idx + 1 }}</span>
                  <div class="rank-body">
                    <div class="rank-top">
                      <span class="rank-name" :title="item.topic">{{ item.topic }}</span>
                      <b>{{ item.count }}</b>
                    </div>
                    <div class="rank-bar">
                      <i :style="{ width: `${item.pct}%` }" />
                    </div>
                  </div>
                </li>
              </ul>
              <p v-else class="empty-hint">暂无话题数据</p>
            </section>
          </div>
        </div>

        <div class="detail-row">
          <section class="panel fill-panel">
            <div class="panel-head">
              <h3>入库趋势</h3>
              <span class="panel-meta">近 14 日</span>
            </div>
            <div ref="trendRef" class="chart chart-fill" />
          </section>
          <section class="panel feed-panel">
            <div class="panel-head">
              <h3>最近入库</h3>
              <RouterLink class="panel-link" to="/inbox">
                全部
                <ArrowRight :size="13" />
              </RouterLink>
            </div>
            <div v-if="recentPosts.length" class="feed">
              <article v-for="post in recentPosts" :key="post.id" class="feed-item">
                <header>
                  <b>{{ post.topic || '未分类' }}</b>
                  <span class="pill pill-default">{{ platformLabel(post.platform) }}</span>
                  <em :style="{ color: sentimentColor[post.sentiment_label] || '#64748b' }">
                    {{ sentimentMap[post.sentiment_label] || '—' }}
                  </em>
                </header>
                <p v-if="videoTitle(post)" class="feed-sub">{{ videoTitle(post) }}</p>
                <p class="feed-text">{{ post.text }}</p>
                <footer>
                  <time>{{ formatDateTime(post.fetched_at || post.published_at) }}</time>
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
            <p v-else class="empty-hint">还没有帖子</p>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.overview-page {
  color: var(--text-primary);
}
.overview-page.is-filled {
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--topbar-h) - 2.75rem);
  min-height: 0;
  overflow: hidden;
}
.overview-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) minmax(0, 1.05fr);
  gap: 0.55rem;
}

.first-run {
  max-width: 40rem;
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

.overview-page .kpi-grid {
  margin-bottom: 0;
}
.overview-page .kpi-foot {
  margin: 0.2rem 0 0;
  font-size: 0.7rem;
  color: var(--text-tertiary);
  line-height: 1.25;
}

.panel-meta {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-weight: 400;
}
.panel-link {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.75rem;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}
.panel-link:hover {
  text-decoration: underline;
}

.main-row,
.detail-row {
  display: grid;
  gap: 0.55rem;
  min-height: 0;
  align-items: stretch;
}
.main-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr);
}
.detail-row {
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
}
.main-row > .panel,
.main-side > .panel,
.detail-row > .panel {
  margin-bottom: 0;
  padding: 0.7rem 0.85rem;
}
.overview-page :deep(.panel-head) {
  min-height: 22px;
  margin-bottom: 0.45rem;
}
.main-side {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.fill-panel,
.feed-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
.fill-panel .panel-head,
.feed-panel .panel-head {
  flex-shrink: 0;
}

.chart {
  width: 100%;
}
.chart-fill {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.15rem;
}
.rank-list li {
  display: grid;
  grid-template-columns: 1.2rem 1fr;
  gap: 0.45rem;
  align-items: center;
  flex: 1;
  min-height: 0;
}
.rank-idx {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary);
  text-align: center;
}
.rank-body {
  min-width: 0;
}
.rank-top {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: baseline;
  margin-bottom: 0.2rem;
}
.rank-name {
  font-size: 0.8rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-top b {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
}
.rank-bar {
  height: 6px;
  border-radius: 99px;
  background: #f1f5f9;
  overflow: hidden;
}
.rank-bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: var(--color-primary);
  opacity: 0.8;
}

.feed {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.empty-hint {
  margin: 0;
  flex: 1;
  display: grid;
  place-items: center;
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.feed-item {
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--color-border);
}
.feed-item:last-child {
  border-bottom: none;
}
.feed-item header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  margin-bottom: 0.15rem;
  font-size: 0.75rem;
}
.feed-item header b {
  color: var(--text-primary);
  font-weight: 600;
}
.feed-item header em {
  font-style: normal;
  font-weight: 600;
}
.feed-sub {
  margin: 0 0 0.1rem;
  font-size: 0.7rem;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.feed-text {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feed-item footer {
  margin-top: 0.2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.7rem;
  color: var(--text-tertiary);
}
.feed-item footer a {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: var(--color-primary);
  text-decoration: none;
}
.feed-item footer a:hover {
  text-decoration: underline;
}

@media (max-width: 1100px) {
  .overview-page.is-filled {
    height: auto;
    overflow: visible;
  }
  .overview-body {
    display: flex;
    flex-direction: column;
    height: auto;
  }
  .main-row,
  .main-side,
  .detail-row {
    grid-template-columns: 1fr;
    height: auto;
  }
  .chart-fill {
    min-height: 200px;
  }
  .rank-list {
    min-height: 180px;
  }
  .feed {
    max-height: 260px;
  }
}
</style>
