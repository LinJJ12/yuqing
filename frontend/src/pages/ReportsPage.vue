<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from '@lucide/vue'
import { fetchReportSummary } from '../api/client'

const loading = ref(true)
const error = ref('')
const report = ref(null)
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

onMounted(refresh)
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>分析报告</h2>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="loading" @click="refresh">
          <RefreshCw :size="14" />
          重新生成
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
</style>
