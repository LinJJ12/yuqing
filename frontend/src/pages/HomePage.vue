<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  BellRing,
  FileText,
  Inbox,
  Radar,
  ScanSearch,
} from '@lucide/vue'
import { AUTH_CHANGED_EVENT, isAuthenticated } from '../lib/auth'
import logoUrl from '../assets/logo.png'

const loggedIn = ref(isAuthenticated())

function syncAuth() {
  loggedIn.value = isAuthenticated()
}

const features = [
  { icon: Radar, label: '采集入库', desc: 'BV 评论与文件导入' },
  { icon: ScanSearch, label: '情感洞察', desc: '分布 · 词云 · 主题' },
  { icon: BellRing, label: '预警报告', desc: '异常提示与导出交付' },
]

const previewNav = ['总览', '监测', '洞察', '预警']
const chartBars = [
  { h: 42, day: '一' },
  { h: 68, day: '二' },
  { h: 55, day: '三' },
  { h: 82, day: '四' },
  { h: 60, day: '五' },
  { h: 74, day: '六' },
  { h: 48, day: '日' },
]

const reduceMotion = ref(false)
const previewActive = ref(false)
const tiltX = ref(0)
const tiltY = ref(0)
const activeBar = ref(-1)
const activeKpi = ref(-1)
const activeNav = ref(0)

const previewStyle = computed(() => {
  if (reduceMotion.value) return { transform: 'none' }
  const scale = previewActive.value ? 1.02 : 1
  return {
    transform: `perspective(1200px) rotateY(${-6 + tiltY.value}deg) rotateX(${3 + tiltX.value}deg) scale(${scale})`,
  }
})

function onPreviewEnter() {
  previewActive.value = true
}

function onPreviewMove(event) {
  if (reduceMotion.value) return
  const el = event.currentTarget
  const rect = el.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const nx = (event.clientX - rect.left) / rect.width - 0.5
  const ny = (event.clientY - rect.top) / rect.height - 0.5
  tiltY.value = nx * 9
  tiltX.value = -ny * 6
}

function onPreviewLeave() {
  previewActive.value = false
  tiltX.value = 0
  tiltY.value = 0
  activeBar.value = -1
  activeKpi.value = -1
  activeNav.value = 0
}

let mediaQuery
function onMotionChange(event) {
  reduceMotion.value = event.matches
  if (event.matches) onPreviewLeave()
}

onMounted(() => {
  syncAuth()
  window.addEventListener(AUTH_CHANGED_EVENT, syncAuth)
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reduceMotion.value = mediaQuery.matches
  mediaQuery.addEventListener('change', onMotionChange)
})

onUnmounted(() => {
  window.removeEventListener(AUTH_CHANGED_EVENT, syncAuth)
  mediaQuery?.removeEventListener('change', onMotionChange)
})
</script>

