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

function shouldFallback(status, data) {
  if (!status) return true
  // 后端已返回统一错误体（如模型加载失败 503），勿再直连重试拖长时间
  if (data && typeof data === 'object' && data.ok === false) return false
  // 代理到错误旧进程时常 404；网关类错误也回退
  return status === 404 || status === 502 || status === 503 || status === 504 || data == null
}

async function withFallback(client, method, url, config = {}) {
  try {
    const res = await client.request({ method, url, ...config })
    if (shouldFallback(res.status, res.data) && res.status !== 200) {
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

export async function fetchPosts({
  topic,
  platform,
  limit = 50,
  offset = 0,
  order = 'fetched',
  label,
  bvid,
} = {}) {
  const { data } = await withFallback(api, 'get', '/posts', {
    params: { topic, platform, limit, offset, order, label, bvid: bvid || undefined },
  })
  return data
}

export async function fetchReviewPosts(limit = 40, { bvid } = {}) {
  const { data } = await withFallback(api, 'get', '/posts/review', {
    params: { limit, bvid: bvid || undefined },
  })
  return data
}

export async function overridePostSentiment(postId, { label, method = 'manual', confidence = 1 } = {}) {
  const { data } = await withFallback(api, 'patch', `/posts/${postId}/sentiment`, {
    data: { label, method, confidence },
  })
  return data
}

export async function llmReviewSentiment({ post_id, text, apply = true } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/sentiment/llm-review', {
    data: { post_id, text, apply },
  })
  return data
}

export async function fetchImports(limit = 20) {
  const { data } = await withFallback(api, 'get', '/imports', { params: { limit } })
  return data
}

export async function uploadImport(
  file,
  { topic = '文件导入', platform = 'campus' } = {},
) {
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

export async function runSentiment({ limit = 2000, only_pending = true, bvid } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/sentiment/run', {
    data: { limit, only_pending, bvid: bvid || null },
  })
  return data
}

export async function fetchSentimentStats({ bvid } = {}) {
  const { data } = await withFallback(api, 'get', '/analysis/sentiment/stats', {
    params: { bvid: bvid || undefined },
  })
  return data
}

export async function runTopics({ limit = 2000, use_bertopic = true, bvid } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/analysis/topics/run', {
    data: { limit, use_bertopic, bvid: bvid || null },
  })
  return data
}

export async function fetchWordCloud(top_k = 40, { bvid } = {}) {
  const { data } = await withFallback(api, 'get', '/analysis/topics/words', {
    params: { top_k, bvid: bvid || undefined },
  })
  return data
}

export async function fetchAlerts(limit = 50, { bvid } = {}) {
  const { data } = await withFallback(api, 'get', '/alerts', {
    params: { limit, bvid: bvid || undefined },
  })
  return data
}

export async function fetchTrends(
  days = 14,
  { use_prophet = true, prophet_horizon = 7, bvid } = {},
) {
  const { data } = await withFallback(api, 'get', '/trends', {
    params: { days, use_prophet, prophet_horizon, bvid: bvid || undefined },
  })
  return data
}

export async function fetchReportSummary() {
  const { data } = await withFallback(api, 'get', '/reports/summary')
  return data
}

export async function fetchVideoSummaries(limit = 50) {
  const { data } = await withFallback(api, 'get', '/reports/videos', {
    params: { limit },
  })
  return data
}

export async function fetchVideoReport(bvid, { with_ai = false } = {}) {
  if (with_ai) {
    const { data } = await withFallback(slowApi, 'post', '/reports/video', {
      data: { bvid, with_ai: true },
    })
    return data
  }
  const { data } = await withFallback(api, 'get', '/reports/video', {
    params: { bvid },
  })
  return data
}

export async function generateReportSummary({ with_ai = false } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/reports/summary', {
    data: { with_ai },
  })
  return data
}

function exportUrl(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  return `${DIRECT}${path}${qs ? `?${qs}` : ''}`
}

export function reportCsvUrl({ with_ai = false } = {}) {
  return exportUrl('/reports/export.csv', { with_ai })
}

export function reportPdfUrl({ with_ai = false } = {}) {
  return exportUrl('/reports/export.pdf', { with_ai })
}

export async function fetchAlertKeywords() {
  const { data } = await withFallback(api, 'get', '/settings/alert-keywords')
  return data
}

export async function saveAlertKeywords(keywords) {
  const { data } = await withFallback(api, 'put', '/settings/alert-keywords', {
    data: { keywords },
  })
  return data
}

export async function createAnalysisJob(payload) {
  const { data } = await withFallback(api, 'post', '/analysis-jobs', { data: payload })
  return data
}

export async function fetchAnalysisJobs(limit = 20) {
  const { data } = await withFallback(api, 'get', '/analysis-jobs', { params: { limit } })
  return data
}

export async function fetchAnalysisJob(jobId) {
  const { data } = await withFallback(api, 'get', `/analysis-jobs/${jobId}`)
  return data
}

export async function fetchAgentStatus() {
  const { data } = await withFallback(api, 'get', '/agent/status')
  return data
}

export async function agentChat(question, history = [], { bvid } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/agent/chat', {
    data: { question, history, bvid: bvid || null },
  })
  return data
}

export async function agentBrief({ bvid } = {}) {
  const { data } = await withFallback(slowApi, 'post', '/agent/brief', {
    data: { bvid: bvid || null },
  })
  return data
}

export async function deletePosts(payload) {
  const { data } = await withFallback(api, 'post', '/posts/delete', {
    data: payload,
  })
  return data
}

export async function collectBilibili(payload) {
  const { data } = await withFallback(slowApi, 'post', '/collect/bilibili', {
    data: payload,
  })
  return data
}
