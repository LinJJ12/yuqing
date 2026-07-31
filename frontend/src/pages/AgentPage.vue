<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  Bot,
  Copy,
  Eraser,
  FileText,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Trash2,
  User,
} from '@lucide/vue'
import MarkdownContent from '../components/MarkdownContent.vue'
import VideoScopePicker from '../components/VideoScopePicker.vue'
import { fetchAgentStatus } from '../api/client'
import {
  activeConversation,
  askAgent,
  clearActiveConversation,
  createConversation,
  deleteConversation,
  generateBrief,
  listConversations,
  setActiveBvid,
  state as agent,
  switchConversation,
} from '../lib/agentSession'

const route = useRoute()
const router = useRouter()

const DEFAULT_Q_VIDEO = '该视频评论负面主要集中在哪些点？有什么建议？'
const DEFAULT_Q_GLOBAL = '当前库里整体口碑如何？有哪些需要关注的风险？'

const SUGGESTIONS_GLOBAL = [
  '当前库里整体口碑如何？有哪些需要关注的风险？',
  '最近负面评论主要在抱怨什么？',
  '帮我总结一下高频话题与情感结构。',
]
const SUGGESTIONS_VIDEO = [
  '该视频评论负面主要集中在哪些点？有什么建议？',
  '观众最认可的地方是什么？',
  '有没有需要优先处理的口碑风险？',
]

const RAIL_KEY = 'zhiwei.agent.railCollapsed'
const draft = ref('')
const showDigestId = ref('')
const threadRef = ref(null)
const inputRef = ref(null)
const syncingScope = ref(false)

function readRailCollapsed() {
  try {
    return localStorage.getItem(RAIL_KEY) === '1'
  } catch {
    return false
  }
}

const railCollapsed = ref(readRailCollapsed())