<template>
  <div class="home">
    <div class="bg-grid" aria-hidden="true" />
    <div class="bg-orb bg-orb-a" aria-hidden="true" />
    <div class="bg-orb bg-orb-b" aria-hidden="true" />

    <header class="home-nav">
      <RouterLink class="brand" to="/">
        <img :src="logoUrl" alt="" class="brand-logo" width="32" height="32" />
        <span class="brand-name">知微</span>
      </RouterLink>
      <nav class="nav-actions">
        <RouterLink v-if="loggedIn" class="btn btn-primary" to="/overview">进入工作台</RouterLink>
        <template v-else>
          <RouterLink class="nav-link" to="/login">登录</RouterLink>
          <RouterLink class="btn btn-primary" to="/login">进入工作台</RouterLink>
        </template>
      </nav>
    </header>

    <main class="home-main">
      <section class="hero-copy">
        <p class="eyebrow">观众反馈 · 内容口碑</p>
        <h1 class="hero-title">
          <span class="title-brand">知微</span>
        </h1>
        <p class="hero-lead">
          本地可运行的社交媒体观众反馈分析工作台——采集 B 站评论，做情感、主题与趋势，预警异常，输出单视频与全局报告。
        </p>

        <div class="hero-cta">
          <RouterLink
            class="btn btn-primary btn-lg"
            :to="loggedIn ? '/overview' : '/login'"
          >
            {{ loggedIn ? '进入工作台' : '登录并开始' }}
          </RouterLink>
          <RouterLink
            v-if="!loggedIn"
            class="btn btn-secondary btn-lg"
            to="/login"
          >
            已有账号
          </RouterLink>
        </div>

        <ul class="feature-row" aria-label="核心能力">
          <li v-for="item in features" :key="item.label" class="feature-item">
            <span class="feature-icon" aria-hidden="true">
              <component :is="item.icon" :size="18" :stroke-width="1.75" />
            </span>
            <div class="feature-text">
              <strong>{{ item.label }}</strong>
              <span>{{ item.desc }}</span>
            </div>
          </li>
        </ul>
      </section>

      <aside class="hero-visual">
        <div class="visual-glow" aria-hidden="true" />
        <div
          class="preview-stage"
          :class="{ active: previewActive }"
          :style="previewStyle"
          @pointerenter="onPreviewEnter"
          @pointermove="onPreviewMove"
          @pointerleave="onPreviewLeave"
        >
          <div class="preview-shell">
            <div class="preview-side">
              <div class="preview-brand">知微</div>
              <button
                v-for="(label, i) in previewNav"
                :key="label"
                type="button"
                class="preview-nav"
                :class="{ active: activeNav === i || (!previewActive && i === 0) }"
                tabindex="-1"
                @pointerenter="activeNav = i"
              >
                {{ label }}
              </button>
            </div>
            <div class="preview-main">
              <div class="preview-top">
                <span class="preview-title">总览</span>
                <span class="preview-pill" :class="{ live: previewActive }">
                  <i class="pill-dot" />
                  服务正常
                </span>
              </div>
              <div class="preview-kpis">
                <div
                  v-for="(kpi, i) in [
                    { label: '帖子', value: '12.4k' },
                    { label: '负面占比', value: '8.2%', neg: true },
                    { label: '预警', value: '3', alert: true },
                  ]"
                  :key="kpi.label"
                  class="preview-kpi"
                  :class="{ hot: activeKpi === i }"
                  @pointerenter="activeKpi = i"
                  @pointerleave="activeKpi = -1"
                >
                  <small>{{ kpi.label }}</small>
                  <strong :class="{ neg: kpi.neg }">
                    {{ kpi.value }}
                    <i
                      v-if="kpi.alert"
                      class="alert-ping"
                      :class="{ live: previewActive || activeKpi === i }"
                    />
                  </strong>
                </div>
              </div>
              <div class="preview-chart" :class="{ hot: previewActive }">
                <div class="chart-head">情感趋势 · 近 7 日</div>
                <div class="chart-bars">
                  <button
                    v-for="(bar, idx) in chartBars"
                    :key="idx"
                    type="button"
                    class="chart-bar-wrap"
                    :class="{ hot: activeBar === idx }"
                    tabindex="-1"
                    @pointerenter="activeBar = idx"
                    @pointerleave="activeBar = -1"
                  >
                    <span class="chart-bar" :style="{ '--h': `${bar.h}%` }" />
                    <span class="chart-day">{{ bar.day }}</span>
                  </button>
                </div>
                <div class="chart-legend">
                  <Inbox :size="13" :stroke-width="2" />
                  <FileText :size="13" :stroke-width="2" />
                  <span>入库 · 报告联动</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p class="preview-hint" :class="{ hide: previewActive }">悬停预览可交互</p>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.home {
  --home-ink: #0f172a;
  --home-muted: #64748b;
  --ink: var(--color-foreground, #0f172a);
  --muted: var(--color-muted-fg, #64748b);
  --line: var(--color-border, #e2e8f0);
  --teal: var(--color-primary, #0f766e);
  --serif: 'Songti SC', 'SimSun', 'STSong', 'Noto Serif SC', serif;
  position: relative;
  isolation: isolate;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(165deg, #f8fafc 0%, #eef6f4 42%, #f1f5f9 100%);
  color: var(--home-ink);
}

.bg-grid {
  position: absolute;
  inset: 0;
  z-index: -2;
  background-image:
    linear-gradient(rgba(15, 118, 110, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.045) 1px, transparent 1px);
  background-size: 48px 48px;
  -webkit-mask-image: radial-gradient(ellipse 80% 70% at 50% 30%, #000 20%, transparent 75%);
  mask-image: radial-gradient(ellipse 80% 70% at 50% 30%, #000 20%, transparent 75%);
}

.bg-orb {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  filter: blur(40px);
  pointer-events: none;
}

.bg-orb-a {
  width: min(52vw, 520px);
  height: min(52vw, 520px);
  top: -12%;
  right: -8%;
  background: rgba(15, 118, 110, 0.18);
  animation: drift 18s ease-in-out infinite alternate;
}

.bg-orb-b {
  width: min(40vw, 380px);
  height: min(40vw, 380px);
  bottom: -18%;
  left: -6%;
  background: rgba(3, 105, 161, 0.12);
  animation: drift 22s ease-in-out infinite alternate-reverse;
}

.home-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem clamp(1.25rem, 3vw, 2.25rem);
  background: rgba(255, 255, 255, 0.78);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  backdrop-filter: blur(12px);
  animation: fade-down 0.55s var(--ease-out) both;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  text-decoration: none;
  color: inherit;
}

.brand-logo {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.brand-name {
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.nav-link {
  padding: 0.4rem 0.7rem;
  color: var(--home-muted);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: var(--radius-md);
  transition: color 160ms, background 160ms;
}

.nav-link:hover {
  color: var(--home-ink);
  background: rgba(15, 118, 110, 0.06);
}

.home-main {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: clamp(1.5rem, 4vw, 3.5rem);
  align-items: center;
  width: min(1120px, 100%);
  margin: 0 auto;
  padding: clamp(2rem, 5vh, 3.5rem) clamp(1.25rem, 3vw, 2.25rem)
    clamp(2.5rem, 6vh, 4rem);
}

.hero-copy {
  animation: fade-up 0.65s var(--ease-out) 0.08s both;
}

.eyebrow {
  margin: 0 0 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.1);
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.hero-title {
  margin: 0;
  line-height: 1;
}

.title-brand {
  display: block;
  font-size: clamp(3.25rem, 8vw, 5rem);
  font-weight: 780;
  letter-spacing: -0.05em;
  background: linear-gradient(135deg, #0f172a 20%, #0f766e 85%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-lead {
  margin: 1.15rem 0 0;
  max-width: 34rem;
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text-secondary);
}

.hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-top: 1.85rem;
}

.btn-lg {
  min-height: 44px;
  padding: 0.6rem 1.25rem;
  font-size: 0.9375rem;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  transition: transform 180ms var(--ease-out), box-shadow 180ms, background 180ms;
}

.btn-primary.btn-lg:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(15, 118, 110, 0.22);
}

.feature-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 2.25rem 0 0;
  padding: 0;
  list-style: none;
}

.feature-item {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  min-height: 64px;
  padding: 0.85rem 0.9rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  transition: border-color 180ms, box-shadow 180ms, transform 180ms;
}

.feature-item:hover {
  border-color: rgba(15, 118, 110, 0.28);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border-radius: 8px;
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.1);
  line-height: 0;
}

.feature-icon :deep(svg) {
  display: block;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.feature-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.15rem;
}

.feature-text strong {
  display: block;
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.25;
  color: var(--home-ink);
}

.feature-text span {
  display: block;
  font-size: 0.75rem;
  color: var(--home-muted);
  line-height: 1.35;
}

.hero-visual {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: fade-up 0.75s var(--ease-out) 0.18s both;
}

.visual-glow {
  position: absolute;
  inset: 8% 4% auto;
  height: 70%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(15, 118, 110, 0.16), transparent 68%);
  filter: blur(8px);
  pointer-events: none;
  z-index: 0;
}

.preview-stage {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 540px;
  transform-origin: center;
  transition: transform 90ms linear, filter 360ms ease;
  will-change: transform;
}

.preview-stage:not(.active) {
  transition: transform 500ms cubic-bezier(0.22, 1, 0.36, 1), filter 360ms ease;
}

.preview-stage.active {
  filter: drop-shadow(0 20px 36px rgba(15, 23, 42, 0.14));
}

.preview-shell {
  display: grid;
  grid-template-columns: 96px 1fr;
  min-height: 340px;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #cbd5e1;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 16px 40px rgba(15, 23, 42, 0.1);
}

.preview-side {
  padding: 0.75rem 0.5rem;
  background: #f8fafc;
  border-right: 1px solid var(--line);
}

.preview-brand {
  margin: 0 0 0.55rem;
  padding: 0 0.45rem;
  font-family: var(--serif);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--ink);
}

.preview-nav {
  display: block;
  width: 100%;
  margin: 0.2rem 0;
  padding: 0.4rem 0.45rem;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 600;
  text-align: left;
  cursor: default;
  transition: background 200ms, color 200ms;
}

.preview-nav.active {
  background: #ccfbf1;
  color: var(--teal);
}

.preview-main {
  padding: 0.9rem 1rem 1rem;
}

.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.8rem;
}

.preview-title {
  font-size: 0.9rem;
  font-weight: 700;
}

.preview-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 650;
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}

