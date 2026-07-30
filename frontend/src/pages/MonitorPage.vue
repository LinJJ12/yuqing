<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Download, ExternalLink, Upload } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import { collectBilibili, deletePosts, fetchImports, fetchOverview, fetchPosts, overridePostSentiment, uploadImport } from '../api/client'

const workTab = ref('collect')

const file = ref(null)
const topic = ref('')
const platform = ref('campus')
const uploading = ref(false)
const message = ref('')
const error = ref('')
const posts = ref([])
const total = ref(0)
const jobs = ref([])
const platformStats = ref([])

const listPlatform = ref('all')
const listLimit = ref(50)

const biliKeyword = ref('')
const biliVideo = ref('')
const biliTopic = ref('')
const biliMaxVideos = ref(2)
const biliMaxComments = ref(50)
const collecting = ref(false)
const biliMessage = ref('')
const biliError = ref('')
const lastCollectedBvid = ref('')
const showKeywordSearch = ref(false)
const filterTitles = ref(true)
const filterComments = ref(true)

const cleanTitle = ref('封校疑云')
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

const sentimentOptions = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中性' },
  { value: 'negative', label: '负面' },
  { value: 'uncertain', label: '不确定' },
]

const sentimentBusyId = ref(null)

const filterOptions = computed(() => {
  const map = Object.fromEntries(platformStats.value.map((x) => [x.platform, x.count]))
  return [
    { value: 'all', label: '全部', count: platformStats.value.reduce((s, x) => s + x.count, 0) },
    { value: 'bili', label: 'B站', count: map.bili || 0 },
    { value: 'campus', label: '样例/导入', count: map.campus || 0 },
    { value: 'xhs', label: '小红书', count: map.xhs || 0 },
    { value: 'dy', label: '抖音', count: map.dy || 0 },
    { value: 'wb', label: '微博', count: map.wb || 0 },
  ].filter((x) => x.value === 'all' || x.count > 0)
})

function platformLabel(code) {
  const hit = platforms.find((p) => p.value === code)
  if (hit) return hit.label
  if (code === 'bili') return 'B站'
  return code || '—'
}

function videoTitle(post) {
  return post?.raw?.extra?.video_title || post?.raw?.title || ''
}

function videoBvid(post) {
  return post?.raw?.extra?.bvid || ''
}

function formatTime(post) {
  return post.fetched_at || post.published_at || '—'
}

async function onSentimentOverride(post, label) {
  if (!label || (label === post.sentiment_label && post.sentiment_method === 'manual')) return
  sentimentBusyId.value = post.id
  error.value = ''
  try {
    const res = await overridePostSentiment(post.id, { label, method: 'manual' })
    if (!res.ok) {
      error.value = res.error?.message || '改判失败'
      return
    }
    const idx = posts.value.findIndex((p) => p.id === post.id)
    if (idx >= 0) posts.value[idx] = res.data
    message.value = `已改判 #${post.id}`
  } catch (e) {
    error.value = e.message || '改判失败'
  } finally {
    sentimentBusyId.value = null
  }
}

async function refresh() {
  const params = {
    limit: Number(listLimit.value) || 50,
    order: 'fetched',
  }
  if (listPlatform.value && listPlatform.value !== 'all') {
    params.platform = listPlatform.value
  }
  const [p, j, o] = await Promise.all([
    fetchPosts(params),
    fetchImports(10),
    fetchOverview(),
  ])
  if (p.ok) {
    posts.value = p.data.items
    total.value = p.data.total
  }
  if (j.ok) jobs.value = j.data
  if (o.ok) platformStats.value = o.data.by_platform || []
}

watch(listPlatform, () => {
  refresh().catch(() => {})
})

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
    listPlatform.value = platform.value
    await refresh()
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
      filter_titles: filterTitles.value,
      filter_comments: filterComments.value,
      require_keyword_hit: filterTitles.value,
    })
    if (!res.ok) {
      biliError.value = res.error?.message || 'B 站采集失败'
      return
    }
    const s = res.data.stats || {}
    const videos = s.videos || []
    const titles = videos.map((v) => v.title || v.bvid).filter(Boolean).slice(0, 3)
    const firstBvid = videos.find((v) => v.bvid)?.bvid
    lastCollectedBvid.value = firstBvid || ''
    const notes = (s.notes || []).join('；')
    biliMessage.value =
      `采集完成：视频 ${videos.length}，评论入库 ${s.inserted ?? 0}` +
      (s.rejected ? `，去噪 ${s.rejected}` : '') +
      (titles.length ? `；样例：${titles.join(' / ')}` : '') +
      (notes ? `。${notes}` : '')
    listPlatform.value = 'bili'
    await refresh()
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
    cleanMessage.value = `预览：将匹配 ${res.data.matched ?? 0} 条（标题含「${title}」）`
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
  if (!window.confirm(`确认删除标题包含「${title}」的 B 站评论？此操作不可撤销。`)) {
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
    await refresh()
  } catch (e) {
    cleanError.value = e.message || '清理失败'
  } finally {
    cleaning.value = false
  }
}

