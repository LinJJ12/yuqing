<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { login as loginRequest } from '../api/client'
import { safeInternalPath, setSession } from '../lib/auth'
import logoUrl from '../assets/logo.png'

const router = useRouter()
const route = useRoute()

const username = ref('admin')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  const user = username.value.trim()
  const pass = password.value
  if (!user || !pass) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await loginRequest(user, pass)
    if (!res.ok) {
      error.value = res.error?.message || '登录失败'
      return
    }
    setSession({
      accessToken: res.data.access_token,
      username: res.data.user?.username || user,
    })
    await router.replace(safeInternalPath(route.query.redirect) || '/overview')
  } catch {
    error.value = '无法连接后端，请确认服务已启动'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="bg-grid" aria-hidden="true" />
    <div class="bg-orb bg-orb-a" aria-hidden="true" />
    <div class="bg-orb bg-orb-b" aria-hidden="true" />

    <div class="login-card">
      <div class="card-accent" aria-hidden="true" />

      <RouterLink class="brand" to="/">
        <img :src="logoUrl" alt="" class="brand-logo" width="42" height="42" />
        <div class="brand-text">
          <div class="brand-name">知微</div>
          <div class="brand-sub">本地观众反馈分析工作台</div>
        </div>
      </RouterLink>

      <div class="card-body">
        <p class="eyebrow">本地单管理员</p>
        <h1 class="title">登录</h1>
        <p class="hint">使用管理员账号进入分析工作台</p>

        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span>用户名</span>
            <input
              v-model="username"
              class="input"
              type="text"
              autocomplete="username"
              name="username"
              placeholder="admin"
              required
            />
          </label>
          <label class="field">
            <span>密码</span>
            <input
              v-model="password"
              class="input"
              type="password"
              autocomplete="current-password"
              name="password"
              placeholder="输入密码"
              required
            />
          </label>

          <p v-if="error" class="error" role="alert">{{ error }}</p>

          <button class="btn btn-primary submit" type="submit" :disabled="loading">
            {{ loading ? '登录中…' : '进入工作台' }}
          </button>
        </form>

        <p class="footer">
          <RouterLink to="/">← 返回首页</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  isolation: isolate;
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  overflow: hidden;
  background: linear-gradient(165deg, #f8fafc 0%, #eef6f4 42%, #f1f5f9 100%);
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

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 12px 28px rgba(15, 23, 42, 0.06),
    0 28px 56px rgba(15, 118, 110, 0.1);
  backdrop-filter: blur(16px);
  animation: fade-up 0.55s var(--ease-out) both;
}

.card-accent {
  height: 3px;
  background: linear-gradient(90deg, #0f766e, #2dd4bf 55%, rgba(45, 212, 191, 0.2));
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin: 0;
  padding: 1.25rem 1.6rem 1.15rem;
  text-decoration: none;
  color: inherit;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.55), rgba(248, 250, 252, 0.35));
  transition: background 180ms;
}

.brand:hover {
  background: linear-gradient(180deg, rgba(240, 253, 250, 0.7), rgba(248, 250, 252, 0.45));
}

.brand-logo {
  border-radius: 11px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(15, 118, 110, 0.08);
}

.brand-name {
  font-family: 'Songti SC', 'SimSun', 'STSong', 'Noto Serif SC', serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #0f172a;
  line-height: 1.2;
}

.brand-sub {
  margin-top: 0.2rem;
  font-size: 0.78rem;
  font-weight: 500;
  color: #64748b;
  line-height: 1.35;
}

.card-body {
  padding: 1.35rem 1.6rem 1.45rem;
}

.eyebrow {
  margin: 0 0 0.7rem;
  display: inline-flex;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
}

.title {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 720;
  letter-spacing: -0.03em;
  color: #0f172a;
  line-height: 1.2;
}

.hint {
  margin: 0.45rem 0 0;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.5;
  color: #64748b;
}

.form {
  display: grid;
  gap: 1rem;
  margin-top: 1.4rem;
}

.field {
  display: grid;
  gap: 0.4rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #334155;
}

.field :deep(.input),
.field .input {
  min-height: 44px;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: rgba(255, 255, 255, 0.92);
  font-size: 0.9375rem;
  font-weight: 500;
  color: #0f172a;
  transition:
    border-color 160ms,
    box-shadow 160ms,
    background 160ms;
}

.field .input::placeholder {
  color: #94a3b8;
  font-weight: 450;
}

.field .input:hover {
  border-color: #94a3b8;
  background: #fff;
}

.field .input:focus {
  outline: none;
  border-color: #0f766e;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16);
}

.error {
  margin: 0;
  padding: 0.55rem 0.7rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 550;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.submit {
  width: 100%;
  margin-top: 0.2rem;
  min-height: 46px;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 650;
  letter-spacing: 0.01em;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 18px rgba(15, 118, 110, 0.18);
  transition: transform 160ms var(--ease-out), box-shadow 160ms, background 160ms;
}

.submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.06), 0 12px 24px rgba(15, 118, 110, 0.24);
}

.submit:disabled {
  opacity: 0.7;
  cursor: wait;
}

.footer {
  margin: 1.25rem 0 0;
  text-align: center;
  font-size: 0.85rem;
}

.footer a {
  color: #0f766e;
  text-decoration: none;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  transition: background 160ms, color 160ms;
}

.footer a:hover {
  background: rgba(15, 118, 110, 0.08);
  text-decoration: none;
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

@keyframes drift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(-14px, 16px, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card,
  .submit,
  .bg-orb {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}
</style>
