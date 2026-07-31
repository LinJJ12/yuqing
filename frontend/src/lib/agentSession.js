/**
 * 助手多会话：彼此隔离；切页不丢；请求完成后按会话 id + 请求代数回写。
 */
import { computed, reactive, watch } from 'vue'
import { agentBrief, agentChat } from '../api/client'

const STORAGE_KEY = 'zhiwei.agent.sessions.v3'
const LEGACY_V2 = 'zhiwei.agent.session.v2'
const LEGACY_V1 = 'zhiwei.agent.session'

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function blankConversation(partial = {}) {
  const now = Date.now()
  return {
    id: uid(),
    title: '新对话',
    createdAt: now,
    updatedAt: now,
    bvid: '',
    messages: [],
    digest: null,
    pendingQuestion: '',
    loadingChat: false,
    loadingBrief: false,
    chatReqId: 0,
    briefReqId: 0,
    ...partial,
  }
}

function titleFromMessages(messages) {
  const firstUser = (messages || []).find((m) => m.role === 'user' && m.content)
  if (!firstUser) return '新对话'
  const t = String(firstUser.content).replace(/\s+/g, ' ').trim()
  return t.length > 28 ? `${t.slice(0, 28)}…` : t
}

function migrateLegacy() {
  // v2 单会话
  try {
    const raw2 = localStorage.getItem(LEGACY_V2)
    if (raw2) {
      const old = JSON.parse(raw2)
      if (old && Array.isArray(old.messages) && old.messages.length) {
        const conv = blankConversation({
          messages: old.messages,
          digest: old.digest || null,
          pendingQuestion: old.pendingQuestion || '',
          title: titleFromMessages(old.messages),
          bvid: typeof old.bvid === 'string' ? old.bvid : '',
        })
        return { activeId: conv.id, conversations: [conv] }
      }
    }
  } catch {
    /* ignore */
  }
  // v1 表单
  try {
    const raw1 = localStorage.getItem(LEGACY_V1)
    if (!raw1) return null
    const old = JSON.parse(raw1)
    if (!old || typeof old !== 'object') return null
    const messages = []
    if (Array.isArray(old.history)) {
      for (const h of old.history) {
        if (h?.role && h?.content) {
          messages.push({ id: uid(), role: h.role, content: h.content, kind: 'chat' })
        }
      }
    }
    if (old.brief) {
      messages.push({
        id: uid(),
        role: 'assistant',
        content: old.brief,
        kind: 'brief',
        title: old.briefMeta?.title || '简报',
      })
    }
    if (!messages.length) return null
    const conv = blankConversation({
      messages,
      digest: old.digest || null,
      title: titleFromMessages(messages),
      bvid: typeof old.bvid === 'string' ? old.bvid : '',
    })
    return { activeId: conv.id, conversations: [conv] }
  } catch {
    return null
  }
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data && Array.isArray(data.conversations) && data.conversations.length) {
        return data
      }
    }
  } catch {
    /* ignore */
  }
  return migrateLegacy()
}

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        activeId: state.activeId,
        conversations: state.conversations.map((c) => ({
          id: c.id,
          title: c.title,
          createdAt: c.createdAt,
          updatedAt: c.updatedAt,
          bvid: c.bvid,
          messages: c.messages,
          digest: c.digest,
          pendingQuestion: c.pendingQuestion,
          // 不持久化 loading / reqId
        })),
      }),
    )
  } catch {
    /* ignore */
  }
}

const saved = load()
const initial =
  saved && saved.conversations?.length
    ? saved
    : (() => {
        const c = blankConversation()
        return { activeId: c.id, conversations: [c] }
      })()

const conversations = initial.conversations.map((c) => ({
  ...blankConversation(),
  ...c,
  loadingChat: false,
  loadingBrief: false,
  chatReqId: 0,
  briefReqId: 0,
}))

let activeId = initial.activeId
if (!conversations.some((c) => c.id === activeId)) {
  activeId = conversations[0]?.id || ''
}

export const state = reactive({
  activeId,
  conversations,
  error: '',
  notice: '',
  status: null,
})

