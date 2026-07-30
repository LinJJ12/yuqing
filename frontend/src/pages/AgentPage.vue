<script setup>
import { onMounted, ref } from 'vue'
import { Bot, Copy, FileText, Send } from '@lucide/vue'
import { agentBrief, agentChat, fetchAgentStatus } from '../api/client'

const question = ref('当前主要风险是什么？有哪些建议？')
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
    message.value = `来源：${res.data.provider} / ${res.data.model}`
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
    const res = await agentBrief()
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
    message.value = `简报来源：${res.data.provider} / ${res.data.model}`
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
        基于当前库内统计与样例回答问题、生成简报。优先云端 OpenAI 兼容接口，否则本机 Ollama Chat。
        {{ status?.message }}
      </p>
      <p v-if="status?.hint" class="hint">{{ status.hint }}</p>
      <p v-if="message" class="ok-text">{{ message }}</p>
      <p v-if="error" class="err">{{ error }}</p>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>舆情问答</h3>
      </div>
      <textarea v-model="question" class="textarea" rows="3" placeholder="例如：食堂相关负面主要集中在哪里？" />
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
            {{ loadingBrief ? '生成中…' : '一键生成' }}
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
      <p class="hint">比报告页「AI 摘要」更长，含态势 / 话题 / 风险 / 建议。</p>
      <h4 v-if="briefMeta?.title">{{ briefMeta.title }}</h4>
      <p v-if="brief" class="answer-text brief">{{ brief }}</p>
      <p v-else class="hint">尚未生成简报。</p>
    </section>
  </div>
</template>

<style scoped>
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
  background: var(--bg-secondary, #f8fafc);
  border-left: 3px solid #1e40af;
}
.digest {
  margin-top: 0.5rem;
  padding: 0.75rem;
  font-size: 0.78rem;
  overflow: auto;
  background: var(--bg-tertiary, #eef2f7);
  border-radius: 6px;
}
.pill-ok {
  background: #dcfce7;
  color: #166534;
}
</style>
