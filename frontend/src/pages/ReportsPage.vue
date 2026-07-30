<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, ExternalLink, FileText, RefreshCw, Sparkles } from '@lucide/vue'
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
const loading = ref(true)
const aiLoading = ref(false)
const error = ref('')
const report = ref(null)
const videoReport = ref(null)
const videos = ref([])
const bvidInput = ref('')
const withAiExport = ref(false)

const labelMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  unknown: '未标注',
}
const methodMap = {
  bert: '模型',
  lexicon: '词典',
  unknown: '未标注',
  all: '合计',
}

const activeBvid = computed(() => String(route.query.bvid || '').trim())
const highlightBvid = computed(() => videoReport.value?.bvid || activeBvid.value)

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
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

async function loadVideo(bvid) {
  const key = (bvid || '').trim()
  if (!key) {
    videoReport.value = null
    error.value = '请选择或填写 BV 号'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await fetchVideoReport(key)
    if (!res.ok) throw new Error(res.error?.message || '视频报告失败')
    videoReport.value = res.data
    bvidInput.value = res.data.bvid || key
  } catch (e) {
    videoReport.value = null
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await loadVideos()
  if (mode.value === 'global') {
    await refreshGlobal()
    return
  }
  const bvid = activeBvid.value || bvidInput.value || videos.value[0]?.bvid || ''
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

function selectVideo(bvid) {
  router.push({ query: { bvid } })
  mode.value = 'video'
}

function submitBvid() {
  const v = bvidInput.value.trim()
  if (!v) {
    error.value = '请填写 BV 号或视频链接'
    return
  }
  router.push({ query: { bvid: v } })
  mode.value = 'video'
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
      error.value = res.data.ai.message || 'AI 摘要不可用'
    }
  } catch (e) {
    error.value = e.message || 'AI 摘要失败'
  } finally {
    aiLoading.value = false
  }
}

function openExport(kind) {
  const url = kind === 'pdf' ? reportPdfUrl({ with_ai: withAiExport.value }) : reportCsvUrl({ with_ai: withAiExport.value })
  window.open(url, '_blank')
}

watch(
  () => route.query.bvid,
  (v, prev) => {
    if (v && String(v) !== String(prev || '')) {
      mode.value = 'video'
      loadVideo(String(v))
    }
  },
)

watch(mode, (m) => {
  if (m === 'global') refreshGlobal()
  else if (m === 'video') {
    // 切回口碑模式时刷新列表；若 query 已有 bvid，由上方 watch / refresh 承接
    refresh()
  }
})

onMounted(refresh)
</script>