export const activeConversation = computed(() => {
  return (
    state.conversations.find((c) => c.id === state.activeId) || state.conversations[0] || null
  )
})

watch(
  () => state.conversations,
  () => persist(),
  { deep: true },
)
watch(
  () => state.activeId,
  () => persist(),
)

function getConv(id) {
  return state.conversations.find((c) => c.id === id) || null
}

function touch(conv) {
  conv.updatedAt = Date.now()
  if (conv.title === '新对话' || !conv.title) {
    conv.title = titleFromMessages(conv.messages)
  }
}

function setUiFeedback(convId, { error, notice } = {}) {
  if (state.activeId !== convId) return
  if (error !== undefined) state.error = error
  if (notice !== undefined) state.notice = notice
}

function invalidateRequests(conv) {
  if (!conv) return
  conv.chatReqId = (conv.chatReqId || 0) + 1
  conv.briefReqId = (conv.briefReqId || 0) + 1
  conv.loadingChat = false
  conv.loadingBrief = false
  conv.pendingQuestion = ''
}

function isChatLive(conv, reqId) {
  return !!(conv && conv.chatReqId === reqId)
}

function isBriefLive(conv, reqId) {
  return !!(conv && conv.briefReqId === reqId)
}

function historyForApi(conv) {
  return (conv.messages || [])
    .filter(
      (m) =>
        m.kind !== 'brief' &&
        m.kind !== 'brief-req' &&
        (m.role === 'user' || m.role === 'assistant') &&
        !m.error,
    )
    .slice(-6)
    .map((m) => ({ role: m.role, content: m.content }))
}

export function listConversations() {
  return [...state.conversations].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
}

export function createConversation({ bvid = '' } = {}) {
  const conv = blankConversation({ bvid: bvid || '' })
  state.conversations.unshift(conv)
  state.activeId = conv.id
  state.error = ''
  state.notice = ''
  persist()
  return conv
}

export function switchConversation(id) {
  const conv = getConv(id)
  if (!conv) return null
  state.activeId = conv.id
  state.error = ''
  state.notice = ''
  persist()
  return conv
}

export function deleteConversation(id) {
  const idx = state.conversations.findIndex((c) => c.id === id)
  if (idx < 0) return
  const wasActive = state.activeId === id
  state.conversations.splice(idx, 1)
  if (!state.conversations.length) {
    const c = blankConversation()
    state.conversations.push(c)
    state.activeId = c.id
  } else if (wasActive) {
    const sorted = listConversations()
    state.activeId = sorted[0].id
  }
  state.error = ''
  state.notice = ''
  persist()
}

export function clearActiveConversation() {
  const conv = activeConversation.value
  if (!conv) return
  invalidateRequests(conv)
  conv.messages = []
  conv.digest = null
  conv.title = '新对话'
  conv.updatedAt = Date.now()
  state.error = ''
  state.notice = ''
  persist()
}

export function setActiveBvid(bvid) {
  const conv = activeConversation.value
  if (!conv) return
  conv.bvid = bvid || ''
  persist()
}

