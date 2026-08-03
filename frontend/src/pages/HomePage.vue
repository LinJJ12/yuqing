<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { isAuthenticated } from '../lib/auth'
import logoUrl from '../assets/logo.png'

const route = useRoute()
// 依赖路由变化刷新登录态（登出后再回首页）
const loggedIn = computed(() => {
  void route.fullPath
  return isAuthenticated()
})
</script>

<template>
  <div class="home">
    <header class="home-nav">
      <RouterLink class="brand" to="/">
        <img :src="logoUrl" alt="" class="brand-logo" width="28" height="28" />
        <span class="brand-name">知微</span>
      </RouterLink>
      <div class="nav-actions">
        <RouterLink v-if="loggedIn" class="btn btn-primary" to="/overview">进入工作台</RouterLink>
        <template v-else>
          <RouterLink class="btn btn-ghost" to="/login">登录</RouterLink>
          <RouterLink class="btn btn-primary" to="/login">进入工作台</RouterLink>
        </template>
      </div>
    </header>

    <main class="home-hero">
      <p class="eyebrow">观众反馈 · 内容口碑</p>
      <h1 class="hero-title">知微</h1>
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
        <RouterLink v-if="!loggedIn" class="btn btn-ghost btn-lg" to="/login">已有账号</RouterLink>
      </div>
      <ul class="feature-list" aria-label="核心能力">
        <li>采集入库</li>
        <li>情感与主题洞察</li>
        <li>预警与报告导出</li>
      </ul>
    </main>
  </div>
</template>

<style scoped>
.home {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(1200px 520px at 12% -10%, rgba(15, 118, 110, 0.12), transparent 55%),
    radial-gradient(900px 480px at 90% 0%, rgba(3, 105, 161, 0.08), transparent 50%),
    linear-gradient(180deg, #f8fafc 0%, var(--bg-base) 45%, #eef2f7 100%);
}

.home-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  text-decoration: none;
  color: var(--text-primary);
}

.brand-logo {
  border-radius: 6px;
}

.brand-name {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.home-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 720px;
  margin: 0 auto;
  padding: 3.5rem 1.5rem 4rem;
}

.eyebrow {
  margin: 0 0 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-primary);
}

.hero-title {
  margin: 0;
  font-size: clamp(2.75rem, 6vw, 4rem);
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.05;
  color: var(--text-primary);
}

.hero-lead {
  margin: 1.1rem 0 0;
  max-width: 38rem;
  font-size: 1.05rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.75rem;
}

.btn-lg {
  min-height: 42px;
  padding: 0.55rem 1.15rem;
  font-size: 0.9375rem;
}

.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin: 2.25rem 0 0;
  padding: 0;
  list-style: none;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.feature-list li {
  position: relative;
  padding-left: 0.85rem;
}

.feature-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.7;
}

@media (max-width: 640px) {
  .home-hero {
    padding-top: 2.5rem;
  }
  .nav-actions .btn-ghost {
    display: none;
  }
}
</style>
