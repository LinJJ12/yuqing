<script setup>
import { computed } from 'vue'
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
            <div>
              <strong>{{ item.label }}</strong>
              <span>{{ item.desc }}</span>
            </div>
          </li>
        </ul>
      </section>

      <aside class="hero-visual" aria-hidden="true">
        <div class="preview-shell">
          <div class="preview-side">
            <div class="preview-brand">知微</div>
            <div class="preview-nav preview-nav-active" />
            <div class="preview-nav" />
            <div class="preview-nav" />
            <div class="preview-nav" />
          </div>
          <div class="preview-main">
            <div class="preview-top">
              <span>总览</span>
              <span class="preview-pill">服务正常</span>
            </div>
            <div class="preview-kpis">
              <div class="preview-kpi">
                <small>帖子</small>
                <strong>12.4k</strong>
              </div>
              <div class="preview-kpi">
                <small>负面占比</small>
                <strong class="neg">8.2%</strong>
              </div>
              <div class="preview-kpi">
                <small>预警</small>
                <strong>3</strong>
              </div>
            </div>
            <div class="preview-chart">
              <div class="chart-bars">
                <span style="--h: 42%" />
                <span style="--h: 68%" />
                <span style="--h: 55%" />
                <span style="--h: 82%" />
                <span style="--h: 60%" />
                <span style="--h: 74%" />
                <span style="--h: 48%" />
              </div>
              <div class="chart-legend">
                <Inbox :size="14" />
                <FileText :size="14" />
                <span>情感趋势 · 近 7 日</span>
              </div>
            </div>
          </div>
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
  animation: drift 14s ease-in-out infinite alternate;
}

.bg-orb-b {
  width: min(40vw, 380px);
  height: min(40vw, 380px);
  bottom: -18%;
  left: -6%;
  background: rgba(3, 105, 161, 0.12);
  animation: drift 18s ease-in-out infinite alternate-reverse;
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
  transition: transform 160ms var(--ease-out), box-shadow 160ms, background 160ms;
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
  align-items: flex-start;
  padding: 0.85rem 0.9rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.feature-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 8px;
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.1);
}

.feature-item strong {
  display: block;
  font-size: 0.8125rem;
  font-weight: 650;
  color: var(--home-ink);
}

.feature-item span {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.75rem;
  color: var(--home-muted);
  line-height: 1.4;
}

.hero-visual {
  animation: fade-up 0.75s var(--ease-out) 0.18s both;
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
    0 24px 48px rgba(15, 23, 42, 0.08);
  transform: perspective(1200px) rotateY(-6deg) rotateX(3deg);
  transform-origin: center left;
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
  height: 10px;
  margin: 0.45rem 0;
  border-radius: 999px;
  background: #e2e8f0;
}

.preview-nav-active {
  background: rgba(15, 118, 110, 0.35);
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
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-success);
  background: rgba(22, 163, 74, 0.08);
  border: 1px solid rgba(22, 163, 74, 0.18);
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
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
}

.preview-kpi small {
  display: block;
  font-size: 0.6875rem;
  color: var(--home-muted);
}

.preview-kpi strong {
  display: block;
  margin-top: 0.2rem;
  font-family: var(--font-mono);
  font-size: 1.05rem;
  letter-spacing: -0.03em;
}

.preview-kpi .neg {
  color: var(--color-destructive);
}

.preview-chart {
  padding: 0.85rem 0.9rem 0.75rem;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: linear-gradient(180deg, #f8fafc, #fff);
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 0.45rem;
  height: 110px;
  margin-bottom: 0.65rem;
}

.chart-bars span {
  flex: 1;
  height: var(--h);
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, #14b8a6, #0f766e);
  opacity: 0.85;
  animation: bar-rise 0.9s var(--ease-out) both;
}

.chart-bars span:nth-child(2) { animation-delay: 0.05s; }
.chart-bars span:nth-child(3) { animation-delay: 0.1s; }
.chart-bars span:nth-child(4) { animation-delay: 0.15s; }
.chart-bars span:nth-child(5) { animation-delay: 0.2s; }
.chart-bars span:nth-child(6) { animation-delay: 0.25s; }
.chart-bars span:nth-child(7) { animation-delay: 0.3s; }

.chart-legend {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--home-muted);
  font-size: 0.7rem;
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
    transform: translate3d(-18px, 22px, 0);
  }
}

@keyframes bar-rise {
  from {
    transform: scaleY(0.35);
    opacity: 0.35;
  }
  to {
    transform: scaleY(1);
    opacity: 0.85;
  }
}

@media (max-width: 900px) {
  .home-main {
    grid-template-columns: 1fr;
  }

  .preview-shell {
    transform: none;
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
}

@media (prefers-reduced-motion: reduce) {
  .home-nav,
  .hero-copy,
  .hero-visual,
  .bg-orb,
  .chart-bars span,
  .btn-lg {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}
</style>
