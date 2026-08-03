<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  BellRing,
  FileText,
  Inbox,
  Radar,
  ScanSearch,
} from '@lucide/vue'
import { isAuthenticated } from '../lib/auth'
import logoUrl from '../assets/logo.png'

const route = useRoute()
const loggedIn = computed(() => {
  void route.fullPath
  return isAuthenticated()
})

const features = [
  { icon: Radar, label: '采集入库', desc: 'BV 评论与文件导入' },
  { icon: ScanSearch, label: '情感洞察', desc: '分布 · 词云 · 主题' },
  { icon: BellRing, label: '预警报告', desc: '异常提示与导出交付' },
]

const chartBars = [42, 68, 55, 82, 60, 74, 48]

const reduceMotion = ref(false)
const previewActive = ref(false)
const tiltX = ref(0)
const tiltY = ref(0)
const activeBar = ref(-1)
const activeKpi = ref(-1)
const activeNav = ref(0)

const previewStyle = computed(() => {
  if (reduceMotion.value) {
    return { transform: 'none' }
  }
  const baseY = -5
  const baseX = 2.5
  const scale = previewActive.value ? 1.025 : 1
  return {
    transform: `perspective(1100px) rotateY(${baseY + tiltY.value}deg) rotateX(${baseX + tiltX.value}deg) scale(${scale})`,
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
  tiltY.value = nx * 12
  tiltX.value = -ny * 9
}

function onPreviewLeave() {
  previewActive.value = false
  tiltX.value = 0
  tiltY.value = 0
  activeBar.value = -1
  activeKpi.value = -1
  activeNav.value = 0
}

function preferReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

let mediaQuery
function onMotionChange(event) {
  reduceMotion.value = event.matches
  if (event.matches) onPreviewLeave()
}

onMounted(() => {
  reduceMotion.value = preferReducedMotion()
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  mediaQuery.addEventListener('change', onMotionChange)
})

onUnmounted(() => {
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
                v-for="i in 4"
                :key="i"
                type="button"
                class="preview-nav"
                :class="{ active: activeNav === i - 1 || (!previewActive && i === 1) }"
                tabindex="-1"
                @pointerenter="activeNav = i - 1"
              />
            </div>
            <div class="preview-main">
              <div class="preview-top">
                <span>总览</span>
                <span class="preview-pill" :class="{ live: previewActive }">
                  <i class="pill-dot" />
                  服务正常
                </span>
              </div>
              <div class="preview-kpis">
                <div
                  class="preview-kpi"
                  :class="{ hot: activeKpi === 0 }"
                  @pointerenter="activeKpi = 0"
                  @pointerleave="activeKpi = -1"
                >
                  <small>帖子</small>
                  <strong>12.4k</strong>
                </div>
                <div
                  class="preview-kpi"
                  :class="{ hot: activeKpi === 1 }"
                  @pointerenter="activeKpi = 1"
                  @pointerleave="activeKpi = -1"
                >
                  <small>负面占比</small>
                  <strong class="neg">8.2%</strong>
                </div>
                <div
                  class="preview-kpi preview-kpi-alert"
                  :class="{ hot: activeKpi === 2 }"
                  @pointerenter="activeKpi = 2"
                  @pointerleave="activeKpi = -1"
                >
                  <small>预警</small>
                  <strong>
                    3
                    <i class="alert-ping" :class="{ live: previewActive || activeKpi === 2 }" />
                  </strong>
                </div>
              </div>
              <div class="preview-chart" :class="{ hot: previewActive }">
                <div class="chart-bars">
                  <button
                    v-for="(h, idx) in chartBars"
                    :key="idx"
                    type="button"
                    class="chart-bar"
                    :class="{ hot: activeBar === idx }"
                    :style="{ '--h': `${h}%` }"
                    tabindex="-1"
                    @pointerenter="activeBar = idx"
                    @pointerleave="activeBar = -1"
                  />
                </div>
                <div class="chart-legend">
                  <span class="legend-icons">
                    <Inbox :size="14" :stroke-width="1.75" />
                    <FileText :size="14" :stroke-width="1.75" />
                  </span>
                  <span class="legend-text">情感趋势 · 近 7 日</span>
                </div>
              </div>
            </div>
          </div>
          <p class="preview-hint">将鼠标移到预览区试试</p>
        </div>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.home {
  --home-ink: #0f172a;
  --home-muted: #64748b;
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
  animation: fade-up 0.75s var(--ease-out) 0.18s both;
}

.preview-stage {
  position: relative;
  transform-style: preserve-3d;
  transform-origin: center center;
  transition:
    transform 90ms linear,
    filter 420ms ease;
  cursor: default;
  will-change: transform;
}

.preview-stage:not(.active) {
  transition:
    transform 520ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 420ms ease;
}

.preview-stage.active {
  filter: drop-shadow(0 22px 36px rgba(15, 23, 42, 0.14));
}

.preview-shell {
  display: grid;
  grid-template-columns: 72px 1fr;
  min-height: 340px;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 18px 40px rgba(15, 23, 42, 0.07);
  transition: box-shadow 420ms cubic-bezier(0.22, 1, 0.36, 1), border-color 300ms;
}

.preview-stage.active .preview-shell {
  border-color: rgba(15, 118, 110, 0.28);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 28px 56px rgba(15, 118, 110, 0.14);
}

.preview-side {
  padding: 0.9rem 0.65rem;
  background: linear-gradient(180deg, #f8fafc, #f1f5f9);
  border-right: 1px solid var(--color-border);
}

.preview-brand {
  margin-bottom: 1rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--home-ink);
  text-align: center;
}

.preview-nav {
  display: block;
  width: 100%;
  height: 10px;
  margin: 0.45rem 0;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: #e2e8f0;
  cursor: default;
  transition:
    background 280ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1);
}

.preview-nav.active {
  background: rgba(15, 118, 110, 0.42);
  transform: scaleX(1.04);
}

.preview-main {
  padding: 0.95rem 1rem 1.1rem;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.65), transparent 40%),
    #fff;
}

.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.9rem;
  font-size: 0.8125rem;
  font-weight: 650;
}

