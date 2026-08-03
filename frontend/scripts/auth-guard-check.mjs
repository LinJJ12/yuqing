/**
 * Auth helpers + router guard regression (AC7).
 * Run: node scripts/auth-guard-check.mjs
 */
import { mkdirSync, writeFileSync, readFileSync, rmSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath, pathToFileURL } from 'url'
import { createMemoryHistory, createRouter } from 'vue-router'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const tmp = join(root, '.tmp-auth-test')

const store = new Map()
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
}
globalThis.window = {
  dispatchEvent() {},
}

mkdirSync(tmp, { recursive: true })
writeFileSync(join(tmp, 'auth.js'), readFileSync(join(root, 'src/lib/auth.js'), 'utf8'))

const auth = await import(`${pathToFileURL(join(tmp, 'auth.js')).href}?t=${Date.now()}`)
const {
  clearSession,
  getToken,
  isAuthenticated,
  safeInternalPath,
  setSession,
} = auth

let failed = 0
function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg)
    failed += 1
  } else {
    console.log('OK:', msg)
  }
}

assert(safeInternalPath('/overview') === '/overview', 'allow relative path')
assert(safeInternalPath('/alerts?x=1') === '/alerts?x=1', 'allow relative path with query')
assert(safeInternalPath('//evil.example') === '', 'reject protocol-relative')
assert(safeInternalPath('https://evil.example') === '', 'reject absolute URL')
assert(safeInternalPath(null) === '', 'reject non-string')

clearSession()
assert(!isAuthenticated(), 'cleared session is unauthenticated')
setSession({ accessToken: 'tok', username: 'admin' })
assert(isAuthenticated() && getToken() === 'tok', 'setSession stores token')
clearSession()
assert(!getToken(), 'clearSession removes token')

const stub = { template: '<div />' }
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'home', component: stub, meta: { layout: 'public' } },
    { path: '/login', name: 'login', component: stub, meta: { layout: 'public' } },
    {
      path: '/overview',
      name: 'overview',
      component: stub,
      meta: { layout: 'app', requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const needsAuth = to.matched.some(
    (record) => record.meta.requiresAuth || record.meta.layout === 'app',
  )
  if (needsAuth && !isAuthenticated()) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && isAuthenticated()) {
    return safeInternalPath(to.query.redirect) || '/overview'
  }
  return true
})

clearSession()
await router.push('/overview')
assert(
  router.currentRoute.value.name === 'login' &&
    router.currentRoute.value.query.redirect === '/overview',
  'unauthenticated overview → login with redirect',
)

setSession({ accessToken: 'tok', username: 'admin' })
await router.push({ name: 'login', query: { redirect: '//evil' } })
assert(router.currentRoute.value.path === '/overview', 'auth login + bad redirect → overview')

await router.push({ name: 'login', query: { redirect: '/overview?tab=1' } })
assert(
  router.currentRoute.value.fullPath === '/overview?tab=1',
  'auth login + safe redirect → target',
)

rmSync(tmp, { recursive: true, force: true })

if (failed) {
  console.error(`\n${failed} assertion(s) failed`)
  process.exit(1)
}
console.log('\nAll auth-guard checks passed')
