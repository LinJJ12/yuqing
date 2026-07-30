<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from '@lucide/vue'
import { fetchAnalysisStatus, fetchHealthReady } from '../api/client'

const loading = ref(true)
const error = ref('')
const online = ref(false)
const analysis = ref(null)

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [h, a] = await Promise.all([fetchHealthReady(), fetchAnalysisStatus()])
    online.value = !!h.ok
    if (!h.ok) throw new Error('健康检查失败')
    analysis.value = a.ok ? a.data : null
  } catch (e) {
    online.value = false
    error.value = e.message || '无法连接后端，请确认服务已启动。'
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
        <h2>系统设置</h2>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="loading"
          @click="refresh"
        >
          <RefreshCw :size="14" />
          刷新状态
        </button>
      </div>

      <p v-if="loading" class="muted">检测中…</p>
      <p v-else-if="error" class="err">{{ error }}</p>
      <template v-else>
        <div class="status-banner" :class="online ? 'ok' : 'bad'">
          <span class="dot" />
          {{ online ? '服务正常' : '服务离线' }}
        </div>

        <div class="kpi-grid" style="margin-top: 1rem; margin-bottom: 0">
          <div class="kpi">
            <div class="kpi-label"><span>帖子总量</span></div>
            <div class="kpi-value">{{ analysis?.db?.total ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>情感已分析</span></div>
            <div class="kpi-value ok">{{ analysis?.db?.bert_done ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>情感类别</span></div>
            <div class="kpi-value sm">正 / 中 / 负</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>主题能力</span></div>
            <div class="kpi-value sm">词云 · 主题聚类</div>
          </div>
        </div>

        <h4>功能说明</h4>
        <ul class="stack-list">
          <li>
            <span>情感分析</span>
            <b>正面 / 中性 / 负面</b>
          </li>
          <li>
            <span>热点话题</span>
            <b>词云 + 主题聚类</b>
          </li>
          <li>
            <span>预警规则</span>
            <b>负面 / 敏感词 · 热度突增</b>
          </li>
          <li>
            <span>数据导入</span>
            <b>JSON / CSV</b>
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>
