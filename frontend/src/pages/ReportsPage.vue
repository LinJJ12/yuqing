<script setup>
import { onMounted, ref } from 'vue'
import { Download, FileText, RefreshCw, Sparkles } from '@lucide/vue'
import {
  fetchReportSummary,
  generateReportSummary,
  reportCsvUrl,
  reportPdfUrl,
} from '../api/client'

const loading = ref(true)
const aiLoading = ref(false)
const error = ref('')
const report = ref(null)
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
}

async function refresh() {
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

async function onAiSummary() {
  aiLoading.value = true
  error.value = ''
  try {
    const res = await generateReportSummary({ with_ai: true })
    if (!res.ok) throw new Error(res.error?.message || '摘要失败')
    report.value = res.data
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

onMounted(refresh)
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>分析报告</h2>
        <div class="head-actions">
          <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
            <RefreshCw :size="14" />
            重新生成
          </button>
          <button type="button" class="btn btn-secondary btn-sm" :disabled="aiLoading || loading" @click="onAiSummary">
            <Sparkles :size="14" />
            AI 摘要
          </button>
        </div>
      </div>
      <div class="export-row">
        <label class="check">
          <input v-model="withAiExport" type="checkbox" />
          导出时附带 AI 摘要（需配置 OPENAI_API_KEY）
        </label>
        <button type="button" class="btn btn-primary btn-sm" @click="openExport('csv')">
          <Download :size="14" />
          导出 CSV
        </button>
        <button type="button" class="btn btn-primary btn-sm" @click="openExport('pdf')">
          <FileText :size="14" />
          导出 PDF
        </button>
      </div>
      <p v-if="loading" class="muted">正在汇总…</p>
      <p v-else-if="error" class="err">{{ error }}</p>
      <template v-else-if="report">
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