function toggleRail() {
  railCollapsed.value = !railCollapsed.value
  try {
    localStorage.setItem(RAIL_KEY, railCollapsed.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

const conv = computed(() => activeConversation.value)
const conversations = computed(() => listConversations())
const routeBvid = computed(() => String(route.query.bvid || '').trim())
const activeBvid = computed(() => routeBvid.value || conv.value?.bvid || '')
const busy = computed(() => !!(conv.value?.loadingChat || conv.value?.loadingBrief))
const suggestions = computed(() =>
  activeBvid.value ? SUGGESTIONS_VIDEO : SUGGESTIONS_GLOBAL,
)
const hasMessages = computed(() => (conv.value?.messages?.length || 0) > 0)
const messages = computed(() => conv.value?.messages || [])

const digestSummary = computed(() => {
  const d = conv.value?.digest
  if (!d || typeof d !== 'object') return ''
  const parts = []
  if (d.scope === 'video') parts.push('范围：单视频')
  else if (d.scope) parts.push(`范围：${d.scope}`)
  if (d.bvid) parts.push(`BV ${d.bvid}`)
  if (d.video_title) parts.push(String(d.video_title).slice(0, 40))
  if (d.total_posts != null) parts.push(`帖子 ${d.total_posts}`)
  if (d.comment_count != null) parts.push(`评论 ${d.comment_count}`)
  if (d.alerts_high != null) parts.push(`高风险预警 ${d.alerts_high}`)
  const by = d.by_sentiment || d.sentiment?.by_label
  if (Array.isArray(by)) {
    const bits = by
      .filter((x) => x && x.label && x.label !== 'unknown')
      .slice(0, 4)
      .map((x) => {
        const name =
          x.label === 'positive'
            ? '正'
            : x.label === 'neutral'
              ? '中'
              : x.label === 'negative'
                ? '负'
                : x.label
        return `${name} ${x.count}`
      })
    if (bits.length) parts.push(bits.join(' · '))
  } else if (by && typeof by === 'object') {
    const bits = ['positive', 'neutral', 'negative']
      .filter((k) => by[k] != null)
      .map((k) => `${k === 'positive' ? '正' : k === 'neutral' ? '中' : '负'} ${by[k]}`)
    if (bits.length) parts.push(bits.join(' · '))
  }
  return parts.join(' · ') || '已附带库内上下文'
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function scrollToBottom() {
  await nextTick()
  const el = threadRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function refreshStatus() {
  const res = await fetchAgentStatus()
  if (res.ok) agent.status = res.data
}

let scopeSyncGen = 0

function applyScopeToRoute(bvid) {
  const next = (bvid || '').trim()
  const cur = String(route.query.bvid || '').trim()
  if (next === cur) return
  const gen = ++scopeSyncGen
  syncingScope.value = true
  const q = { ...route.query }
  if (next) q.bvid = next
  else delete q.bvid
  router.replace({ query: q }).finally(() => {
    if (gen === scopeSyncGen) syncingScope.value = false
  })
}

function onNewChat() {
  createConversation({ bvid: activeBvid.value })
  draft.value = ''
  showDigestId.value = ''
  // activeId watch 会同步路由 bvid
  inputRef.value?.focus()
}

function onSwitch(id) {
  if (id === agent.activeId) return
  switchConversation(id)
  draft.value = ''
  showDigestId.value = ''
  scrollToBottom()
  inputRef.value?.focus()
}

function onDeleteConv(id, e) {
  e?.stopPropagation?.()
  const target = agent.conversations.find((c) => c.id === id)
  const label = target?.title || '该对话'
  if (!confirm(`删除会话「${label}」？`)) return
  const wasActive = id === agent.activeId
  deleteConversation(id)
  if (wasActive) {
    draft.value = ''
    showDigestId.value = ''
  }
}

async function onAsk(text) {
  const q = (text ?? draft.value).trim()
  if (!q) {
    agent.error = '请输入问题'
    return
  }
  if (busy.value) return
  const prevDraft = draft.value
  // 从输入框发送时先清空；若请求未真正发起则还原
  if (text == null) draft.value = ''
  const started = await askAgent(q, activeBvid.value || undefined)
  if (!started && text == null) draft.value = prevDraft
  await scrollToBottom()
  inputRef.value?.focus()
}

async function onBrief() {
  if (busy.value) return
  await generateBrief(activeBvid.value || undefined)
  await scrollToBottom()
}

async function copyText(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    agent.notice = '已复制到剪贴板'
    agent.error = ''
  } catch {
    agent.error = '复制失败，请手动选择文本'
  }
}

function onClear() {
  if (!confirm('清空当前会话的全部消息？')) return
  clearActiveConversation()
  draft.value = ''
  showDigestId.value = ''
  inputRef.value?.focus()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!busy.value) onAsk()
  }
}

function useSuggestion(text) {
  draft.value = ''
  onAsk(text)
}

watch(
  () => [conv.value?.messages?.length, conv.value?.loadingChat, conv.value?.loadingBrief],
  () => scrollToBottom(),
)

// 路由视频范围 → 写入当前会话
watch(
  routeBvid,
  (v) => {
    if (syncingScope.value) return
    setActiveBvid(v)
  },
)

// 切换会话后，把会话自己的 bvid 同步到路由
watch(
  () => agent.activeId,
  () => {
    const b = activeConversation.value?.bvid || ''
    const cur = routeBvid.value
    if (b === cur) return
    applyScopeToRoute(b)
  },
)

onMounted(async () => {
  // 首次进入：优先路由 bvid，否则用当前会话保存的
  if (!routeBvid.value && conv.value?.bvid) {
    applyScopeToRoute(conv.value.bvid)
  } else if (routeBvid.value) {
    setActiveBvid(routeBvid.value)
  }
  try {
    await refreshStatus()
  } catch {
    agent.error = '无法连接后端'
  }
  await scrollToBottom()
  inputRef.value?.focus()
})
</script>

<template>
  <div class="page agent-page" :class="{ 'rail-collapsed': railCollapsed }">
    <aside class="session-rail" :class="{ collapsed: railCollapsed }">
      <button
        v-if="!railCollapsed"
        type="button"
        class="btn btn-primary btn-sm new-btn"
        @click="onNewChat"
      >
        <MessageSquarePlus :size="15" />
        新对话
      </button>
      <button
        v-else
        type="button"
        class="btn btn-primary btn-sm rail-square"
        title="新对话"
        @click="onNewChat"
      >
        <MessageSquarePlus :size="16" />
      </button>
      <ul v-if="!railCollapsed" class="session-list">
        <li
          v-for="item in conversations"
          :key="item.id"
          class="session-item"
          :class="{
            active: item.id === agent.activeId,
            busy: item.loadingChat || item.loadingBrief,
          }"
        >
          <button type="button" class="session-main" @click="onSwitch(item.id)">
            <span class="session-title">{{ item.title || '新对话' }}</span>
            <span class="session-meta">
              <em v-if="item.loadingChat || item.loadingBrief">生成中</em>
              <template v-else>{{ formatTime(item.updatedAt) }}</template>
              <template v-if="item.bvid"> · {{ item.bvid }}</template>
            </span>
          </button>
          <button
            type="button"
            class="session-del"
            title="删除会话"
            @click="onDeleteConv(item.id, $event)"
          >
            <Trash2 :size="13" />
          </button>
        </li>
      </ul>
      <div v-else class="session-icons">
        <button
          v-for="item in conversations"
          :key="item.id"
          type="button"
          class="session-dot rail-square"
          :class="{
            active: item.id === agent.activeId,
            busy: item.loadingChat || item.loadingBrief,
          }"
          :title="`${item.title || '新对话'}（右键删除）`"
          @click="onSwitch(item.id)"
          @contextmenu.prevent="onDeleteConv(item.id, $event)"
        >
          {{ (item.title || '新').slice(0, 1) }}
        </button>
      </div>
    </aside>

    <div class="chat-pane">
      <div class="chat-center">
        <header class="chat-top">
          <div class="chat-top-left">
            <button
              type="button"
              class="btn btn-ghost btn-sm rail-toggle"
              :title="railCollapsed ? '展开会话栏' : '收起会话栏'"
              @click="toggleRail"
            >
              <PanelLeftOpen v-if="railCollapsed" :size="18" />
              <PanelLeftClose v-else :size="18" />
            </button>
            <Bot :size="18" class="top-icon" />
            <div>
              <h2>{{ conv?.title || '智能助手' }}</h2>
              <p class="chat-top-sub">
                {{ agent.status?.message || '多会话隔离 · 基于库内数据问答' }}
              </p>
            </div>
            <span class="pill" :class="agent.status?.ready ? 'pill-success' : 'pill-warning'">
              {{ agent.status?.ready ? '可用' : '未就绪' }}
            </span>
          </div>
          <div class="chat-top-actions">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="busy || agent.status?.ready === false"
              @click="onBrief"
            >
              <FileText :size="14" />
              {{ conv?.loadingBrief ? '生成中…' : activeBvid ? '观众反馈简报' : '生成简报' }}
            </button>
            <button
              type="button"
              class="btn btn-ghost btn-sm"
              :disabled="!hasMessages && !draft && !busy"
              @click="onClear"
            >
              <Eraser :size="14" />
              清空本会话
            </button>
          </div>
        </header>

        <VideoScopePicker :disabled="busy" label="视频范围" />

        <p v-if="agent.status && !agent.status.ready" class="banner warn">
          助手未就绪。请到
          <RouterLink to="/settings">设置</RouterLink>
          检查云端 LLM 或本机对话模型。
          <span v-if="agent.status.hint"> {{ agent.status.hint }}</span>
        </p>
        <p v-if="agent.error" class="banner err">{{ agent.error }}</p>
        <p v-else-if="agent.notice" class="banner ok">{{ agent.notice }}</p>
        <p v-if="busy" class="banner ok">
          {{
            conv?.loadingBrief
              ? '简报生成中，切换会话/页面也不会串台…'
              : '回答生成中，切换会话/页面也不会串台…'
          }}
        </p>

        <div ref="threadRef" class="chat-thread">
          <div class="chat-inner">
          <div v-if="!hasMessages && !conv?.loadingChat" class="empty-state">
            <div class="empty-icon">
              <Bot :size="28" />
            </div>
            <h3>有什么想了解的？</h3>
            <p>
              {{
                activeBvid
                  ? '当前会话将基于该视频评论回答。'
                  : '当前会话默认用全局库；可从上方选择单视频。可用会话栏新建或切换对话。'
              }}
            </p>
            <div class="suggest-grid">
              <button
                v-for="s in suggestions"
                :key="s"
                type="button"
                class="suggest-card"
                :disabled="busy || agent.status?.ready === false"
                @click="useSuggestion(s)"
              >
                {{ s }}
              </button>
            </div>
          </div>

          <article
            v-for="msg in messages"
            :key="msg.id"
            class="msg"
            :class="[msg.role, { error: msg.error }]"
          >
            <div class="msg-avatar" aria-hidden="true">
              <Bot v-if="msg.role === 'assistant'" :size="16" />
              <User v-else :size="16" />
            </div>
            <div class="msg-body">
              <header class="msg-head">
                <b>{{ msg.role === 'assistant' ? (msg.kind === 'brief' ? '简报' : '助手') : '你' }}</b>
                <span v-if="msg.title" class="msg-title">{{ msg.title }}</span>
                <span v-if="msg.meta" class="msg-meta">{{ msg.meta }}</span>
              </header>
              <MarkdownContent
                v-if="msg.role === 'assistant'"
                class="msg-md"
                :source="msg.content"
              />
              <p v-else class="msg-text">{{ msg.content }}</p>
              <div v-if="msg.role === 'assistant' && !msg.error" class="msg-actions">
                <button type="button" class="btn btn-ghost btn-sm" @click="copyText(msg.content)">
                  <Copy :size="13" />
                  复制
                </button>
                <button
                  v-if="conv?.digest && msg.kind === 'chat'"
                  type="button"
                  class="btn btn-ghost btn-sm"
                  @click="showDigestId = showDigestId === msg.id ? '' : msg.id"
                >
                  {{ showDigestId === msg.id ? '收起引用' : '引用摘要' }}
                </button>
              </div>
              <p v-if="showDigestId === msg.id && digestSummary" class="digest-line">
                {{ digestSummary }}
              </p>
            </div>
          </article>

          <article v-if="conv?.loadingChat || conv?.loadingBrief" class="msg assistant thinking">
            <div class="msg-avatar" aria-hidden="true">
              <Bot :size="16" />
            </div>
            <div class="msg-body">
              <header class="msg-head"><b>助手</b></header>
              <p class="thinking-dots">
                {{ conv?.loadingBrief ? '正在生成简报' : '正在思考' }}
                <span /><span /><span />
              </p>
            </div>
          </article>
          </div>
        </div>

        <footer class="composer">
          <div class="composer-inner">
            <div class="composer-box">
              <textarea
                ref="inputRef"
                v-model="draft"
                class="composer-input"
                rows="1"
                :placeholder="activeBvid ? DEFAULT_Q_VIDEO : DEFAULT_Q_GLOBAL"
                :disabled="busy"
                @keydown="onKeydown"
              />
              <button
                type="button"
                class="btn btn-primary send-btn"
                :disabled="busy || !draft.trim() || agent.status?.ready === false"
                title="发送（Enter）"
                @click="onAsk()"
              >
                <Send :size="16" />
              </button>
            </div>
            <p class="composer-hint">Enter 发送 · Shift+Enter 换行 · 各会话消息互不影响</p>
          </div>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-page {
  display: grid;
  grid-template-columns: 14rem minmax(0, 1fr);
  gap: 0.75rem;
  width: auto;
  max-width: none;
  /* 铺满内容区，盖住全局灰蓝底 */
  margin: -1rem -1.25rem -1.75rem;
  padding: 1rem 1.25rem 1.25rem;
  height: calc(100dvh - var(--topbar-h));
  min-height: 28rem;
  background: #fff;
  color: var(--text-primary);
  transition: grid-template-columns 0.2s ease;
}
.agent-page.rail-collapsed {
  padding-left: 0.5rem;
  grid-template-columns: 2.75rem minmax(0, 1fr);
  gap: 0.5rem;
}

.session-rail {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 0;
  min-width: 0;
  padding: 0 0.65rem 0 0;
  border-right: 1px solid var(--color-border);
  box-sizing: border-box;
}
.session-rail.collapsed {
  padding: 0;
  gap: 0.4rem;
  align-items: center;
  border-right: none;
}

.new-btn {
  width: 100%;
  justify-content: center;
  flex-shrink: 0;
}

/* 收起/展开只放在聊天标题栏，位置固定 */
.rail-toggle {
  width: 2rem;
  height: 2rem;
  min-width: 2rem;
  min-height: 2rem;
  padding: 0;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  border-radius: 0.55rem;
  color: var(--text-secondary);
}

.rail-square {
  width: 2rem;
  height: 2rem;
  min-width: 2rem;
  min-height: 2rem;
  max-width: 2rem;
  padding: 0;
  margin: 0;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  box-sizing: border-box;
  border-radius: 0.55rem;
  line-height: 1;
}

.session-icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 0;
  margin: 0;
  box-sizing: border-box;
}