.preview-pill.live .pill-dot {
  animation: pulse 1.8s ease-out infinite;
}

.preview-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.preview-kpi {
  padding: 0.6rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #fff;
  box-shadow: inset 3px 0 0 var(--teal);
  transition: transform 200ms, border-color 200ms, box-shadow 200ms;
}

.preview-kpi.hot {
  transform: translateY(-2px);
  border-color: #99f6e4;
  box-shadow:
    inset 3px 0 0 var(--teal),
    0 8px 16px rgba(15, 118, 110, 0.1);
}

.preview-kpi small {
  display: block;
  font-size: 0.7rem;
  color: var(--muted);
}

.preview-kpi strong {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.2rem;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
}

.preview-kpi .neg {
  color: #dc2626;
}

.alert-ping {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d97706;
  opacity: 0.75;
}

.alert-ping.live {
  opacity: 1;
  animation: pulse-warn 1.6s ease-out infinite;
}

.preview-chart {
  padding: 0.7rem 0.75rem 0.6rem;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #f8fafc;
  transition: border-color 200ms;
}

.preview-chart.hot {
  border-color: #99f6e4;
}

.chart-head {
  margin-bottom: 0.45rem;
  font-size: 0.72rem;
  font-weight: 650;
  color: #475569;
}

.chart-bars {
  display: flex;
  align-items: stretch;
  gap: 0.35rem;
  height: 104px;
  margin-bottom: 0.4rem;
}

