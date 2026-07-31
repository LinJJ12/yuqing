<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Download, Upload } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import CollapsiblePanel from '../components/CollapsiblePanel.vue'
import { collectBilibili, deletePosts, fetchImports, uploadImport } from '../api/client'
import { formatDateTime } from '../lib/datetime'

const JOB_PAGE_SIZE = 10
const workTab = ref('collect')

const file = ref(null)
const topic = ref('')
const platform = ref('campus')
const uploading = ref(false)
const message = ref('')
const error = ref('')
const jobs = ref([])
const jobsPage = ref(1)

const jobStatusMap = {
  queued: '排队中',
  running: '运行中',
  succeeded: '成功',
  failed: '失败',
  pending: '等待中',
  done: '完成',
  completed: '完成',
  error: '失败',
  ok: '完成',
}

const jobsTotalPages = computed(() =>
  Math.max(1, Math.ceil((jobs.value?.length || 0) / JOB_PAGE_SIZE)),
)
const pagedJobs = computed(() => {
  const start = (jobsPage.value - 1) * JOB_PAGE_SIZE
  return (jobs.value || []).slice(start, start + JOB_PAGE_SIZE)
})
const jobsPageFrom = computed(() =>
  jobs.value.length ? (jobsPage.value - 1) * JOB_PAGE_SIZE + 1 : 0,
)
const jobsPageTo = computed(() =>
  Math.min(jobs.value.length, jobsPage.value * JOB_PAGE_SIZE),
)

function goJobsPage(page) {
  const next = Math.min(Math.max(1, page), jobsTotalPages.value)
  if (next === jobsPage.value) return
  jobsPage.value = next
}

watch(
  () => jobs.value.length,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / JOB_PAGE_SIZE))
    if (jobsPage.value > maxPage) jobsPage.value = maxPage
  },
)

async function refreshJobs() {
  const j = await fetchImports(100)
  if (j.ok) {
    jobs.value = Array.isArray(j.data) ? j.data : j.data?.items || []
    jobsPage.value = 1
  }
}

const biliKeyword = ref('')
const biliVideo = ref('')
const biliTopic = ref('')
const biliMaxVideos = ref(2)
const biliMaxComments = ref(50)
const collecting = ref(false)
const biliMessage = ref('')
const biliError = ref('')
const lastCollectedBvid = ref('')
const lastCollectStats = ref(null)
const showKeywordSearch = ref(false)
const filterTitles = ref(true)
const requireKeywordHit = ref(true)
const filterComments = ref(true)

const cleanTitle = ref('')
const cleaning = ref(false)
const cleanMessage = ref('')
const cleanError = ref('')

const platforms = [
  { value: 'campus', label: '样例/导入' },
  { value: 'xhs', label: '小红书' },
  { value: 'dy', label: '抖音' },
  { value: 'wb', label: '微博' },
  { value: 'bili', label: 'B站' },
]

function onFileChange(e) {
  file.value = e.target.files?.[0] || null
}

async function submit() {
  error.value = ''
  message.value = ''
  if (!file.value) {
    error.value = '请先选择数据文件（表格或数据包）'
    return
  }
  uploading.value = true
  try {
    const res = await uploadImport(file.value, {
      topic: topic.value.trim() || '文件导入',
      platform: platform.value,
    })
    if (!res.ok) {
      error.value = res.error?.message || '导入失败'
      return
    }
    const s = res.data.stats || {}
    message.value = `导入完成：接受 ${s.accepted ?? 0}，入库 ${s.inserted ?? 0}，重复 ${s.duplicates ?? 0}，拒绝 ${s.rejected ?? 0}`
    await refreshJobs()
  } catch (e) {
    error.value =
      e?.response?.data?.error?.message || e.message || '上传失败，请确认后端已启动'
  } finally {
    uploading.value = false
  }
}

