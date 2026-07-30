<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bot, Copy, FileText, Send } from '@lucide/vue'
import { agentBrief, agentChat, fetchAgentStatus } from '../api/client'

const route = useRoute()
const question = ref('该视频评论负面主要集中在哪些点？有什么建议？')
const bvid = ref('')
const history = ref([])
const answer = ref('')
const digest = ref(null)
const brief = ref('')
const briefMeta = ref(null)
const status = ref(null)
const showDigest = ref(false)
const loadingChat = ref(false)
const loadingBrief = ref(false)
const error = ref('')
const message = ref('')

async function refreshStatus() {
  const res = await fetchAgentStatus()
  if (res.ok) status.value = res.data
}

async function onAsk() {
  error.value = ''
  message.value = ''
  const q = question.value.trim()
  if (!q) {
    error.value = '请输入问题'
    return
  }
  loadingChat.value = true
  try {
    const res = await agentChat(
      q,
      history.value.map((h) => ({ role: h.role, content: h.content })),
      { bvid: bvid.value.trim() || undefined },
    )
    if (!res.ok) {
      error.value = res.error?.message || '问答失败'
      return
    }
    answer.value = res.data.content || ''
    digest.value = res.data.context_digest || null
    history.value = [
      ...history.value,
      { role: 'user', content: q },
      { role: 'assistant', content: answer.value },
    ].slice(-6)
    const scope = res.data.context_digest?.scope === 'video' ? '单视频' : '全局'
    message.value = `来源：${res.data.provider} / ${res.data.model}（${scope}）`
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loadingChat.value = false
  }
}

async function onBrief() {
  error.value = ''
  message.value = ''
  loadingBrief.value = true
  try {
    const res = await agentBrief({ bvid: bvid.value.trim() || undefined })
    if (!res.ok) {
      error.value = res.error?.message || '简报生成失败'
      return
    }
    brief.value = res.data.content || ''
    briefMeta.value = {
      title: res.data.title,
      provider: res.data.provider,
      model: res.data.model,
      digest: res.data.context_digest,
    }
    const scope = res.data.context_digest?.scope === 'video' ? '观众反馈' : '全局'
    message.value = `简报来源：${res.data.provider} / ${res.data.model}（${scope}）`
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loadingBrief.value = false
  }
}

async function copyBrief() {
  if (!brief.value) return
  try {
    await navigator.clipboard.writeText(brief.value)
    message.value = '简报已复制到剪贴板'
  } catch {
    error.value = '复制失败，请手动选择文本'
  }
}

watch(
  () => route.query.bvid,
  (v) => {
    if (v) bvid.value = String(v)
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    await refreshStatus()
  } catch {
    error.value = '无法连接后端'
  }
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>智能助手</h2>
        <span
          class="pill"
          :class="status?.ready ? 'pill-ok' : 'pill-warning'"
        >
          {{ status?.ready ? '可用' : '未就绪' }}
        </span>
      </div>
      <p class="hint">
        可填 BV 限定「单视频观众反馈」；留空则用全局库统计。优先云端 OpenAI 兼容接口，否则本机 Ollama Chat。
        {{ status?.message }}
      </p>
      <p v-if="status?.hint" class="hint">{{ status.hint }}</p>
      <label class="field">
        BV / 链接（可选，限定单视频）
        <input v-model="bvid" class="input" placeholder="留空=全局；填 BV 则按该视频评论回答" />
      </label>
      <p v-if="message" class="ok-text">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>舆情问答</h3>
      </div>
      <textarea
        v-model="question"
        class="textarea"
        rows="3"
        placeholder="例如：该视频评论负面主要集中在哪些点？"
      />
      <div class="actions">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="loadingChat || loadingBrief"
          @click="onAsk"
        >
          <Send :size="16" />
          {{ loadingChat ? '思考中…' : '提问' }}
        </button>
      </div>
      <div v-if="answer" class="answer-box">
        <header class="post-meta">
          <Bot :size="16" />
          <b>回答</b>
        </header>
        <p class="answer-text">{{ answer }}</p>
        <button type="button" class="btn btn-ghost btn-sm" @click="showDigest = !showDigest">
          {{ showDigest ? '收起' : '展开' }}引用摘要
        </button>
        <pre v-if="showDigest && digest" class="digest">{{ JSON.stringify(digest, null, 2) }}</pre>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>生成简报</h3>
        <div class="head-actions">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="loadingChat || loadingBrief"
            @click="onBrief"
          >
            <FileText :size="14" />
            {{ loadingBrief ? '生成中…' : bvid.trim() ? '观众反馈简报' : '一键生成' }}
          </button>
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            :disabled="!brief"
            @click="copyBrief"
          >
            <Copy :size="14" />
            复制
          </button>
        </div>
      </div>
      <p class="hint">
        {{ bvid.trim() ? '将基于该 BV 评论生成观众反馈简报。' : '全局简报：态势 / 话题 / 风险 / 建议。' }}
      </p>
      <h4 v-if="briefMeta?.title">{{ briefMeta.title }}</h4>
      <p v-if="brief" class="answer-text brief">{{ brief }}</p>
      <p v-else class="hint">尚未生成简报。</p>
    </section>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 0.75rem 0 0.25rem;
  font-size: 0.88rem;
  color: var(--text-secondary);
}
.actions {
  display: flex;
  gap: 0.6rem;
  margin: 0.75rem 0;
}
.head-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.answer-box {
  margin-top: 0.85rem;
}
.answer-text {
  margin: 0.5rem 0;
  color: var(--text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}
.answer-text.brief {
  padding: 0.85rem 1rem;
  background: var(--bg-tertiary);
  border-left: 2px solid var(--color-primary);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}
.digest {
  margin-top: 0.5rem;
  padding: 0.75rem;
  font-size: 0.78rem;
  overflow: auto;
  background: var(--bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.pill-ok {
  background: rgba(22, 163, 74, 0.08);
  color: var(--color-success);
  border: 1px solid rgba(22, 163, 74, 0.2);
}
</style>
