import axios from 'axios'

/**
 * 优先走 Vite 代理 `/api`；失败时直连后端。
 * 业务错误看 body.ok（HTTP 4xx/5xx 也可能带统一错误体）。
 */
const DIRECT = 'http://127.0.0.1:8001/api/v1'
const PROXY = '/api/v1'

function createClient(timeout) {
  return axios.create({
    baseURL: PROXY,
    timeout,
    validateStatus: () => true,
  })
}

export const api = createClient(30000)
export const slowApi = createClient(600000)

function shouldFallback(status, hasBody) {
  if (!status) return true
  // 代理到错误旧进程时常 404；网关类错误也回退
  return status === 404 || status === 502 || status === 503 || status === 504 || !hasBody
}

async function withFallback(client, method, url, config = {}) {
  try {
    const res = await client.request({ method, url, ...config })
    if (shouldFallback(res.status, !!res.data) && res.status !== 200) {
      const fallback = axios.create({
        baseURL: DIRECT,
        timeout: client.defaults.timeout,
        validateStatus: () => true,
      })
      const retry = await fallback.request({ method, url, ...config })
      return retry
    }
    return res
  } catch (err) {
    const fallback = axios.create({
      baseURL: DIRECT,
      timeout: client.defaults.timeout,
      validateStatus: () => true,
    })
    return fallback.request({ method, url, ...config })
  }
}

export async function fetchHealthReady() {
  const { data } = await withFallback(api, 'get', '/health/ready')
  return data
}

export async function fetchOverview() {
  const { data } = await withFallback(api, 'get', '/dashboard/overview')
  return data
}

export async function fetchPosts({ topic, limit = 50, offset = 0 } = {}) {
  const { data } = await withFallback(api, 'get', '/posts', {
    params: { topic, limit, offset },
  })
  return data
}

export async function fetchImports(limit = 20) {
  const { data } = await withFallback(api, 'get', '/imports', { params: { limit } })
  return data
}

export async function uploadImport(file, { topic = '文件导入', platform = 'campus' } = {}) {
  const form = new FormData()
  form.append('file', file)
  form.append('topic', topic)
  form.append('platform', platform)
  const res = await withFallback(api, 'post', '/imports', { data: form })
  return res.data
}

export async function fetchAnalysisStatus() {
  const { data } = await withFallback(api, 'get', '/analysis/status')
  return data
}

export async function previewSentiment(text) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/sentiment/preview', {
    data: { text },
  })
  return data
}

export async function runSentiment({ limit = 500, only_pending = true } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/sentiment/run', {
    data: { limit, only_pending },
  })
  return data
}

export async function fetchSentimentStats() {
  const { data } = await withFallback(api, 'get', '/analysis/sentiment/stats')
  return data
}

export async function runTopics({ limit = 2000, use_bertopic = true } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/topics/run', {
    data: { limit, use_bertopic },
  })
  return data
}

export async function fetchWordCloud(top_k = 40) {
  const { data } = await withFallback(api, 'get', '/analysis/topics/words', {
    params: { top_k },
  })
  return data
}

export async function fetchAlerts(limit = 50) {
  const { data } = await withFallback(api, 'get', '/alerts', { params: { limit } })
  return data
}

export async function fetchTrends(days = 14) {
  const { data } = await withFallback(api, 'get', '/trends', { params: { days } })
  return data
}

export async function fetchReportSummary() {
  const { data } = await withFallback(api, 'get', '/reports/summary')
  return data
}
