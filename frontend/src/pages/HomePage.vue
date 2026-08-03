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
  { icon: ScanSearch, label: '情感洞察', desc: '情感分布 · 词云 · 主题' },
  { icon: BellRing, label: '预警报告', desc: '异常提示与报告导出' },
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
    <header class="home-nav">
      <div class="nav-inner">
        <RouterLink class="brand" to="/">
          <img :src="logoUrl" alt="" class="brand-logo" width="28" height="28" />
          <span class="brand-name">知微</span>
        </RouterLink>
        <nav class="nav-actions">
          <RouterLink v-if="loggedIn" class="btn btn-primary" to="/overview">进入工作台</RouterLink>
          <template v-else>
            <RouterLink class="nav-link" to="/login">登录</RouterLink>
            <RouterLink class="btn btn-primary" to="/login">进入工作台</RouterLink>
          </template>
        </nav>
      </div>
    </header>

    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <p class="eyebrow">本地观众反馈分析</p>
          <h1 class="title-brand">知微</h1>
          <p class="hero-lead">见微知著 — 从评论细节见口碑走势</p>

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
          <p class="hero-note">本地单管理员 · 数据落本机</p>
        </div>

        <div class="hero-visual">
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
        </div>
      </div>
    </section>

    <section class="features" aria-label="核心能力">
      <div class="features-inner">
        <article v-for="item in features" :key="item.label" class="feature-card">
          <span class="feature-icon" aria-hidden="true">
            <component :is="item.icon" :size="20" :stroke-width="1.9" />
          </span>
          <h2>{{ item.label }}</h2>
          <p>{{ item.desc }}</p>
        </article>
      </div>
    </section>

    <footer class="home-footer">
      <div class="footer-inner">
        <span class="footer-desc">本地观众反馈分析工作台</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.home {
  --ink: var(--color-foreground);
  --muted: var(--color-muted-fg);
  --line: var(--color-border);
  --teal: var(--color-primary);
  --serif: 'Songti SC', 'SimSun', 'STSong', 'Noto Serif SC', serif;
  /* 占满 public-shell：多余空白分给 hero，页脚贴底；溢出由 public-shell 滚动 */
  box-sizing: border-box;
  min-height: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  color: var(--ink);
}

.home-nav {
  flex: 0 0 auto;
  position: relative;
  z-index: 10;
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 56px;
  padding: 0 clamp(1.25rem, 3vw, 2.5rem);
  box-sizing: border-box;
}

.hero-inner,
.features-inner {
  width: min(1100px, calc(100% - 2.5rem));
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: inherit;
}

.brand-logo {
  border-radius: 6px;
}

.brand-name {
  font-family: var(--serif);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.nav-link {
  padding: 0.4rem 0.7rem;
  border-radius: 6px;
  color: #475569;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
}

.nav-link:hover {
  color: var(--ink);
  background: #f8fafc;
}

/* —— Hero：文案 + 产品预览；吃掉剩余视口高度 —— */
.hero {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  padding: 1.25rem 0 0.75rem;
  min-height: 0;
}

.hero-inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
  gap: clamp(1rem, 2.2vw, 1.75rem);
  align-items: center;
  width: min(1040px, calc(100% - 2.5rem));
}

.eyebrow {
  margin: 0 0 0.85rem;
  display: inline-flex;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--teal);
  background: #f0fdfa;
  border: 1px solid #99f6e4;
}

.title-brand {
  margin: 0;
  font-family: var(--serif);
  font-size: clamp(3.1rem, 6vw, 4.5rem);
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: 1.05;
}

.hero-lead {
  margin: 1rem 0 0;
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.55;
  color: #334155;
}

.hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.5rem;
}

.btn-lg {
  min-height: 44px;
  padding: 0.6rem 1.2rem;
  font-size: 0.9375rem;
  border-radius: 8px;
}

.hero-note {
  margin: 0.75rem 0 0;
  font-size: 0.78rem;
  color: var(--muted);
}

.hero-visual {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
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

/* —— Features —— */
.features {
  flex: 0 0 auto;
  padding: 0 0 0.5rem;
}

.features-inner {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
}

.feature-card {
  padding: 1.25rem 1.2rem 1.3rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  transition: border-color 180ms, box-shadow 180ms, transform 180ms;
}

.feature-card:hover {
  border-color: #99f6e4;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  transform: translateY(-2px);
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: 0.85rem;
  border-radius: 10px;
  color: var(--teal);
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  line-height: 0;
}

.feature-icon :deep(svg) {
  display: block;
}

.feature-card h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.feature-card p {
  margin: 0.4rem 0 0;
  font-size: 0.875rem;
  line-height: 1.45;
  color: #475569;
}

.home-footer {
  flex: 0 0 auto;
  border-top: 1px solid var(--line);
  background: #fff;
  padding: 0;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
  min-height: 44px;
  padding: 0.65rem clamp(1.25rem, 3vw, 2.5rem);
  box-sizing: border-box;
  margin: 0;
  font-size: 0.78rem;
  color: var(--muted);
}

.footer-desc {
  text-align: right;
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
  .hero-inner,
  .features-inner {
    grid-template-columns: 1fr;
  }

  .hero {
    flex: 0 0 auto;
    align-items: stretch;
    padding-top: 1.5rem;
  }

  .hero-visual {
    order: 2;
  }

  .preview-stage {
    max-width: 480px;
  }
}

@media (max-width: 640px) {
  .nav-link {
    display: none;
  }

  .nav-inner,
  .footer-inner {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .hero-inner,
  .features-inner {
    width: min(1100px, calc(100% - 2rem));
  }
}

@media (prefers-reduced-motion: reduce) {
  .preview-stage,
  .preview-kpi,
  .chart-bar,
  .feature-card,
  .pill-dot,
  .alert-ping {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}
</style>