.session-dot {
  border: 1px solid var(--color-border);
  background: #fff;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
}
.session-dot:hover {
  border-color: rgba(15, 118, 110, 0.35);
  color: var(--color-primary);
}
.session-dot.active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.35);
  color: var(--color-primary);
}
.session-dot.busy {
  outline: 2px solid rgba(15, 118, 110, 0.25);
}
.session-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.session-item {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: stretch;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
}
.session-item:hover {
  background: #fff;
  border-color: var(--color-border);
}
.session-item.active {
  background: rgba(15, 118, 110, 0.08);
  border-color: rgba(15, 118, 110, 0.22);
}
.session-item.busy .session-meta em {
  color: var(--color-primary);
  font-style: normal;
}
.session-main {
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.55rem 0.45rem 0.55rem 0.6rem;
  cursor: pointer;
  min-width: 0;
  font: inherit;
}
.session-title {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.7rem;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-del {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  padding: 0 0.45rem;
  cursor: pointer;
  opacity: 0;
}
.session-item:hover .session-del,
.session-item.active .session-del {
  opacity: 1;
}
.session-del:hover {
  color: var(--color-destructive);
}

.chat-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  align-items: stretch;
}
.agent-page.rail-collapsed .chat-pane {
  padding-left: 0.75rem;
}
.chat-center {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 48rem;
  margin: 0 auto;
}