onMounted(async () => {
  try {
    // 默认优先看 B 站；若还没有则看全部
    const o = await fetchOverview()
    if (o.ok) {
      platformStats.value = o.data.by_platform || []
      const biliCount = platformStats.value.find((x) => x.platform === 'bili')?.count || 0
      listPlatform.value = biliCount > 0 ? 'bili' : 'all'
    }
    await refresh()
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  }
})
</script>

<template>
  <div class="page monitor-page">
    <PageHeader title="舆情监测" subtitle="采集入库 → 浏览评论 → 跳转口碑报告" />

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
              </template>
              <label class="check-row">
                <input v-model="filterTitles" type="checkbox" />
                过滤娱乐向标题
              </label>
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
          <p v-if="biliMessage" class="ok-text status-line">
            {{ biliMessage }}
            <RouterLink
              v-if="lastCollectedBvid"
              class="link-out"
              :to="{ path: '/reports', query: { bvid: lastCollectedBvid } }"
            >
              查看口碑 →
            </RouterLink>
          </p>
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

    <section v-if="jobs.length" class="panel jobs-panel">
      <div class="panel-head">
        <h3>最近任务</h3>
        <span class="pill pill-default">{{ jobs.length }}</span>
      </div>
      <div class="jobs-scroll">
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
            <tr v-for="job in jobs.slice(0, 5)" :key="job.id">
              <td>{{ job.created_at }}</td>
              <td class="ellipsis">{{ job.filename }}</td>
              <td>{{ job.platform || '—' }}</td>
              <td><span class="pill pill-primary">{{ jobStatusMap[job.status] || job.status }}</span></td>
              <td>{{ job.stats?.inserted ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel list-panel">
      <div class="toolbar">
        <div class="toolbar-left">
          <h3 class="list-title">入库结果</h3>
          <span class="pill pill-default">{{ posts.length }} / {{ total }}</span>
        </div>
        <div class="toolbar-right">
          <div class="segmented">
            <button
              v-for="opt in filterOptions"
              :key="opt.value"
              type="button"
              :class="{ active: listPlatform === opt.value }"
              @click="listPlatform = opt.value"
            >
              {{ opt.label }} {{ opt.count }}
            </button>
          </div>
          <label class="field field-inline">
            条数
            <select v-model.number="listLimit" class="input" @change="refresh">
              <option :value="30">30</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
            </select>
          </label>
        </div>
      </div>

      <div v-if="posts.length" class="table-scroll">
        <table class="data-table posts-table">
          <thead>
            <tr>
              <th style="width: 10%">平台</th>
              <th style="width: 12%">话题</th>
              <th style="width: 34%">内容</th>
              <th style="width: 12%">情感</th>
              <th style="width: 12%">时间</th>
              <th style="width: 20%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="post in posts" :key="post.id">
              <td>{{ platformLabel(post.platform) }}</td>
              <td class="ellipsis" :title="post.topic || ''">{{ post.topic || '未分类' }}</td>
              <td>
                <div class="cell-text" :title="post.text">{{ post.text }}</div>
                <div v-if="videoTitle(post)" class="cell-sub">{{ videoTitle(post) }}</div>
              </td>
              <td>
                <select
                  class="input sentiment-select"
                  :value="post.sentiment_label || ''"
                  :disabled="sentimentBusyId === post.id"
                  @change="onSentimentOverride(post, $event.target.value)"
                >
                  <option value="" disabled>未分析</option>
                  <option v-for="opt in sentimentOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </td>
              <td class="ellipsis">{{ formatTime(post) }}</td>
              <td>
                <div class="row-actions">
                  <RouterLink
                    v-if="videoBvid(post)"
                    class="link-out"
                    :to="{ path: '/reports', query: { bvid: videoBvid(post) } }"
                  >
                    口碑
                  </RouterLink>
                  <a
                    v-if="post.source_url"
                    class="link-out"
                    :href="post.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink :size="13" />
                    原帖
                  </a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">当前筛选下暂无帖子。可先在上方采集，或切换筛选。</p>
    </section>
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
.jobs-scroll {
  max-height: 9rem;
  overflow: auto;
}
.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.list-title {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 650;
}
.field-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  margin: 0;
}
.field-inline .input {
  width: 5rem;
}
.table-scroll {
  max-height: min(58vh, 34rem);
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.posts-table {
  table-layout: fixed;
}
.posts-table th,
.posts-table td {
  padding: 0.55rem 0.65rem;
  white-space: normal;
  vertical-align: top;
}
.cell-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.45;
  color: var(--text-primary);
}
.cell-sub {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sentiment-select {
  width: 100%;
  min-height: 1.9rem;
  padding: 0.15rem 0.35rem;
  font-size: 0.8rem;
}
.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
}
.link-out {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
}
.link-out:hover {
  text-decoration: underline;
}
@media (max-width: 900px) {
  .num-row {
    grid-template-columns: 1fr;
  }
  .table-scroll {
    max-height: 45vh;
  }
}
</style>
