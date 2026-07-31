<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ExternalLink, Pencil, Plus, RefreshCw, Search, Trash2, X } from '@lucide/vue'
import {
  createPost,
  deletePost,
  deletePostsByIds,
  fetchOverview,
  fetchPosts,
  overridePostSentiment,
  updatePost,
} from '../api/client'
import { formatDateTime } from '../lib/datetime'

const PAGE_SIZE = 10

const posts = ref([])
const total = ref(0)
const platformStats = ref([])
const listPlatform = ref('all')
const listPage = ref(1)
const searchQ = ref('')
const searchInput = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const message = ref('')
const sentimentBusyId = ref(null)
const selected = ref(new Set())
const editorOpen = ref(false)
const editorMode = ref('create') // create | edit
const editingId = ref(null)
const form = ref(emptyForm())

const platforms = [
  { value: 'campus', label: '样例/导入' },
  { value: 'bili', label: 'B站' },
  { value: 'xhs', label: '小红书' },
  { value: 'dy', label: '抖音' },
  { value: 'wb', label: '微博' },
]

const sentimentOptions = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中性' },
  { value: 'negative', label: '负面' },
  { value: 'uncertain', label: '不确定' },
]

function emptyForm() {
  return {
    text: '',
    platform: 'campus',
    topic: '',
    author: '',
    source_url: '',
    bvid: '',
    video_title: '',
    sentiment_label: '',
  }
}

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

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const pageFrom = computed(() => {
  if (!total.value) return 0
  return (listPage.value - 1) * PAGE_SIZE + 1
})
const pageTo = computed(() => Math.min(total.value, listPage.value * PAGE_SIZE))
const selectedCount = computed(() => selected.value.size)
const allSelected = computed(
  () => posts.value.length > 0 && posts.value.every((p) => selected.value.has(p.id)),
)

function platformLabel(code) {
  const hit = platforms.find((p) => p.value === code)
  if (hit) return hit.label
  return code || '—'
}

function videoTitle(post) {
  return post?.raw?.extra?.video_title || post?.raw?.title || ''
}

function videoBvid(post) {
  return post?.raw?.extra?.bvid || ''
}

function formatTime(post) {
  return formatDateTime(post.fetched_at || post.published_at)
}

function toggleSelect(id) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleSelectAll() {
  if (allSelected.value) {
    selected.value = new Set()
    return
  }
  selected.value = new Set(posts.value.map((p) => p.id))
}

function openCreate() {
  editorMode.value = 'create'
  editingId.value = null
  form.value = emptyForm()
  if (listPlatform.value !== 'all') form.value.platform = listPlatform.value
  editorOpen.value = true
  error.value = ''
}

function openEdit(post) {
  editorMode.value = 'edit'
  editingId.value = post.id
  form.value = {
    text: post.text || '',
    platform: post.platform || 'campus',
    topic: post.topic || '',
    author: post.author || '',
    source_url: post.source_url || '',
    bvid: videoBvid(post),
    video_title: videoTitle(post),
    sentiment_label: post.sentiment_label || '',
  }
  editorOpen.value = true
  error.value = ''
}

function closeEditor() {
  if (saving.value) return
  editorOpen.value = false
}