.preview-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-success);
  background: rgba(22, 163, 74, 0.08);
  border: 1px solid rgba(22, 163, 74, 0.18);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  transition: background 280ms, border-color 280ms;
}

.preview-pill.live {
  background: rgba(22, 163, 74, 0.14);
  border-color: rgba(22, 163, 74, 0.3);
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
}

.preview-pill.live .pill-dot {
  animation: pulse-dot 1.8s ease-out infinite;
}

.preview-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.55rem;
  margin-bottom: 0.85rem;
}

.preview-kpi {
  padding: 0.65rem 0.7rem;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: #fff;
  box-shadow: inset 3px 0 0 var(--color-primary);
  transition:
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    border-color 280ms,
    box-shadow 280ms,
    background 280ms;
}

.preview-kpi.hot {
  transform: translateY(-3px);
  border-color: rgba(15, 118, 110, 0.28);
  background: #f8fffd;
  box-shadow:
    inset 3px 0 0 var(--color-primary),
    0 8px 16px rgba(15, 118, 110, 0.1);
}

.preview-kpi small {
  display: block;
  font-size: 0.6875rem;
  color: var(--home-muted);
}

.preview-kpi strong {
  position: relative;
  display: inline-block;
  margin-top: 0.2rem;
  font-family: var(--font-mono);
  font-size: 1.05rem;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.preview-kpi .neg {
  color: var(--color-destructive);
}

.preview-kpi-alert strong {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.alert-ping {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-warning);
  opacity: 0.75;
  transition: opacity 220ms;
}

.alert-ping.live {
  opacity: 1;
  animation: pulse-warn 1.6s ease-out infinite;
}

.preview-chart {
  position: relative;
  overflow: hidden;
  padding: 0.85rem 0.9rem 0.75rem;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, #f8fafc, #fff);
  transition: border-color 300ms, box-shadow 300ms;
}

.preview-chart.hot {
  border-color: rgba(15, 118, 110, 0.22);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.04);
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 0.45rem;
  height: 110px;
  margin-bottom: 0.65rem;
}

.chart-bar {
  flex: 1;
  height: var(--h);
  padding: 0;
  border: 0;
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, #14b8a6, #0f766e);
  opacity: 0.72;
  transform-origin: bottom center;
  transform: scaleY(0.92);
  cursor: default;
  transition:
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 280ms ease,
    filter 280ms ease;
}

.preview-stage.active .chart-bar {
  opacity: 0.86;
  transform: scaleY(1);
}

.chart-bar.hot {
  opacity: 1;
  transform: scaleY(1.12);
  filter: brightness(1.08);
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--home-muted);
  font-size: 0.7rem;
  line-height: 1;
}

.legend-icons {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  line-height: 0;
}

.legend-icons :deep(svg) {
  display: block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.legend-text {
  line-height: 1.2;
}

.preview-hint {
  margin: 0.7rem 0 0;
  text-align: center;
  font-size: 0.75rem;
  color: var(--home-muted);
  opacity: 0.75;
  transition: opacity 280ms;
}

.preview-stage.active .preview-hint {
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

@keyframes pulse-dot {
  0% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(22, 163, 74, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0);
  }
}

@keyframes pulse-warn {
  0% {
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.45);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(217, 119, 6, 0);
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
    max-width: 520px;
    margin: 0 auto;
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
