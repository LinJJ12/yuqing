<script setup>
import { onMounted, ref } from 'vue'
import { Download, Upload } from '@lucide/vue'
import { collectBilibili, fetchImports, fetchPosts, uploadImport } from '../api/client'

const file = ref(null)
const topic = ref('')
const platform = ref('campus')
const uploading = ref(false)
const message = ref('')
const error = ref('')
const posts = ref([])
const total = ref(0)
const jobs = ref([])

const biliKeyword = ref('校园食堂')
const biliVideo = ref('')
const biliTopic = ref('')
const biliMaxVideos = ref(2)
const biliMaxComments = ref(30)
const collecting = ref(false)
const biliMessage = ref('')
const biliError = ref('')

const platforms = [
  { value: 'campus', label: '校园/通用' },
  { value: 'xhs', label: '小红书 (xhs)' },
  { value: 'dy', label: '抖音 (dy)' },
  { value: 'wb', label: '微博 (wb)' },
  { value: 'bili', label: 'B站 (bili)' },
]

async function refresh() {
  const [p, j] = await Promise.all([fetchPosts({ limit: 30 }), fetchImports(10)])
  if (p.ok) {
    posts.value = p.data.items
    total.value = p.data.total
  }
  if (j.ok) jobs.value = j.data
}

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
    await refresh()
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  }
})
</script>

<template>
  <div class="page">
    <section class="panel">
      <div class="panel-head">
        <h2>B 站评论采集</h2>
        <span class="pill pill-primary">内嵌</span>
      </div>
      <p class="hint">
        按关键词搜索公开视频并拉取评论入库，或直接填 BV 号/链接。仅演示用，请控制条数。
        未登录时平台常只返回少量一级评论（会附带二级回复）；若条数偏少，可在
        <code>backend/.env</code> 配置 <code>BILIBILI_SESSDATA</code> 后重启后端。
      </p>
      <div class="form-grid">
        <label class="field">
          关键词（搜索视频）
          <input v-model="biliKeyword" class="input" placeholder="例如：校园食堂" />
        </label>
        <label class="field">
          视频 BV / 链接（可选，优先）
          <input
            v-model="biliVideo"
            class="input"
            placeholder="BV1… 或 https://www.bilibili.com/video/BV…"
          />
        </label>
        <label class="field">
          话题（可选）
          <input v-model="biliTopic" class="input" placeholder="默认用关键词" />
        </label>
        <label class="field">
          最多视频数
          <input v-model.number="biliMaxVideos" class="input" type="number" min="1" max="10" />
        </label>
        <label class="field">
          每视频评论数
          <input v-model.number="biliMaxComments" class="input" type="number" min="1" max="200" />
        </label>
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
      <p v-if="biliMessage" class="ok-text" style="margin-top: 0.75rem">{{ biliMessage }}</p>
      <p v-if="biliError" class="err" style="margin-top: 0.75rem">{{ biliError }}</p>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>导入数据</h2>
        <span class="pill pill-default">JSON / CSV</span>
      </div>
      <p class="hint">
        支持 JSON / JSONL / CSV。校园样例或 MediaCrawler 转换结果均可上传；真实采集步骤见
        <code>docs/real-data-collection.md</code>。
      </p>
      <div class="form-grid">
        <label class="field">
          平台
          <select v-model="platform" class="input">
            <option v-for="p in platforms" :key="p.value" :value="p.value">
              {{ p.label }}
            </option>
          </select>
        </label>
        <label class="field">
          话题（可选，不填则按正文关键词自动归类）
          <input v-model="topic" class="input" placeholder="例如：食堂" />
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
      <p v-if="message" class="ok-text" style="margin-top: 0.75rem">{{ message }}</p>
      <p v-if="error" class="err" style="margin-top: 0.75rem">{{ error }}</p>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>最近导入任务</h3>
      </div>
      <table v-if="jobs.length" class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>文件</th>
            <th>平台</th>
            <th>状态</th>
            <th>入库</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td>{{ job.created_at }}</td>
            <td>{{ job.filename }}</td>
            <td>{{ job.platform || '—' }}</td>
            <td>
              <span class="pill pill-primary">{{ job.status }}</span>
            </td>
            <td>{{ job.stats?.inserted ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">暂无导入记录</p>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>帖子列表</h3>
        <span class="pill pill-default">共 {{ total }}</span>
      </div>
      <div v-if="posts.length" class="post-list">
        <article v-for="post in posts" :key="post.id" class="post-item">
          <header class="post-meta">
            <b>{{ post.topic }}</b>
            <span class="pill pill-default">{{ post.platform || '—' }}</span>
            <span class="pill pill-default">{{ post.sentiment_label || '—' }}</span>
            <em>{{ post.author || '匿名' }}</em>
          </header>
          <p>{{ post.text }}</p>
        </article>
      </div>
      <p v-else class="hint">暂无帖子</p>
    </section>
  </div>
</template>
