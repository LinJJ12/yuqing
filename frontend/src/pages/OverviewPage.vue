<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  MessageSquareText,
  Tags,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
} from '@lucide/vue'
import { fetchOverview } from '../api/client'

const loading = ref(true)
const error = ref('')
const overview = ref(null)

const sentimentMap = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  uncertain: '不确定',
  unknown: '未标注',
}

const sentimentPill = {
  positive: 'pill-success',
  neutral: 'pill-default',
  negative: 'pill-danger',
  uncertain: 'pill-warning',
  unknown: 'pill-warning',
}

const platformMap = {
  bili: 'B站',
  campus: '样例/导入',
  xhs: '小红书',
  dy: '抖音',
  wb: '微博',
}

const total = computed(() => overview.value?.total_posts ?? 0)
const topicCount = computed(() => overview.value?.by_topic?.length ?? 0)

function sentimentCount(label) {
  const row = overview.value?.by_sentiment?.find((x) => x.label === label)
  return row?.count ?? 0
}

const positiveCount = computed(() => sentimentCount('positive'))
const negativeCount = computed(() => sentimentCount('negative'))

function platformLabel(code) {
  return platformMap[code] || code || '—'
}

function videoTitle(post) {
  return post?.raw?.extra?.video_title || ''
}

onMounted(async () => {
  try {
    const o = await fetchOverview()
    if (!o.ok) error.value = o.error?.message || '总览加载失败'
    else overview.value = o.data
  } catch {
    error.value = '无法连接后端，请确认服务已启动。'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div v-if="loading" class="panel">
      <div class="skeleton" style="width: 40%; margin-bottom: 0.75rem" />
      <div class="skeleton" style="width: 70%" />
    </div>
    <p v-else-if="error" class="panel err">{{ error }}</p>
    <template v-else>
      <div class="kpi-grid">
        <div class="kpi">
          <div class="kpi-label">
            <span>帖子总量</span>
            <MessageSquareText :size="14" />
          </div>
          <div class="kpi-value">{{ total }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">
            <span>话题数</span>
            <Tags :size="14" />
          </div>
          <div class="kpi-value">{{ topicCount }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">
            <span>正面</span>
            <ThumbsUp :size="14" />
          </div>
          <div class="kpi-value ok">{{ positiveCount }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">
            <span>负面</span>
            <ThumbsDown :size="14" />
          </div>
          <div class="kpi-value bad">{{ negativeCount }}</div>
        </div>
      </div>

      <div class="cols-2">
        <section class="panel">
          <div class="panel-head">
            <h3>数据来源（平台）</h3>
          </div>
          <ul v-if="overview.by_platform?.length" class="stack-list">
            <li v-for="item in overview.by_platform" :key="item.platform">
              <span>{{ platformLabel(item.platform) }}</span>
              <b>{{ item.count }}</b>
            </li>
          </ul>
          <p v-else class="muted">暂无数据</p>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h3>情感分布</h3>
          </div>
          <ul v-if="overview.by_sentiment?.length" class="stack-list">
            <li v-for="item in overview.by_sentiment" :key="item.label">
              <span>{{ sentimentMap[item.label] || item.label }}</span>
              <b>{{ item.count }}</b>
            </li>
          </ul>
          <p v-else class="muted">暂无数据</p>
        </section>
      </div>

      <section class="panel">
        <div class="panel-head">
          <h3>话题分布</h3>
        </div>
        <ul v-if="overview.by_topic?.length" class="stack-list">
          <li v-for="item in overview.by_topic" :key="item.topic">
            <span>{{ item.topic }}</span>
            <b>{{ item.count }}</b>
          </li>
        </ul>
        <p v-else class="muted">暂无数据，请到「监测」页采集或导入。</p>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h3>最近入库</h3>
          <span class="pill pill-default">按采集/导入时间</span>
        </div>
        <div v-if="overview.recent_posts?.length" class="post-list">
          <article
            v-for="post in overview.recent_posts"
            :key="post.id"
            class="post-item"
          >
            <header class="post-meta">
              <b>{{ post.topic || '未分类' }}</b>
              <span class="pill pill-default">{{ platformLabel(post.platform) }}</span>
              <span
                class="pill"
                :class="sentimentPill[post.sentiment_label] || 'pill-default'"
              >
                {{
                  sentimentMap[post.sentiment_label] ||
                  post.sentiment_label ||
                  '—'
                }}
              </span>
              <em>{{ post.fetched_at || post.published_at }}</em>
            </header>
            <p v-if="videoTitle(post)" class="muted" style="margin: 0 0 0.25rem; font-size: 0.8rem">
              {{ videoTitle(post) }}
            </p>
            <p>{{ post.text }}</p>
            <p v-if="post.source_url" style="margin: 0.4rem 0 0">
              <a :href="post.source_url" target="_blank" rel="noopener noreferrer">
                <ExternalLink :size="14" style="vertical-align: -2px; margin-right: 0.2rem" />
                打开原帖
              </a>
            </p>
          </article>
        </div>
        <p v-else class="muted">
          还没有帖子。请打开「监测」采集 B 站评论或上传样例。
        </p>
      </section>
    </template>
  </div>
</template>
