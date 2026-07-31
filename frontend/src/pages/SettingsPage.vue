<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { RefreshCw, Save } from '@lucide/vue'
import {
  fetchAlertKeywords,
  fetchAnalysisStatus,
  fetchHealthReady,
  saveAlertKeywords,
} from '../api/client'

const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const saveError = ref('')
const message = ref('')
const online = ref(false)
const health = ref(null)
const analysis = ref(null)
const keywordsText = ref('')

const readiness = computed(() => health.value?.readiness || analysis.value?.readiness || null)

const demoChecklist = computed(() => {
  const r = readiness.value
  if (!r) return []
  return [
    {
      key: 'sentiment',
      ok: !!r.sentiment?.ok,
      label: '情感模型缓存',
      detail: r.sentiment?.ok
        ? r.sentiment.message
        : r.sentiment?.hint || '运行 uv run python backend/scripts/prefetch_models.py',
    },
    {
      key: 'bilibili',
      ok: !!r.bilibili?.configured,
      label: 'B 站登录态（Cookie）',
      detail: r.bilibili?.configured
        ? r.bilibili.message
        : r.bilibili?.hint || '在 backend/.env 配置 BILIBILI_SESSDATA 后重启后端',
    },
    {
      key: 'llm',
      ok: !!((r.llm || r.deepseek)?.configured) || !!r.agent?.ready,
      label: '云端 LLM / 助手（可选）',
      detail: (r.llm || r.deepseek)?.configured
        ? (r.llm || r.deepseek).message
        : r.agent?.ready
          ? r.agent.message
          : '未配置也可演示；报告智能摘要与助手需 OPENAI_* 或 Ollama Chat',
      optional: true,
    },
  ]
})

function tone(ok, warn = false) {
  if (ok) return 'ok'
  if (warn) return 'pending'
  return 'bad'
}

async function refresh() {
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const [h, a, kw] = await Promise.all([
      fetchHealthReady(),
      fetchAnalysisStatus(),
      fetchAlertKeywords(),
    ])
    online.value = !!h.ok
    if (!h.ok) throw new Error('健康检查失败')
    health.value = h.data
    analysis.value = a.ok ? a.data : null
    if (kw.ok) {
      keywordsText.value = (kw.data.keywords || []).join('\n')
    }
  } catch (e) {
    online.value = false
    loadError.value = e.message || '无法连接后端，请确认服务已启动。'
  } finally {
    loading.value = false
  }
}