/** @returns {Promise<boolean>} 是否已发起请求 */
export async function askAgent(question, bvid) {
  const q = String(question || '').trim()
  if (!q) {
    state.error = '请输入问题'
    return false
  }
  if (state.status?.ready === false) {
    state.error = '助手未就绪，请先到设置检查模型'
    return false
  }

  let conv = activeConversation.value
  if (!conv) conv = createConversation({ bvid: bvid || '' })
  const convId = conv.id
  if (conv.loadingChat || conv.loadingBrief) return false

  state.error = ''
  state.notice = ''
  conv.chatReqId = (conv.chatReqId || 0) + 1
  const reqId = conv.chatReqId
  conv.messages.push({ id: uid(), role: 'user', content: q, kind: 'chat' })
  conv.pendingQuestion = q
  conv.loadingChat = true
  if (bvid != null) conv.bvid = bvid || ''
  touch(conv)
  persist()

  const hist = historyForApi(conv).slice(0, -1)
  try {
    const res = await agentChat(q, hist, { bvid: bvid || undefined })
    const target = getConv(convId)
    if (!isChatLive(target, reqId)) return true

    if (!res.ok) {
      setUiFeedback(convId, { error: res.error?.message || '问答失败', notice: '' })
      target.messages.push({
        id: uid(),
        role: 'assistant',
        content: `抱歉，本次回答失败：${res.error?.message || '未知错误'}`,
        kind: 'chat',
        error: true,
      })
      touch(target)
      return true
    }
    target.digest = res.data.context_digest || null
    target.messages.push({
      id: uid(),
      role: 'assistant',
      content: res.data.content || '',
      kind: 'chat',
      meta: `${res.data.provider} / ${res.data.model}`,
    })
    touch(target)
    const scope = res.data.context_digest?.scope === 'video' ? '单视频' : '全局'
    setUiFeedback(convId, {
      notice: `来源：${res.data.provider} / ${res.data.model}（${scope}）`,
      error: '',
    })
  } catch (e) {
    const target = getConv(convId)
    if (!isChatLive(target, reqId)) return true
    setUiFeedback(convId, { error: e.message || '请求失败', notice: '' })
    target.messages.push({
      id: uid(),
      role: 'assistant',
      content: `请求失败：${e.message || '网络错误'}`,
      kind: 'chat',
      error: true,
    })
    touch(target)
  } finally {
    const target = getConv(convId)
    if (isChatLive(target, reqId)) {
      target.loadingChat = false
      target.pendingQuestion = ''
    }
    persist()
  }
  return true
}

/** @returns {Promise<boolean>} 是否已发起请求 */
export async function generateBrief(bvid) {
  if (state.status?.ready === false) {
    state.error = '助手未就绪，请先到设置检查模型'
    return false
  }

  let conv = activeConversation.value
  if (!conv) conv = createConversation({ bvid: bvid || '' })
  const convId = conv.id
  if (conv.loadingBrief || conv.loadingChat) return false

  state.error = ''
  state.notice = ''
  conv.briefReqId = (conv.briefReqId || 0) + 1
  const reqId = conv.briefReqId
  const prompt = bvid ? '请基于当前视频生成观众反馈简报' : '请生成全局舆情简报'
  conv.messages.push({ id: uid(), role: 'user', content: prompt, kind: 'brief-req' })
  conv.loadingBrief = true
  if (bvid != null) conv.bvid = bvid || ''
  touch(conv)
  persist()

  try {
    const res = await agentBrief({ bvid: bvid || undefined })
    const target = getConv(convId)
    if (!isBriefLive(target, reqId)) return true

    if (!res.ok) {
      setUiFeedback(convId, { error: res.error?.message || '简报生成失败', notice: '' })
      target.messages.push({
        id: uid(),
        role: 'assistant',
        content: `简报生成失败：${res.error?.message || '未知错误'}`,
        kind: 'chat',
        error: true,
      })
      touch(target)
      return true
    }
    target.digest = res.data.context_digest || target.digest
    target.messages.push({
      id: uid(),
      role: 'assistant',
      content: res.data.content || '',
      kind: 'brief',
      title: res.data.title || '简报',
      meta: `${res.data.provider} / ${res.data.model}`,
    })
    touch(target)
    const scope = res.data.context_digest?.scope === 'video' ? '观众反馈' : '全局'
    setUiFeedback(convId, {
      notice: `简报来源：${res.data.provider} / ${res.data.model}（${scope}）`,
      error: '',
    })
  } catch (e) {
    const target = getConv(convId)
    if (!isBriefLive(target, reqId)) return true
    setUiFeedback(convId, { error: e.message || '请求失败', notice: '' })
    target.messages.push({
      id: uid(),
      role: 'assistant',
      content: `简报生成失败：${e.message || '网络错误'}`,
      kind: 'chat',
      error: true,
    })
    touch(target)
  } finally {
    const target = getConv(convId)
    if (isBriefLive(target, reqId)) target.loadingBrief = false
    persist()
  }
  return true
}

/** @deprecated 使用 clearActiveConversation / deleteConversation */
export function clearAgentSession() {
  clearActiveConversation()
}