.chat-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  flex-shrink: 0;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0.35rem;
}
.chat-top-left {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  min-width: 0;
}
.top-icon {
  flex-shrink: 0;
  margin-top: 0.15rem;
  color: var(--color-primary);
}
.chat-top h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 18rem;
}
.chat-top-sub {
  margin: 0.15rem 0 0;
  font-size: 0.78rem;
  color: var(--text-tertiary);
  line-height: 1.4;
}
.chat-top-actions {
  display: flex;
  gap: 0.4rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.banner {
  flex-shrink: 0;
  margin: 0 0 0.45rem;
  font-size: 0.82rem;
  line-height: 1.45;
}
.banner.warn {
  color: #b45309;
}
.banner.ok {
  color: var(--color-success);
}
.banner.err {
  color: var(--color-destructive);
}

.chat-thread {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.25rem 0.15rem 1rem;
}
.chat-inner {
  width: 100%;
  margin: 0;
}

.empty-state {
  text-align: center;
  padding: 2.5rem 1rem 1.5rem;
}
.empty-icon {
  display: inline-grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background: rgba(15, 118, 110, 0.1);
  color: var(--color-primary);
  margin-bottom: 0.85rem;
}
.empty-state h3 {
  margin: 0 0 0.35rem;
  font-size: 1.15rem;
  font-weight: 650;
}
.empty-state > p {
  margin: 0 auto 1.25rem;
  max-width: 26rem;
  font-size: 0.875rem;
  color: var(--text-tertiary);
  line-height: 1.5;
}
.suggest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.55rem;
  text-align: left;
}
.suggest-card {
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: #fff;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.45;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.suggest-card:hover:not(:disabled) {
  border-color: rgba(15, 118, 110, 0.35);
  background: rgba(15, 118, 110, 0.04);
  color: var(--text-primary);
}
.suggest-card:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.msg {
  display: grid;
  grid-template-columns: 2rem 1fr;
  gap: 0.7rem;
  padding: 0.85rem 0.25rem;
}
.msg + .msg {
  border-top: 1px solid var(--color-border);
}
.msg-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  margin-top: 0.1rem;
}
.msg.user .msg-avatar {
  background: #e2e8f0;
  color: #475569;
}
.msg.assistant .msg-avatar {
  background: rgba(15, 118, 110, 0.12);
  color: var(--color-primary);
}
.msg-body {
  min-width: 0;
}
.msg-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.45rem;
  margin-bottom: 0.35rem;
}
.msg-head b {
  font-size: 0.85rem;
  font-weight: 650;
}
.msg-title {
  font-size: 0.78rem;
  color: var(--color-primary);
  font-weight: 600;
}
.msg-meta {
  font-size: 0.72rem;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}