.chart-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: default;
}

.chart-bar {
  display: block;
  width: 100%;
  height: var(--h);
  border-radius: 5px 5px 2px 2px;
  background: linear-gradient(180deg, #2dd4bf, #0f766e);
  transform-origin: bottom;
  transform: scaleY(0.96);
  transition: transform 250ms cubic-bezier(0.22, 1, 0.36, 1);
}

.preview-stage.active .chart-bar {
  transform: scaleY(1);
}

.chart-bar-wrap.hot .chart-bar {
  transform: scaleY(1.08);
}

.chart-day {
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--muted);
}

.chart-bar-wrap.hot .chart-day {
  color: var(--teal);
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
}

.chart-legend :deep(svg) {
  display: block;
  color: var(--teal);
}

.preview-hint {
  margin: 0.7rem 0 0;
  font-size: 0.75rem;
  color: var(--muted);
  transition: opacity 200ms;
}

.preview-hint.hide {
  opacity: 0;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fade-down {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes drift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(-14px, 16px, 0);
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(22, 163, 74, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0);
  }
}

@keyframes pulse-warn {
  0% {
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.4);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(217, 119, 6, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0);
  }
}

@media (max-width: 900px) {
  .home-main {
    grid-template-columns: 1fr;
  }

  .preview-stage {
    max-width: 480px;
  }

  .feature-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .nav-link {
    display: none;
  }

  .preview-hint {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-nav,
  .hero-copy,
  .hero-visual,
  .bg-orb,
  .pill-dot,
  .alert-ping,
  .btn-lg,
  .feature-item,
  .preview-stage,
  .preview-kpi,
  .chart-bar,
  .preview-nav {
    animation: none !important;
    transition: none !important;
  }

  .preview-stage,
  .btn-lg,
  .feature-item,
  .preview-kpi,
  .chart-bar {
    transform: none !important;
  }
}
</style>