async function submitBili() {
  biliError.value = ''
  biliMessage.value = ''
  lastCollectStats.value = null
  lastCollectedBvid.value = ''
  if (!biliKeyword.value.trim() && !biliVideo.value.trim()) {
    biliError.value = '请填写视频链接或视频号（推荐），或展开关键词搜索'
    return
  }
  collecting.value = true
  try {
    const res = await collectBilibili({
      keyword: biliKeyword.value.trim() || null,
      video: biliVideo.value.trim() || null,
      topic: biliTopic.value.trim() || null,
      max_videos: Number(biliMaxVideos.value) || 2,
      max_comments_per_video: Number(biliMaxComments.value) || 50,
      include_video_title: false,
      filter_titles: showKeywordSearch.value ? filterTitles.value : false,
      filter_comments: filterComments.value,
      require_keyword_hit: showKeywordSearch.value ? requireKeywordHit.value : false,
    })
    if (!res.ok) {
      biliError.value = res.error?.message || '采集失败'
      lastCollectStats.value = null
      return
    }
    const s = res.data.stats || {}
    const videos = s.videos || []
    const titles = videos.map((v) => v.title || v.bvid).filter(Boolean).slice(0, 3)
    const firstBvid = videos.find((v) => v.bvid)?.bvid
    lastCollectedBvid.value = firstBvid || ''
    lastCollectStats.value = s
    const notes = (s.notes || []).join('；')
    const noiseSum = Object.values(s.noise_filtered || {}).reduce((a, b) => a + Number(b || 0), 0)
    const rejectedN = (s.videos_rejected || []).length
    biliMessage.value =
      `采集完成：视频 ${videos.length}，评论入库 ${s.inserted ?? 0}` +
      (noiseSum || s.rejected ? `，去噪 ${noiseSum || s.rejected}` : '') +
      (rejectedN ? `，跳过视频 ${rejectedN}` : '') +
      (s.logged_in === false ? '，未登录 Cookie' : '') +
      (titles.length ? `；样例：${titles.join(' / ')}` : '') +
      (notes ? `。${notes}` : '')
    await refreshJobs()
  } catch (e) {
    biliError.value =
      e?.response?.data?.error?.message || e.message || '采集失败，请确认后端已启动'
  } finally {
    collecting.value = false
  }
}

async function previewClean() {
  cleanError.value = ''
  cleanMessage.value = ''
  const title = cleanTitle.value.trim()
  if (!title) {
    cleanError.value = '请填写要匹配的视频标题关键词'
    return
  }
  cleaning.value = true
  try {
    const res = await deletePosts({
      title_contains: title,
      platform: 'bili',
      dry_run: true,
    })
    if (!res.ok) {
      cleanError.value = res.error?.message || '预览失败'
      return
    }
    cleanMessage.value = `将匹配 ${res.data.matched ?? 0} 条`
  } catch (e) {
    cleanError.value = e.message || '预览失败'
  } finally {
    cleaning.value = false
  }
}

async function runClean() {
  cleanError.value = ''
  cleanMessage.value = ''
  const title = cleanTitle.value.trim()
  if (!title) {
    cleanError.value = '请填写要匹配的视频标题关键词'
    return
  }
  cleaning.value = true
  try {
    const res = await deletePosts({
      title_contains: title,
      platform: 'bili',
      dry_run: false,
    })
    if (!res.ok) {
      cleanError.value = res.error?.message || '清理失败'
      return
    }
    cleanMessage.value = `已删除 ${res.data.deleted ?? 0} 条（匹配 ${res.data.matched ?? 0}）`
    await refreshJobs()
  } catch (e) {
    cleanError.value = e.message || '清理失败'
  } finally {
    cleaning.value = false
  }
}

onMounted(async () => {
  try {
    await refreshJobs()
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  }
})
</script>

