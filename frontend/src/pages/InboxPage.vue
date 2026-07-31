<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ExternalLink, RefreshCw } from '@lucide/vue'
import PageHeader from '../components/PageHeader.vue'
import {
  fetchOverview,
  fetchPosts,
  overridePostSentiment,
} from '../api/client'
import { formatDateTime } from '../lib/datetime'

const PAGE_SIZE = 20

const posts = ref([])
const total = ref(0)
const platformStats = ref([])
const listPlatform = ref('all')
const listPage = ref(1)
const loading = ref(false)
const error = ref('')
const message = ref('')
const sentimentBusyId = ref(null)

const platforms = [
  { value: 'campus', label: '样例/导入' },
  { value: 'xhs', label: '小红书' },
  { value: 'dy', label: '抖音' },
  { value: 'wb', label: '微博' },
  { value: 'bili', label: 'B站' },
]

const sentimentOptions = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中性' },
  { value: 'negative', label: '负面' },
  { value: 'uncertain', label: '不确定' },
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

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const pageFrom = computed(() => {
  if (!total.value) return 0
  return (listPage.value - 1) * PAGE_SIZE + 1
})
const pageTo = computed(() => Math.min(total.value, listPage.value * PAGE_SIZE))

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
  return formatDateTime(post.fetched_at || post.published_at)
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
    }
    if (o.ok) platformStats.value = o.data.by_platform || []
  } catch (e) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
}

function goPage(page) {
  const next = Math.min(Math.max(1, page), totalPages.value)
  if (next === listPage.value) return
  listPage.value = next
  refresh().catch(() => {})
}

watch(listPlatform, () => {
  listPage.value = 1
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
    <PageHeader title="入库浏览" subtitle="按平台筛选 · 翻页查看 · 改判情感">
      <template #actions>
        <RouterLink class="btn btn-secondary btn-sm" to="/monitor">去采集</RouterLink>
        <button type="button" class="btn btn-ghost btn-sm" :disabled="loading" @click="refresh">
          <RefreshCw :size="14" />
          刷新
        </button>
      </template>
    </PageHeader>

    <p v-if="message" class="ok-text status-line">{{ message }}</p>
    <p v-if="error" class="err status-line">{{ error }}</p>

    <section class="panel list-panel">
      <div class="toolbar">
        <div class="toolbar-left">
          <h3 class="list-title">入库结果</h3>
          <span class="pill pill-default">
            {{ total ? `${pageFrom}–${pageTo} / ${total}` : `0 / ${total}` }}
          </span>
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
      <p v-else class="hint">
        {{ loading ? '加载中…' : '当前筛选下暂无帖子。可先到「监测」采集或导入。' }}
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
.table-scroll {
  max-height: min(68vh, 40rem);
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
.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
