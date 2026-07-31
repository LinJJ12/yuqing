/**
 * Feedback loop for agentSession isolation / race bugs.
 * Run: node scripts/agent-session-check.mjs
 */
import { mkdirSync, writeFileSync, readFileSync, rmSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath, pathToFileURL } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const tmp = join(root, '.tmp-agent-test')

const store = new Map()
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
}

let chatImpl = async () => ({
  ok: true,
  data: {
    content: 'ans',
    provider: 'p',
    model: 'm',
    context_digest: { scope: 'global' },
  },
})
let briefImpl = async () => ({
  ok: true,
  data: {
    content: 'brief',
    title: 't',
    provider: 'p',
    model: 'm',
    context_digest: { scope: 'global' },
  },
})

mkdirSync(tmp, { recursive: true })
writeFileSync(
  join(tmp, 'client.js'),
  `
export async function agentChat(q, hist, opts) { return globalThis.__chat(q, hist, opts) }
export async function agentBrief(opts) { return globalThis.__brief(opts) }
`,
)

const src = readFileSync(join(root, 'src/lib/agentSession.js'), 'utf8').replace(
  "from '../api/client'",
  "from './client.js'",
)
writeFileSync(join(tmp, 'agentSession.js'), src)

globalThis.__chat = (...a) => chatImpl(...a)
globalThis.__brief = (...a) => briefImpl(...a)

const mod = await import(`${pathToFileURL(join(tmp, 'agentSession.js')).href}?t=${Date.now()}`)
const {
  state,
  askAgent,
  clearActiveConversation,
  createConversation,
  deleteConversation,
  generateBrief,
  activeConversation,
  listConversations,
} = mod

let failed = 0
function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg)
    failed += 1
  } else {
    console.log('OK:', msg)
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

// --- 1) clear during in-flight must drop late answer
let release
chatImpl = () => new Promise((r) => { release = r })
const p1 = askAgent('q1')
await sleep(20)
assert(activeConversation.value.loadingChat === true, 'loading while in flight')
clearActiveConversation()
assert(activeConversation.value.messages.length === 0, 'cleared messages')
release({
  ok: true,
  data: { content: 'late', provider: 'p', model: 'm', context_digest: null },
})
await p1
assert(
  activeConversation.value.messages.length === 0,
  `late answer must not appear after clear (got ${activeConversation.value.messages.length})`,
)

// --- 2) background session failure must not set global error on another session
createConversation()
const idA = state.activeId
chatImpl = () => new Promise((r) => { release = r })
const p2 = askAgent('qA')
await sleep(20)
createConversation()
const idB = state.activeId
assert(idA !== idB, 'switched to new conv')
state.error = ''
release({ ok: false, error: { message: 'boom-A' } })
await p2
assert(
  state.error === '',
  `background failure must not set global error (got ${JSON.stringify(state.error)})`,
)
const convA = state.conversations.find((c) => c.id === idA)
assert(convA?.messages?.some((m) => m.error), 'error message stored on A')

// --- 3) delete during in-flight must not throw / must not revive deleted
chatImpl = () => new Promise((r) => { release = r })
const p3 = askAgent('q-del')
await sleep(20)
const doomed = state.activeId
createConversation()
deleteConversation(doomed)
release({
  ok: true,
  data: { content: 'ghost', provider: 'p', model: 'm', context_digest: null },
})
await p3
assert(
  !state.conversations.some((c) => c.id === doomed),
  'deleted conversation stays deleted',
)
assert(
  !state.conversations.some((c) => c.messages?.some((m) => m.content === 'ghost')),
  'ghost answer not written elsewhere',
)

// --- 4) stale activeId falls back safely
state.activeId = 'missing-id'
assert(activeConversation.value != null, 'activeConversation falls back')
assert(listConversations().length >= 1, 'still has conversations')

// --- 5) brief catch should attach error message (when implemented)
let rejectBrief
briefImpl = () => new Promise((_, rej) => { rejectBrief = rej })
createConversation()
const p5 = generateBrief()
await sleep(20)
rejectBrief(new Error('net-down'))
await p5
const briefConv = activeConversation.value
assert(
  briefConv.loadingBrief === false,
  'brief loading cleared after throw',
)
assert(
  briefConv.messages.some(
    (m) => m.error || String(m.content).includes('失败') || String(m.content).includes('net-down'),
  ),
  'brief network error should leave a message in the thread',
)

rmSync(tmp, { recursive: true, force: true })

if (failed) {
  console.error(`\n${failed} assertion(s) failed`)
  process.exit(1)
}
console.log('\nAll checks passed')
