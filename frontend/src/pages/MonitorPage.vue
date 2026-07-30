<script setup>
import { onMounted, ref } from 'vue'
import { Upload } from '@lucide/vue'
import { fetchImports, fetchPosts, uploadImport } from '../api/client'

const file = ref(null)
const topic = ref('')
const platform = ref('campus')
const uploading = ref(false)
const message = ref('')
const error = ref('')
const posts = ref([])
const total = ref(0)
const jobs = ref([])

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