async function onSaveKeywords() {
  saving.value = true
  saveError.value = ''
  message.value = ''
  try {
    const keywords = keywordsText.value
      .split(/[\n,，;；]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    const res = await saveAlertKeywords(keywords)
    if (!res.ok) throw new Error(res.error?.message || '保存失败')
    keywordsText.value = (res.data.keywords || []).join('\n')
    message.value = `已保存 ${res.data.keywords.length} 个敏感词`
  } catch (e) {
    saveError.value = e.message || '保存失败'
  } finally {
    saving.value = false
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
      <p v-else-if="loadError" class="err">{{ loadError }}</p>
      <template v-else>
        <div
          class="status-banner"
          :class="tone(online && readiness?.demo_ready_core, online && !readiness?.demo_ready_core)"
        >
          <span class="dot" />
          <template v-if="!online">服务离线</template>
          <template v-else-if="readiness?.demo_ready">演示全链路就绪（含主题向量）</template>
          <template v-else-if="readiness?.demo_ready_core">核心就绪（情感/预警/报告可用；主题需本机嵌入）</template>
          <template v-else>服务在线，但情感模型未缓存 — 请先预取模型</template>
        </div>

        <h4>演示前 3 步</h4>
        <ol class="demo-checklist">
          <li v-for="step in demoChecklist" :key="step.key" :class="{ done: step.ok }">
            <span class="check-mark">{{ step.ok ? '✓' : step.optional ? '○' : '!' }}</span>
            <div>
              <b>{{ step.label }}{{ step.optional ? '（可选）' : '' }}</b>
              <p>{{ step.detail }}</p>
            </div>
          </li>
        </ol>
        <p class="hint">
          预取命令：
          <code class="mono-inline">uv run python backend/scripts/prefetch_models.py</code>
          · 采完 BV 后去
          <RouterLink to="/monitor">监测</RouterLink>
          /
          <RouterLink to="/sentiment">情感</RouterLink>
          /
          <RouterLink to="/reports">报告</RouterLink>
        </p>

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
            <div class="kpi-label"><span>设备</span></div>
            <div class="kpi-value sm">{{ health?.device || '—' }}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label"><span>显卡</span></div>
            <div class="kpi-value sm">{{ health?.gpu_name || (health?.cuda ? '已启用' : '仅用处理器') }}</div>
          </div>
        </div>

        <h4>依赖就绪</h4>
        <div v-if="readiness" class="ready-grid">
          <article class="ready-card" :class="tone(readiness.sentiment?.ok)">
            <header>
              <b>情感模型</b>
              <span class="pill" :class="readiness.sentiment?.ok ? 'pill-ok' : 'pill-warning'">
                {{ readiness.sentiment?.cached ? (readiness.sentiment?.loaded ? '已加载' : '已缓存') : '未缓存' }}
              </span>
            </header>
            <p>{{ readiness.sentiment?.message }}</p>
            <small v-if="readiness.sentiment?.hint">{{ readiness.sentiment.hint }}</small>
            <small class="mono">{{ readiness.sentiment?.model_id }}</small>
          </article>

          <article
            class="ready-card"
            :class="tone(readiness.bilibili?.configured, readiness.bilibili && !readiness.bilibili.configured)"
          >
            <header>
              <b>B 站登录态</b>
              <span
                class="pill"
                :class="readiness.bilibili?.configured ? 'pill-ok' : 'pill-warning'"
              >
                {{ readiness.bilibili?.configured ? '已配置' : '未配置' }}
              </span>
            </header>
            <p>{{ readiness.bilibili?.message || '未探测到 B 站 Cookie 状态' }}</p>
            <small v-if="readiness.bilibili?.hint">{{ readiness.bilibili.hint }}</small>
            <small class="mono">环境变量 BILIBILI_SESSDATA（不回显内容）</small>
          </article>

          <article class="ready-card" :class="tone(readiness.ollama?.ok, readiness.ollama?.reachable)">
            <header>
              <b>本机嵌入</b>
              <span
                class="pill"
                :class="readiness.ollama?.ok ? 'pill-ok' : readiness.ollama?.reachable ? 'pill-warning' : 'pill-danger'"
              >
                {{ readiness.ollama?.ok ? '就绪' : readiness.ollama?.reachable ? '缺模型' : '未连接' }}
              </span>
            </header>
            <p>{{ readiness.ollama?.message }}</p>
            <small v-if="readiness.ollama?.hint">{{ readiness.ollama.hint }}</small>
            <small class="mono">{{ readiness.ollama?.model }}</small>
          </article>

          <article class="ready-card" :class="tone(true, !(readiness.llm || readiness.deepseek)?.configured)">
            <header>
              <b>云端大模型</b>
              <span
                class="pill"
                :class="(readiness.llm || readiness.deepseek)?.configured ? 'pill-ok' : 'pill-default'"
              >
                {{ (readiness.llm || readiness.deepseek)?.configured ? '已配置' : '可选' }}
              </span>
            </header>
            <p>{{ (readiness.llm || readiness.deepseek)?.message }}</p>
            <small v-if="(readiness.llm || readiness.deepseek)?.hint">
              {{ (readiness.llm || readiness.deepseek).hint }}
            </small>
            <small class="mono">兼容主流云端接口（火山 / 百炼 / DeepSeek 等）</small>
          </article>

          <article
            class="ready-card"
            :class="tone(readiness.agent?.ready, readiness.agent && !readiness.agent.ready)"
          >
            <header>
              <b>智能助手</b>
              <span class="pill" :class="readiness.agent?.ready ? 'pill-ok' : 'pill-warning'">
                {{ readiness.agent?.ready ? '可用' : '未就绪' }}
              </span>
            </header>
            <p>{{ readiness.agent?.message || '问答 / 简报需配置云端密钥或本机对话模型' }}</p>
            <small v-if="readiness.agent?.hint">{{ readiness.agent.hint }}</small>
            <small class="mono">优先云端大模型，否则使用本机对话模型</small>
          </article>
        </div>

        <ul v-if="readiness?.warnings?.length" class="notes warn-list">
          <li v-for="(w, i) in readiness.warnings" :key="i">{{ w }}</li>
        </ul>

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
            <span>趋势</span>
            <b>滑动平均 + 智能预测</b>
          </li>
          <li>
            <span>报告导出</span>
            <b>文档 / 表格 · 可选云端大模型</b>
          </li>
          <li>
            <span>智能助手</span>
            <b>问答 · 简报（云端 / 本机）</b>
          </li>
          <li>
            <span>数据导入</span>
            <b>数据文件 / 表格 · 可选平台</b>
          </li>
        </ul>
        <p class="hint" style="margin-top: 0.85rem">
          演示前请先完成模型预取与真实采集配置（见项目文档「模型缓存」「真实数据采集」）。
        </p>
      </template>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>预警敏感词</h3>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="saving || loading"
          @click="onSaveKeywords"
        >
          <Save :size="14" />
          保存
        </button>
      </div>
      <p class="hint">每行一个词，也可用逗号分隔。命中且负面情感时标为高风险。</p>
      <textarea
        v-model="keywordsText"
        class="textarea"
        rows="8"
        placeholder="劝退&#10;翻车&#10;注水&#10;看不下去"
      />
      <p v-if="message" class="ok-text">{{ message }}</p>
      <p v-if="saveError" class="err">{{ saveError }}</p>
    </section>
  </div>
</template>

<style scoped>
.ready-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin: 0.75rem 0 1rem;
}
.ready-card {
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}
.ready-card.ok {
  border-color: rgba(22, 163, 74, 0.35);
}
.ready-card.pending {
  border-color: rgba(217, 119, 6, 0.4);
}
.ready-card.bad {
  border-color: rgba(220, 38, 38, 0.35);
}
.ready-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}
.ready-card p {
  margin: 0.25rem 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.45;
}
.ready-card small {
  display: block;
  color: var(--text-tertiary);
  font-size: 0.78rem;
  margin-top: 0.25rem;
  line-height: 1.4;
}
.ready-card .mono {
  font-family: ui-monospace, Consolas, monospace;
  word-break: break-all;
}
.warn-list {
  margin: 0 0 1rem;
  padding-left: 1.1rem;
  color: #b45309;
  line-height: 1.55;
}
.pill-ok {
  background: rgba(22, 163, 74, 0.08);
  color: var(--color-success);
  border: 1px solid rgba(22, 163, 74, 0.2);
}
.demo-checklist {
  margin: 0.5rem 0 0.75rem;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.demo-checklist li {
  display: flex;
  gap: 0.65rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}
.demo-checklist li.done {
  border-color: rgba(22, 163, 74, 0.3);
}
.demo-checklist .check-mark {
  flex-shrink: 0;
  width: 1.25rem;
  text-align: center;
  font-weight: 700;
  color: #b45309;
}
.demo-checklist li.done .check-mark {
  color: var(--color-success);
}
.demo-checklist b {
  display: block;
  font-size: 0.9rem;
}
.demo-checklist p {
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.45;
}
.mono-inline {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.82rem;
}
</style>
