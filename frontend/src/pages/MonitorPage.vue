<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Download, ExternalLink, Upload } from '@lucide/vue'
import { collectBilibili, fetchImports, fetchOverview, fetchPosts, uploadImport } from '../api/client'

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
const biliMaxComments = ref(30)
const collecting = ref(false)
const biliMessage = ref('')
const biliError = ref('')

const platforms = [
  { value: 'campus', label: '样例/导入' },
  { value: 'xhs', label: '小红书 (xhs)' },
  { value: 'dy', label: '抖音 (dy)' },
  { value: 'wb', label: '微博 (wb)' },
  { value: 'bili', label: 'B站 (bili)' },
]

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

function formatTime(post) {
  return post.fetched_at || post.published_at || '—'
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
    error.value = '请先选择 JSON / JSONL / CSV 文件'
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
    biliError.value = '请填写关键词或视频 BV/链接'
    return
  }
  collecting.value = true
  try {
    const res = await collectBilibili({
      keyword: biliKeyword.value.trim() || null,
      video: biliVideo.value.trim() || null,
      topic: biliTopic.value.trim() || null,
      max_videos: Number(biliMaxVideos.value) || 2,
      max_comments_per_video: Number(biliMaxComments.value) || 30,
      include_video_title: false,
    })
    if (!res.ok) {
      biliError.value = res.error?.message || 'B 站采集失败'
      return
    }
    const s = res.data.stats || {}
    const videos = s.videos || []
    const titles = videos.map((v) => v.title || v.bvid).filter(Boolean).slice(0, 3)
    biliMessage.value =
      `采集完成：视频 ${videos.length}，评论入库 ${s.inserted ?? 0}` +
      (titles.length ? `；样例：${titles.join(' / ')}` : '')
    listPlatform.value = 'bili'
    await refresh()
  } catch (e) {
    biliError.value =
      e?.response?.data?.error?.message || e.message || '采集失败，请确认后端已启动'
  } finally {
    collecting.value = false
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
    <div class="cols-2 collect-row">
      <section class="panel">
        <div class="panel-head">
          <h2>B 站评论采集</h2>
          <span class="pill pill-primary">内嵌</span>
        </div>
        <p class="hint">贴 BV 分析单视频口碑，或用关键词搜视频拉评论。采集后列表切到「B站」。</p>
        <div class="form-grid compact-form">
          <label class="field">
            关键词
            <input v-model="biliKeyword" class="input" placeholder="例如：数码评测 / 美食探店" />
          </label>
          <label class="field">
            BV / 链接（优先）
            <input
              v-model="biliVideo"
              class="input"
              placeholder="BV1… 或视频链接"
            />
          </label>
          <label class="field">
            话题（可选）
            <input v-model="biliTopic" class="input" placeholder="默认用关键词或视频标题" />
          </label>
          <div class="num-row">
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
          <button
            type="button"
            class="btn btn-primary"
            :disabled="collecting"
            @click="submitBili"
          >
            <Download :size="16" />
            {{ collecting ? '采集中…' : '开始采集并入库' }}
          </button>
        </div>
        <p v-if="biliMessage" class="ok-text" style="margin-top: 0.6rem">{{ biliMessage }}</p>
        <p v-if="biliError" class="err" style="margin-top: 0.6rem">{{ biliError }}</p>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>文件导入</h2>
          <span class="pill pill-default">JSON / CSV</span>
        </div>
        <p class="hint">样例 JSON 或 MediaCrawler 转换结果均可导入。</p>
        <div class="form-grid compact-form">
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
          <label class="field">
            文件
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
        <p v-if="message" class="ok-text" style="margin-top: 0.6rem">{{ message }}</p>
        <p v-if="error" class="err" style="margin-top: 0.6rem">{{ error }}</p>
      </section>
    </div>

    <section v-if="jobs.length" class="panel jobs-panel">
      <div class="panel-head">
        <h3>最近任务</h3>
        <span class="pill pill-default">{{ jobs.length }}</span>
      </div>
      <div class="jobs-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>来源</th>
              <th>平台</th>
              <th>状态</th>
              <th>入库</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobs.slice(0, 5)" :key="job.id">
              <td>{{ job.created_at }}</td>
              <td class="ellipsis">{{ job.filename }}</td>
              <td>{{ job.platform || '—' }}</td>
              <td>
                <span class="pill pill-primary">{{ job.status }}</span>
              </td>
              <td>{{ job.stats?.inserted ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel list-panel">
      <div class="panel-head">
        <h2>入库结果</h2>
        <span class="pill pill-default">当前 {{ posts.length }} / 共 {{ total }}</span>
      </div>
      <p class="hint">按入库时间排列。列表在框内滚动，上方采集区始终可见。</p>
      <div class="filter-row">
        <button
          v-for="opt in filterOptions"
          :key="opt.value"
          type="button"
          class="btn"
          :class="listPlatform === opt.value ? 'btn-primary' : 'btn-ghost'"
          @click="listPlatform = opt.value"
        >
          {{ opt.label }}
          <span class="pill pill-default">{{ opt.count }}</span>
        </button>
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
      <div v-if="posts.length" class="post-list post-scroll">
        <article v-for="post in posts" :key="post.id" class="post-item">
          <header class="post-meta">
            <b>{{ post.topic || '未分类' }}</b>
            <span class="pill pill-default">{{ platformLabel(post.platform) }}</span>
            <span class="pill pill-default">{{ post.sentiment_label || '未分析' }}</span>
            <em>{{ post.author || '匿名' }}</em>
            <em>{{ formatTime(post) }}</em>
          </header>
          <p v-if="videoTitle(post)" class="post-sub">来源视频：{{ videoTitle(post) }}</p>
          <p>{{ post.text }}</p>
          <div v-if="post.source_url" class="post-actions">
            <a class="link-out" :href="post.source_url" target="_blank" rel="noopener noreferrer">
              <ExternalLink :size="14" />
              打开原帖
            </a>
          </div>
        </article>
      </div>
      <p v-else class="hint">当前筛选下暂无帖子。可先在上方采集，或切换筛选。</p>
    </section>
  </div>
</template>

<style scoped>
.collect-row {
  align-items: stretch;
  margin-bottom: 0;
}
.compact-form {
  gap: 0.65rem;
}
.num-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}
.jobs-panel {
  padding-top: 0.85rem;
  padding-bottom: 0.85rem;
}
.jobs-scroll {
  max-height: 9.5rem;
  overflow: auto;
}
.ellipsis {
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.list-panel .hint {
  margin-bottom: 0.35rem;
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin: 0.5rem 0 0.75rem;
}
.filter-row .btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.field-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  font-size: 0.85rem;
}
.field-inline .input {
  width: 5.5rem;
}
.post-sub {
  margin: 0 0 0.35rem;
  font-size: 0.8rem;
  color: var(--text-tertiary);
}
.post-actions {
  margin-top: 0.45rem;
}
.link-out {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
}
.link-out:hover {
  text-decoration: underline;
}
.post-scroll {
  max-height: min(52vh, 28rem);
  overflow: auto;
  padding-right: 0.25rem;
  border-top: 1px solid var(--bg-tertiary);
  border-radius: 0 0 12px 12px;
}
@media (max-width: 900px) {
  .post-scroll {
    max-height: 40vh;
  }
}
</style>