async function submitEditor() {
  const payload = {
    text: form.value.text.trim(),
    platform: form.value.platform,
    topic: form.value.topic.trim() || null,
    author: form.value.author.trim(),
    source_url: form.value.source_url.trim() || null,
    bvid: form.value.bvid.trim() || null,
    video_title: form.value.video_title.trim() || null,
  }
  if (!payload.text) {
    error.value = '正文不能为空'
    return
  }
  saving.value = true
  error.value = ''
  try {
    if (editorMode.value === 'create') {
      if (form.value.sentiment_label) payload.sentiment_label = form.value.sentiment_label
      const res = await createPost(payload)
      if (!res.ok) {
        error.value = res.error?.message || '新增失败'
        return
      }
      message.value = `已新增 #${res.data.id}`
    } else {
      const res = await updatePost(editingId.value, {
        ...payload,
        clear_topic: !payload.topic,
        clear_source_url: !payload.source_url,
      })
      if (!res.ok) {
        error.value = res.error?.message || '保存失败'
        return
      }
      message.value = `已更新 #${editingId.value}`
    }
    editorOpen.value = false
    await refresh()
  } catch (e) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDeleteOne(post) {
  if (!confirm(`确定删除帖子 #${post.id}？\n${(post.text || '').slice(0, 60)}`)) return
  error.value = ''
  try {
    const res = await deletePost(post.id)
    if (!res.ok) {
      error.value = res.error?.message || '删除失败'
      return
    }
    message.value = `已删除 #${post.id}`
    selected.value.delete(post.id)
    selected.value = new Set(selected.value)
    await refresh()
  } catch (e) {
    error.value = e.message || '删除失败'
  }
}

async function onDeleteSelected() {
  const ids = [...selected.value]
  if (!ids.length) return
  if (!confirm(`确定删除选中的 ${ids.length} 条帖子？`)) return
  error.value = ''
  try {
    const res = await deletePostsByIds(ids)
    if (!res.ok) {
      error.value = res.error?.message || '批量删除失败'
      return
    }
    message.value = `已删除 ${res.data.deleted} 条`
    selected.value = new Set()
    await refresh()
  } catch (e) {
    error.value = e.message || '批量删除失败'
  }
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
  loading.value = true
  error.value = ''
  try {
    const params = {
      limit: PAGE_SIZE,
      offset: (listPage.value - 1) * PAGE_SIZE,
      order: 'fetched',
      q: searchQ.value.trim() || undefined,
    }
    if (listPlatform.value && listPlatform.value !== 'all') {
      params.platform = listPlatform.value
    }
    const [p, o] = await Promise.all([fetchPosts(params), fetchOverview()])
    if (p.ok) {
      posts.value = p.data.items
      total.value = p.data.total
      const maxPage = Math.max(1, Math.ceil((p.data.total || 0) / PAGE_SIZE))
      if (listPage.value > maxPage) {
        listPage.value = maxPage
        if (p.data.total > 0) {
          await refresh()
          return
        }
      }
      // 去掉不在当前页的勾选
      const pageIds = new Set(posts.value.map((x) => x.id))
      selected.value = new Set([...selected.value].filter((id) => pageIds.has(id)))
    }
    if (o.ok) platformStats.value = o.data.by_platform || []
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

function applySearch() {
  searchQ.value = searchInput.value.trim()
  listPage.value = 1
  refresh().catch(() => {})
}

function goPage(page) {
  const next = Math.min(Math.max(1, page), totalPages.value)
  if (next === listPage.value) return
  listPage.value = next
  refresh().catch(() => {})
}

watch(listPlatform, () => {
  listPage.value = 1
  selected.value = new Set()
  refresh().catch(() => {})
})

onMounted(async () => {
  try {
    const o = await fetchOverview()
    if (o.ok) {
      platformStats.value = o.data.by_platform || []
      const biliCount = platformStats.value.find((x) => x.platform === 'bili')?.count || 0
      const next = biliCount > 0 ? 'bili' : 'all'
      if (listPlatform.value === next) await refresh()
      else listPlatform.value = next
    } else {
      await refresh()
    }
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  }
})
</script>

<template>
  <div class="page inbox-page">
    <p v-if="message" class="ok-text status-line">{{ message }}</p>
    <p v-if="error" class="err status-line">{{ error }}</p>

    <section class="panel list-panel">
      <div class="toolbar">
        <div class="toolbar-left">
          <h3 class="list-title">入库结果</h3>
          <span class="pill pill-default">
            {{ total ? `${pageFrom}–${pageTo} / ${total}` : `0 / ${total}` }}
          </span>
          <button
            v-if="selectedCount"
            type="button"
            class="btn btn-ghost btn-sm danger-btn"
            @click="onDeleteSelected"
          >
            <Trash2 :size="14" />
            删除选中 {{ selectedCount }}
          </button>
        </div>
        <div class="toolbar-right">
          <button type="button" class="btn btn-primary btn-sm" @click="openCreate">
            <Plus :size="14" />
            新增
          </button>
          <RouterLink class="btn btn-secondary btn-sm" to="/monitor">去采集</RouterLink>
          <button type="button" class="btn btn-ghost btn-sm" :disabled="loading" @click="refresh">
            <RefreshCw :size="14" />
            刷新
          </button>
          <form class="search-box" @submit.prevent="applySearch">
            <Search :size="14" class="search-icon" />
            <input
              v-model="searchInput"
              class="input search-input"
              placeholder="搜索正文 / 话题 / 作者"
            />
            <button type="submit" class="btn btn-secondary btn-sm">查询</button>
          </form>
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
        </div>
      </div>

      <div v-if="posts.length" class="table-wrap">
        <table class="data-table posts-table">
          <thead>
            <tr>
              <th style="width: 3rem">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :indeterminate="selectedCount > 0 && !allSelected"
                  @change="toggleSelectAll"
                />
              </th>
              <th style="width: 8%">平台</th>
              <th style="width: 10%">话题</th>
              <th style="width: 32%">内容</th>
              <th style="width: 11%">情感</th>
              <th style="width: 12%">时间</th>
              <th style="width: 18%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="post in posts" :key="post.id">
              <td>
                <input
                  type="checkbox"
                  :checked="selected.has(post.id)"
                  @change="toggleSelect(post.id)"
                />
              </td>
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
                  <button type="button" class="link-out" @click="openEdit(post)">
                    <Pencil :size="13" />
                    编辑
                  </button>
                  <button type="button" class="link-out danger" @click="onDeleteOne(post)">
                    <Trash2 :size="13" />
                    删除
                  </button>
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
      <p v-else class="hint">
        {{
          loading
            ? '加载中…'
            : '当前筛选下暂无帖子。可点「新增」，或到「监测」采集/导入。'
        }}
      </p>

      <div v-if="total > PAGE_SIZE" class="pager">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="listPage <= 1"
          @click="goPage(listPage - 1)"
        >
          上一页
        </button>
        <span class="pager-info">第 {{ listPage }} / {{ totalPages }} 页</span>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="listPage >= totalPages"
          @click="goPage(listPage + 1)"
        >
          下一页
        </button>
      </div>
    </section>

    <div v-if="editorOpen" class="modal-mask" @click.self="closeEditor">
      <section class="modal-card panel">
        <div class="panel-head">
          <h3>{{ editorMode === 'create' ? '新增帖子' : `编辑 #${editingId}` }}</h3>
          <button type="button" class="btn btn-ghost btn-sm" :disabled="saving" @click="closeEditor">
            <X :size="16" />
          </button>
        </div>
        <div class="form-grid">
          <label class="field">
            平台
            <select v-model="form.platform" class="input">
              <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </label>
          <label class="field">
            话题
            <input v-model="form.topic" class="input" placeholder="可选" />
          </label>
          <label class="field">
            作者
            <input v-model="form.author" class="input" placeholder="可选" />
          </label>
          <label v-if="editorMode === 'create'" class="field">
            情感（可选）
            <select v-model="form.sentiment_label" class="input">
              <option value="">稍后分析</option>
              <option v-for="opt in sentimentOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </label>
          <label class="field span-2">
            正文 <span class="req">*</span>
            <textarea v-model="form.text" class="textarea" rows="4" placeholder="评论/帖子正文" />
          </label>
          <label class="field">
            视频 BV
            <input v-model="form.bvid" class="input" placeholder="可选，如 BV1…" />
          </label>
          <label class="field">
            视频标题
            <input v-model="form.video_title" class="input" placeholder="可选" />
          </label>
          <label class="field span-2">
            原帖链接
            <input v-model="form.source_url" class="input" placeholder="https://…" />
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" :disabled="saving" @click="closeEditor">
            取消
          </button>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="submitEditor">
            {{ saving ? '保存中…' : editorMode === 'create' ? '创建' : '保存' }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.status-line {
  margin: 0 0 0.65rem;
}
.list-title {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 650;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  align-items: center;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
}
.search-box {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  position: relative;
}
.search-icon {
  position: absolute;
  left: 0.55rem;
  color: var(--text-tertiary);
  pointer-events: none;
}
.search-input {
  width: 14rem;
  padding-left: 1.85rem;
  min-height: 2rem;
  font-size: 0.8125rem;
}
.danger-btn {
  color: var(--color-destructive);
}
.table-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
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
  min-width: 0;
  width: 100%;
  font-size: 0.8rem;
  min-height: 2rem;
  padding: 0.2rem 0.4rem;
}
.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
}
.link-out {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  border: none;
  background: none;
  padding: 0;
  color: var(--color-primary);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
  text-decoration: none;
}
.link-out:hover {
  text-decoration: underline;
}
.link-out.danger {
  color: var(--color-destructive);
}
.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(15, 23, 42, 0.35);
  display: grid;
  place-items: center;
  padding: 1rem;
}
.modal-card {
  width: min(36rem, 100%);
  max-height: min(90vh, 40rem);
  overflow: auto;
  margin: 0;
  box-shadow: var(--shadow-md);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.field.span-2 {
  grid-column: 1 / -1;
}
.req {
  color: var(--color-destructive);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .field.span-2 {
    grid-column: auto;
  }
  .search-input {
    width: 10rem;
  }
}
</style>
