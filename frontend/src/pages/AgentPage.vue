<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Bot, Copy, Eraser, FileText, Send } from '@lucide/vue'
import MarkdownContent from '../components/MarkdownContent.vue'
import { agentBrief, agentChat, fetchAgentStatus } from '../api/client'

const route = useRoute()
const STORAGE_KEY = 'zhiwei.agent.session'
const DEFAULT_Q_VIDEO = '该视频评论负面主要集中在哪些点？有什么建议？'
const DEFAULT_Q_GLOBAL = '当前库里整体口碑如何？有哪些需要关注的风险？'

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    return data && typeof data === 'object' ? data : null
  } catch {
    return null
  }
}

function saveSession(payload) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* ignore quota / private mode */
  }
}

const saved = loadSession()

const question = ref(typeof saved?.question === 'string' ? saved.question : DEFAULT_Q_VIDEO)
const bvid = ref(typeof saved?.bvid === 'string' ? saved.bvid : '')
const history = ref(Array.isArray(saved?.history) ? saved.history : [])
const answer = ref(typeof saved?.answer === 'string' ? saved.answer : '')
const digest = ref(saved?.digest && typeof saved.digest === 'object' ? saved.digest : null)
const brief = ref(typeof saved?.brief === 'string' ? saved.brief : '')
const briefMeta = ref(saved?.briefMeta && typeof saved.briefMeta === 'object' ? saved.briefMeta : null)
const status = ref(null)
const showDigest = ref(Boolean(saved?.showDigest))
const loadingChat = ref(false)
const loadingBrief = ref(false)
const error = ref('')
const message = ref(typeof saved?.message === 'string' ? saved.message : '')

const digestSummary = computed(() => {
  const d = digest.value
  if (!d || typeof d !== 'object') return ''
  const parts = []
  if (d.scope === 'video') parts.push('范围：单视频')
  else if (d.scope) parts.push(`范围：${d.scope}`)
  if (d.bvid) parts.push(`BV ${d.bvid}`)
  if (d.video_title) parts.push(String(d.video_title).slice(0, 40))
  if (d.total_posts != null) parts.push(`帖子 ${d.total_posts}`)
  if (d.comment_count != null) parts.push(`评论 ${d.comment_count}`)
  if (d.alerts_high != null) parts.push(`高风险预警 ${d.alerts_high}`)
  // by_sentiment 可能是数组 [{label,count}] 或对象
  const by = d.by_sentiment || d.sentiment?.by_label
  if (Array.isArray(by)) {
    const bits = by
      .filter((x) => x && x.label && x.label !== 'unknown')
      .slice(0, 4)
      .map((x) => {
        const name =
          x.label === 'positive' ? '正' : x.label === 'neutral' ? '中' : x.label === 'negative' ? '负' : x.label
        return `${name} ${x.count}`
      })
    if (bits.length) parts.push(bits.join(' · '))
  } else if (by && typeof by === 'object') {
    const bits = ['positive', 'neutral', 'negative']
      .filter((k) => by[k] != null)
      .map((k) => `${k === 'positive' ? '正' : k === 'neutral' ? '中' : '负'} ${by[k]}`)
    if (bits.length) parts.push(bits.join(' · '))
  }
  if (d.conclusion) parts.push(`结论摘要已附带`)
  return parts.join(' · ') || '已附带库内上下文'
})

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

function clearSession() {
  answer.value = ''
  digest.value = null
  history.value = []
  brief.value = ''
  briefMeta.value = null
  showDigest.value = false
  message.value = ''
  error.value = ''
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

watch(
  () => route.query.bvid,
  (v) => {
    if (v) bvid.value = String(v)
  },
  { immediate: true },
)

watch(
  () => bvid.value.trim(),
  (has) => {
    const q = question.value.trim()
    if (!q || q === DEFAULT_Q_VIDEO || q === DEFAULT_Q_GLOBAL) {
      question.value = has ? DEFAULT_Q_VIDEO : DEFAULT_Q_GLOBAL
    }
  },
  { immediate: true },
)

watch(
  [bvid, question, history, answer, digest, brief, briefMeta, message, showDigest],
  () => {
    saveSession({
      bvid: bvid.value,
      question: question.value,
      history: history.value,
      answer: answer.value,
      digest: digest.value,
      brief: brief.value,
      briefMeta: briefMeta.value,
      message: message.value,
      showDigest: showDigest.value,
    })
  },
  { deep: true },
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
        可填视频号限定「单视频观众反馈」；留空则用全局库统计。优先云端大模型，否则使用本机对话模型。
        {{ status?.message }}
      </p>
      <p v-if="status?.hint" class="hint">{{ status.hint }}</p>
      <p v-if="status && !status.ready" class="hint warn-cta">
        助手未就绪时问答/简报不可用。请到
        <RouterLink to="/settings">设置</RouterLink>
        检查云端 LLM 或本机对话模型。
      </p>
      <label class="field">
        视频号 / 链接（可选，限定单视频）
        <input v-model="bvid" class="input" placeholder="留空=全局；填写后按该视频评论回答" />
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
        :placeholder="bvid.trim() ? DEFAULT_Q_VIDEO : DEFAULT_Q_GLOBAL"
      />
      <div class="actions">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="loadingChat || loadingBrief || status?.ready === false"
          @click="onAsk"
        >
          <Send :size="16" />
          {{ loadingChat ? '思考中…' : '提问' }}
        </button>
        <button
          type="button"
          class="btn btn-ghost"
          :disabled="!answer && !brief && !history.length"
          @click="clearSession"
        >
          <Eraser :size="16" />
          清空结果
        </button>
      </div>
      <div v-if="answer" class="answer-box">
        <header class="post-meta">
          <Bot :size="16" />
          <b>回答</b>
        </header>
        <MarkdownContent class="answer-md" :source="answer" />
        <button type="button" class="btn btn-ghost btn-sm" @click="showDigest = !showDigest">
          {{ showDigest ? '收起' : '展开' }}引用摘要
        </button>
        <p v-if="showDigest && digestSummary" class="digest-human">{{ digestSummary }}</p>
        <pre v-else-if="showDigest && digest" class="digest">{{ JSON.stringify(digest, null, 2) }}</pre>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>生成简报</h3>
        <div class="head-actions">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="loadingChat || loadingBrief || status?.ready === false"
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
        {{ bvid.trim() ? '将基于该视频评论生成观众反馈简报。' : '全局简报：态势 / 话题 / 风险 / 建议。' }}
      </p>
      <h4 v-if="briefMeta?.title">{{ briefMeta.title }}</h4>
      <MarkdownContent v-if="brief" class="answer-md brief" :source="brief" />
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
.warn-cta {
  color: #b45309;
}
.actions {
  display: flex;
  gap: 0.6rem;
  margin: 0.75rem 0;
}
.answer-box {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}
.answer-md {
  margin-top: 0.35rem;
}
.answer-md.brief {
  margin-top: 0.5rem;
}
.digest-human {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.45;
}
.digest {
  margin-top: 0.5rem;
  padding: 0.65rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  overflow: auto;
  max-height: 14rem;
}
.head-actions {
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
}
</style>
