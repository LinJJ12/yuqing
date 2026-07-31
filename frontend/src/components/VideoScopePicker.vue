<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchVideoSummaries } from '../api/client'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  /** false：报告页等必须选具体视频，不提供「全部」 */
  allowEmpty: { type: Boolean, default: true },
  label: { type: String, default: '视频' },
})

const route = useRoute()
const router = useRouter()

const videos = ref([])
const videoQuery = ref('')
const showManual = ref(false)
const bvidInput = ref('')
const loadingVideos = ref(false)

const activeBvid = computed(() => String(route.query.bvid || '').trim())
const showFilter = computed(() => (videos.value || []).length > 6)

const filteredVideos = computed(() => {
  const q = videoQuery.value.trim().toLowerCase()
  const list = videos.value || []
  if (!q) return list
  return list.filter((v) => {
    const id = String(v.bvid || '').toLowerCase()
    const title = String(v.video_title || '').toLowerCase()
    return id.includes(q) || title.includes(q)
  })
})

const activeTitle = computed(() => {
  if (!activeBvid.value) return ''
  const hit = (videos.value || []).find((v) => v.bvid === activeBvid.value)
  return hit?.video_title || ''
})

const selectValue = computed(() => activeBvid.value)

async function loadVideos() {
  loadingVideos.value = true
  try {
    const res = await fetchVideoSummaries(50)
    if (res.ok) videos.value = res.data.items || []
  } finally {
    loadingVideos.value = false
  }
}

function selectBvid(bvid) {
  const next = (bvid || '').trim()
  if (!props.allowEmpty && !next) return
  const q = { ...route.query }
  if (next) q.bvid = next
  else delete q.bvid
  router.push({ query: q })
}

function onPick(e) {
  selectBvid(e.target.value)
}

function submitManual() {
  const v = bvidInput.value.trim()
  if (!v) return
  selectBvid(v)
  showManual.value = false
}

function clearScope() {
  if (!props.allowEmpty) return
  selectBvid('')
}

watch(
  activeBvid,
  (v) => {
    bvidInput.value = v
  },
  { immediate: true },
)

onMounted(loadVideos)

defineExpose({ activeBvid, loadVideos, videos })
</script>

<template>
  <div class="scope-bar" :class="{ 'has-actions': $slots.actions }">
    <span class="scope-label">{{ label }}</span>
    <select
      class="input scope-select"
      :value="selectValue"
      :disabled="disabled || loadingVideos || (!videos.length && !activeBvid)"
      :title="activeTitle || activeBvid || (allowEmpty ? '全部视频' : '选择视频')"
      @change="onPick"
    >
      <option v-if="allowEmpty" value="">
        {{
          videos.length
            ? `全部（${videos.length}）`
            : loadingVideos
              ? '加载中…'
              : '暂无视频'
        }}
      </option>
      <option v-else value="" disabled>
        {{
          videos.length
            ? `选择视频（${videos.length}）`
            : loadingVideos
              ? '加载中…'
              : '暂无视频'
        }}
      </option>
      <option
        v-if="activeBvid && !filteredVideos.some((v) => v.bvid === activeBvid)"
        :value="activeBvid"
      >
        {{ activeBvid }}
      </option>
      <option v-for="v in filteredVideos" :key="v.bvid" :value="v.bvid">
        {{ v.video_title || v.bvid }}（{{ v.comment_count }}）
      </option>
    </select>

    <input
      v-if="showFilter && !showManual"
      v-model="videoQuery"
      class="input scope-filter"
      placeholder="筛选…"
      :disabled="disabled"
    />

    <template v-if="showManual">
      <input
        v-model="bvidInput"
        class="input scope-manual"
        placeholder="BV 号或链接"
        :disabled="disabled"
        @keyup.enter="submitManual"
      />
      <button type="button" class="btn btn-secondary btn-sm" :disabled="disabled" @click="submitManual">
        确定
      </button>
      <button type="button" class="link-btn" :disabled="disabled" @click="showManual = false">
        取消
      </button>
    </template>

    <template v-else>
      <button
        v-if="allowEmpty && activeBvid"
        type="button"
        class="link-btn"
        :disabled="disabled"
        @click="clearScope"
      >
        全部
      </button>
      <button type="button" class="link-btn" :disabled="disabled" @click="showManual = true">
        输入 BV
      </button>
    </template>

    <div v-if="$slots.actions" class="scope-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.scope-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 0 0 0.75rem;
  padding: 0.35rem 0;
  min-height: 2rem;
}
.scope-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
  margin-left: auto;
}
.scope-label {
  flex: none;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}
.scope-select {
  flex: 1 1 14rem;
  max-width: 22rem;
  min-width: 10rem;
  height: 2rem;
  padding: 0 1.75rem 0 0.65rem;
  font-size: 0.8125rem;
  line-height: 1.2;
}
.scope-filter,
.scope-manual {
  flex: 0 1 9rem;
  width: 9rem;
  max-width: 12rem;
  height: 2rem;
  padding: 0 0.55rem;
  font-size: 0.8125rem;
}
.scope-manual {
  flex: 1 1 12rem;
  max-width: 18rem;
  width: auto;
}
.link-btn {
  flex: none;
  margin: 0;
  padding: 0.15rem 0.2rem;
  border: none;
  background: transparent;
  color: var(--accent-primary);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.link-btn:hover:not(:disabled) {
  text-decoration: underline;
}
.link-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