<template>
  <div class="page monitor-page">
    <PageHeader title="舆情监测" subtitle="采集 / 导入 / 清理 → 再到「入库」浏览">
      <template #actions>
        <RouterLink class="btn btn-secondary btn-sm" to="/inbox">查看入库</RouterLink>
      </template>
    </PageHeader>

    <section class="panel work-panel">
      <div class="ui-tabs">
        <div class="ui-tabs-nav" role="tablist">
          <button
            type="button"
            class="ui-tab"
            :class="{ active: workTab === 'collect' }"
            role="tab"
            @click="workTab = 'collect'"
          >
            视频采集
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: workTab === 'import' }"
            role="tab"
            @click="workTab = 'import'"
          >
            文件导入
          </button>
          <button
            type="button"
            class="ui-tab"
            :class="{ active: workTab === 'clean' }"
            role="tab"
            @click="workTab = 'clean'"
          >
            数据清理
          </button>
        </div>

        <div v-show="workTab === 'collect'" class="ui-tabs-body">
          <div class="form-grid compact-form work-form">
            <label class="field">
              视频号 / 链接
              <input
                v-model="biliVideo"
                class="input"
                placeholder="粘贴 B 站视频链接或视频号"
              />
            </label>
            <div class="num-row">
              <label class="field">
                话题（可选）
                <input v-model="biliTopic" class="input" placeholder="默认用视频标题" />
              </label>
              <label class="field">
                每视频评论
                <input
                  v-model.number="biliMaxComments"
                  class="input"
                  type="number"
                  min="1"
                  max="200"
                />
              </label>
            </div>
            <div class="more-opts">
              <button type="button" class="btn btn-ghost btn-sm" @click="showKeywordSearch = !showKeywordSearch">
                {{ showKeywordSearch ? '收起关键词搜索' : '展开关键词搜索' }}
              </button>
              <template v-if="showKeywordSearch">
                <label class="field">
                  关键词
                  <input v-model="biliKeyword" class="input" placeholder="无视频号时使用" />
                </label>
                <label class="field">
                  视频数
                  <input
                    v-model.number="biliMaxVideos"
                    class="input"
                    type="number"
                    min="1"
                    max="10"
                  />
                </label>
                <label class="check-row">
                  <input v-model="filterTitles" type="checkbox" />
                  过滤娱乐向标题（黑名单）
                </label>
                <label class="check-row">
                  <input v-model="requireKeywordHit" type="checkbox" />
                  标题须命中搜索词
                </label>
              </template>
              <p v-else class="hint gate-hint">
                当前为 BV 直采：标题黑名单 / 须命中搜索词仅在关键词搜索时生效。
              </p>
              <label class="check-row">
                <input v-model="filterComments" type="checkbox" />
                过滤空评 / 刷评
              </label>
            </div>
            <button type="button" class="btn btn-primary" :disabled="collecting" @click="submitBili">
              <Download :size="16" />
              {{ collecting ? '采集中…' : '开始采集并入库' }}
            </button>
          </div>
          <div v-if="biliMessage || lastCollectStats" class="collect-result">
            <p v-if="biliMessage" class="ok-text status-line">{{ biliMessage }}</p>
            <ul v-if="lastCollectStats" class="stats-chips">
              <li>入库 {{ lastCollectStats.inserted ?? 0 }}</li>
              <li v-if="lastCollectStats.logged_in != null">
                Cookie {{ lastCollectStats.logged_in ? '已登录' : '未配置' }}
              </li>
              <li v-if="(lastCollectStats.videos_rejected || []).length">
                跳过视频 {{ lastCollectStats.videos_rejected.length }}
              </li>
              <li v-if="lastCollectStats.sentiment_job_id">情感任务已排队</li>
            </ul>
            <details
              v-if="(lastCollectStats?.videos_rejected || []).length"
              class="rejected-fold"
            >
              <summary>查看跳过的视频（{{ lastCollectStats.videos_rejected.length }}）</summary>
              <ul>
                <li
                  v-for="(v, i) in lastCollectStats.videos_rejected.slice(0, 8)"
                  :key="i"
                >
                  {{ v.title || v.bvid || '—' }}
                  <span v-if="v.reason" class="muted"> · {{ v.reason }}</span>
                </li>
              </ul>
            </details>
            <div class="result-links">
              <RouterLink class="link-out" to="/inbox">查看入库 →</RouterLink>
              <RouterLink
                v-if="lastCollectedBvid"
                class="link-out"
                :to="{ path: '/reports', query: { bvid: lastCollectedBvid } }"
              >
                查看口碑 →
              </RouterLink>
              <RouterLink class="link-out" to="/sentiment">去情感页看进度 →</RouterLink>
            </div>
          </div>
          <p v-if="biliError" class="err status-line">{{ biliError }}</p>
        </div>

        <div v-show="workTab === 'import'" class="ui-tabs-body">
          <div class="form-grid compact-form work-form">
            <div class="num-row">
              <label class="field">
                平台
                <select v-model="platform" class="input">
                  <option v-for="p in platforms" :key="p.value" :value="p.value">
                    {{ p.label }}
                  </option>
                </select>
              </label>
              <label class="field">
                话题（可选）
                <input v-model="topic" class="input" placeholder="例如：产品口碑" />
              </label>
            </div>
            <label class="field">
              文件（表格 / 数据文件）
              <input
                class="file-input"
                type="file"
                accept=".json,.jsonl,.ndjson,.csv"
                @change="onFileChange"
              />
            </label>
            <div v-if="file" class="file-name">已选：{{ file.name }}</div>
            <button type="button" class="btn btn-primary" :disabled="uploading" @click="submit">
              <Upload :size="16" />
              {{ uploading ? '导入中…' : '开始导入' }}
            </button>
          </div>
          <p v-if="message" class="ok-text status-line">{{ message }}</p>
          <p v-if="error" class="err status-line">{{ error }}</p>
          <div v-if="message" class="result-links">
            <RouterLink class="link-out" to="/inbox">查看入库 →</RouterLink>
          </div>
        </div>

        <div v-show="workTab === 'clean'" class="ui-tabs-body">
          <p class="hint">按视频标题关键词删除误采数据。先预览再删除。</p>
          <div class="bvid-row">
            <input v-model="cleanTitle" class="input" placeholder="标题包含…" />
            <button type="button" class="btn btn-secondary btn-sm" :disabled="cleaning" @click="previewClean">
              预览
            </button>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="cleaning" @click="runClean">
              {{ cleaning ? '处理中…' : '删除匹配' }}
            </button>
          </div>
          <p v-if="cleanMessage" class="ok-text status-line">{{ cleanMessage }}</p>
          <p v-if="cleanError" class="err status-line">{{ cleanError }}</p>
        </div>
      </div>
    </section>

    <CollapsiblePanel
      v-if="jobs.length"
      title="最近任务"
      storage-key="yuqing.monitor.jobs"
      :default-open="false"
    >
      <template #badge>
        <span class="pill pill-default">{{ jobs.length }}</span>
      </template>
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 22%">时间</th>
            <th style="width: 36%">来源</th>
            <th style="width: 14%">平台</th>
            <th style="width: 14%">状态</th>
            <th style="width: 14%">入库</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in pagedJobs" :key="job.id">
            <td>{{ formatDateTime(job.created_at) }}</td>
            <td class="ellipsis">{{ job.filename }}</td>
            <td>{{ job.platform || '—' }}</td>
            <td><span class="pill pill-primary">{{ jobStatusMap[job.status] || job.status }}</span></td>
            <td>{{ job.stats?.inserted ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="jobs.length > JOB_PAGE_SIZE" class="pager">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="jobsPage <= 1"
          @click="goJobsPage(jobsPage - 1)"
        >
          上一页
        </button>
        <span class="pager-info">
          {{ jobsPageFrom }}–{{ jobsPageTo }} / {{ jobs.length }} · 第 {{ jobsPage }} / {{ jobsTotalPages }} 页
        </span>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="jobsPage >= jobsTotalPages"
          @click="goJobsPage(jobsPage + 1)"
        >
          下一页
        </button>
      </div>
    </CollapsiblePanel>
  </div>
</template>

<style scoped>
.work-panel {
  padding-top: 0.65rem;
}
.work-form {
  max-width: 40rem;
  margin-top: 0;
}
.compact-form {
  gap: 0.65rem;
}
.num-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}
.more-opts {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  align-items: flex-start;
}
.check-row {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: var(--text-secondary);
}
.bvid-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
  margin-top: 0.55rem;
}
.bvid-row .input {
  flex: 1;
  min-width: 10rem;
  max-width: 24rem;
}
.status-line {
  margin-top: 0.65rem;
}
.gate-hint {
  margin: 0.15rem 0;
  font-size: 0.78rem;
}
.collect-result {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.stats-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.stats-chips li {
  padding: 0.2rem 0.55rem;
  border-radius: 99px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.rejected-fold {
  font-size: 0.82rem;
  color: var(--text-secondary);
}
.rejected-fold ul {
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
}
.result-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  margin-top: 0.35rem;
}
.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-name {
  font-size: 0.82rem;
  color: var(--text-secondary);
}
</style>