<template>
  <div class="page reports-page">
    <section class="panel">
      <div class="panel-head">
        <h2>分析报告</h2>
        <div class="head-actions">
          <button
            type="button"
            class="btn btn-sm"
            :class="mode === 'video' ? 'btn-primary' : 'btn-secondary'"
            @click="mode = 'video'"
          >
            单视频口碑
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="mode === 'global' ? 'btn-primary' : 'btn-secondary'"
            @click="mode = 'global'"
          >
            全局汇总
          </button>
          <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
            <RefreshCw :size="14" />
            刷新
          </button>
        </div>
      </div>

      <template v-if="mode === 'video'">
        <p class="hint">按 BV 聚合评论情感与高频词，生成观众反馈结论。可先在监测页采集再回来查看。</p>
        <div class="bvid-row">
          <input
            v-model="bvidInput"
            class="input"
            placeholder="BV 号或视频链接"
            @keyup.enter="submitBvid"
          />
          <button type="button" class="btn btn-primary btn-sm" :disabled="loading" @click="submitBvid">
            生成口碑
          </button>
        </div>
        <div v-if="videos.length" class="video-chips">
          <button
            v-for="v in videos"
            :key="v.bvid"
            type="button"
            class="chip"
            :class="{ active: highlightBvid === v.bvid }"
            :title="v.video_title || v.bvid"
            @click="selectVideo(v.bvid)"
          >
            <span class="chip-title">{{ v.video_title || v.bvid }}</span>
            <span class="chip-meta">{{ v.comment_count }} 评 · 负 {{ v.negative }}</span>
          </button>
        </div>
        <p v-else-if="!loading" class="muted">暂无带 BV 的评论。请到「监测」贴 BV 采集。</p>
      </template>

      <template v-else>
        <div class="export-row">
          <label class="check">
            <input v-model="withAiExport" type="checkbox" />
            导出时附带 AI 摘要（需配置 OPENAI_API_KEY）
          </label>
          <button type="button" class="btn btn-secondary btn-sm" :disabled="aiLoading || loading" @click="onAiSummary">
            <Sparkles :size="14" />
            AI 摘要
          </button>
          <button type="button" class="btn btn-primary btn-sm" @click="openExport('csv')">
            <Download :size="14" />
            导出 CSV
          </button>
          <button type="button" class="btn btn-primary btn-sm" @click="openExport('pdf')">
            <FileText :size="14" />
            导出 PDF
          </button>
        </div>
      </template>

      <p v-if="loading" class="muted">正在汇总…</p>
      <p v-else-if="error" class="err">{{ error }}</p>

      <template v-else-if="mode === 'video' && videoReport">
        <h3 class="report-title">{{ videoReport.generated_for }}</h3>
        <p v-if="videoReport.video_title" class="muted video-line">
          {{ videoReport.bvid }}
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

        <div class="conclusion">{{ videoReport.conclusion }}</div>

        <div class="kpi-grid">
          <div class="kpi">
            <div class="kpi-label"><span>评论数</span></div>
            <div class="kpi-value">{{ videoReport.overview?.total_posts ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>正面</span></div>
            <div class="kpi-value ok">{{ videoReport.sentiment?.by_label?.positive ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>中性</span></div>
            <div class="kpi-value">{{ videoReport.sentiment?.by_label?.neutral ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>负面</span></div>
            <div class="kpi-value bad">{{ videoReport.sentiment?.by_label?.negative ?? 0 }}</div>
          </div>
        </div>

        <h4>情感明细</h4>
        <ul class="stack-list">
          <li v-for="row in videoReport.sentiment?.breakdown || []" :key="row.label + row.method">
            <span>{{ labelMap[row.label] || row.label }}（{{ methodMap[row.method] || row.method }}）</span>
            <b>{{ row.count }}</b>
          </li>
        </ul>

        <h4>高频词</h4>
        <div v-if="videoReport.word_cloud?.length" class="tags">
          <span v-for="w in videoReport.word_cloud.slice(0, 24)" :key="w.name" class="tag">
            {{ w.name }} · {{ w.value }}
          </span>
        </div>
        <p v-else class="muted">暂无分词结果</p>

        <h4>预警评论（{{ videoReport.alerts?.total ?? 0 }}）</h4>
        <ul v-if="videoReport.alerts?.items?.length" class="stack-list">
          <li v-for="a in videoReport.alerts.items.slice(0, 8)" :key="a.id">
            <span>{{ a.message }}</span>
            <b>{{ a.severity }}</b>
          </li>
        </ul>
        <p v-else class="muted">无明显负面/敏感命中</p>

        <h4>评论样例</h4>
        <ul class="sample-list">
          <li v-for="p in videoReport.sample_posts || []" :key="p.id">
            <div class="sample-head">
              <span class="pill pill-default">{{ labelMap[p.sentiment_label] || p.sentiment_label || '—' }}</span>
              <span class="muted">{{ p.author || '匿名' }} · 赞 {{ p.likes }}</span>
              <a
                v-if="p.source_url"
                :href="p.source_url"
                target="_blank"
                rel="noopener"
                class="ext"
              >原评</a>
            </div>
            <p>{{ p.text }}</p>
          </li>
        </ul>

        <h4>说明</h4>
        <ul class="notes">
          <li v-for="(n, i) in videoReport.notes || []" :key="i">{{ n }}</li>
        </ul>
      </template>

      <template v-else-if="mode === 'global' && report">
        <h3 class="report-title">{{ report.generated_for }}</h3>
        <div class="kpi-grid">
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

        <h4>情感分布</h4>
        <ul class="stack-list">
          <li v-for="row in report.sentiment?.breakdown || []" :key="row.label + row.method">
            <span>{{ labelMap[row.label] || row.label }}（{{ methodMap[row.method] || row.method }}）</span>
            <b>{{ row.count }}</b>
          </li>
        </ul>

        <h4>话题 Top</h4>
        <ul class="stack-list">
          <li v-for="row in report.overview?.by_topic || []" :key="row.topic">
            <span>{{ row.topic }}</span>
            <b>{{ row.count }}</b>
          </li>
        </ul>

        <template v-if="report.ai_summary">
          <h4>AI 摘要</h4>
          <p class="ai-box">{{ report.ai_summary }}</p>
        </template>

        <h4>说明</h4>
        <ul class="notes">
          <li v-for="(n, i) in report.notes || []" :key="i">{{ n }}</li>
        </ul>
      </template>
    </section>
  </div>
</template>

<style scoped>
.hint {
  margin: 0 0 0.75rem;
  color: var(--text-secondary);
  font-size: 0.88rem;
}
.bvid-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.bvid-row .input {
  flex: 1;
}
.video-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 1rem;
}
.chip {
  max-width: 100%;
  text-align: left;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: #fff;
  border-radius: 10px;
  padding: 0.45rem 0.65rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.chip.active {
  border-color: #166534;
  background: #f0fdf4;
}
.chip-title {
  font-size: 0.82rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 16rem;
}
.chip-meta {
  font-size: 0.72rem;
  color: var(--text-secondary);
}
.conclusion {
  margin: 0.5rem 0 1rem;
  padding: 0.9rem 1rem;
  background: linear-gradient(135deg, #f8fafc, #f0fdf4);
  border-left: 3px solid #166534;
  line-height: 1.7;
  color: var(--text-primary, #0f172a);
}
.video-line {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: -0.4rem 0 0.8rem;
}
.ext {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: #1d4ed8;
  text-decoration: none;
  font-size: 0.82rem;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.tag {
  font-size: 0.78rem;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  background: #f1f5f9;
  color: var(--text-secondary);
}
.sample-list {
  list-style: none;
  margin: 0 0 1rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.sample-list li {
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 10px;
  background: #fff;
}
.sample-list p {
  margin: 0.35rem 0 0;
  line-height: 1.55;
  font-size: 0.9rem;
}
.sample-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.report-title {
  margin: 0.25rem 0 1rem;
  font-size: 1.05rem;
  font-weight: 600;
}
.notes {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
.head-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.export-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
  margin: 0.75rem 0 1rem;
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-right: 0.4rem;
}
.ai-box {
  margin: 0.35rem 0 1rem;
  padding: 0.85rem 1rem;
  background: var(--bg-secondary, #f8fafc);
  border-left: 3px solid #1e40af;
  color: var(--text-secondary);
  line-height: 1.65;
  white-space: pre-wrap;
}
</style>