.msg-text {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.msg-md {
  font-size: 0.9375rem;
}
.msg.error .msg-md,
.msg.error .msg-text {
  color: var(--color-destructive);
}
.msg-actions {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.45rem;
}
.digest-line {
  margin: 0.4rem 0 0;
  font-size: 0.8rem;
  color: var(--text-tertiary);
  line-height: 1.45;
}

.thinking-dots {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.thinking-dots span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.4;
  animation: blink 1.2s infinite ease-in-out;
}
.thinking-dots span:nth-child(2) {
  animation-delay: 0.15s;
}
.thinking-dots span:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

.composer {
  flex-shrink: 0;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
  background: #fff;
}
.composer-inner {
  width: 100%;
  margin: 0;
}
.composer-box {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.55rem 0.55rem 0.55rem 0.85rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 1rem;
  box-shadow: var(--shadow-sm);
}
.composer-box:focus-within {
  border-color: rgba(15, 118, 110, 0.45);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
}
.composer-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font: inherit;
  font-size: 0.9375rem;
  line-height: 1.5;
  max-height: 8rem;
  padding: 0.35rem 0;
  color: var(--text-primary);
}
.composer-input::placeholder {
  color: var(--text-tertiary);
}
.send-btn {
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  border-radius: 0.65rem;
  flex-shrink: 0;
}
.composer-hint {
  margin: 0.4rem 0 0;
  text-align: center;
  font-size: 0.72rem;
  color: var(--text-tertiary);
}

@media (max-width: 900px) {
  .agent-page,
  .agent-page.rail-collapsed {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100dvh - var(--topbar-h));
    margin: -1rem -1.25rem -1.75rem;
    padding: 1rem 1.25rem 1.25rem;
  }
  .agent-page.rail-collapsed .chat-pane {
    padding-left: 0;
  }
  .session-rail,
  .session-rail.collapsed {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    padding: 0 0 0.65rem;
    max-height: 10rem;
    align-items: stretch;
  }
  .session-rail.collapsed {
    max-height: none;
  }
  .session-list {
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .session-icons {
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    justify-content: flex-start;
    width: 100%;
  }
  .session-item {
    min-width: 10rem;
  }
  .chat-pane {
    min-height: 24rem;
  }
  .chat-center {
    max-width: none;
  }
  .chat-top {
    flex-direction: column;
  }
  .suggest-grid {
    grid-template-columns: 1fr;
  }
}
</style>
