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
    <div class="login-card">
      <RouterLink class="brand" to="/">
        <img :src="logoUrl" alt="" class="brand-logo" width="40" height="40" />
        <div>
          <div class="brand-name">知微</div>
          <div class="brand-sub">本地观众反馈分析工作台</div>
        </div>
      </RouterLink>

      <h1 class="title">登录</h1>
      <p class="hint">使用本地管理员账号进入工作台</p>

      <form class="form" @submit.prevent="onSubmit">
        <label class="field">
          <span>用户名</span>
          <input
            v-model="username"
            class="input"
            type="text"
            autocomplete="username"
            name="username"
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
            required
          />
        </label>

        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <button class="btn btn-primary submit" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="footer">
        <RouterLink to="/">返回首页</RouterLink>
      </p>
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
  background: #ffffff;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 1.85rem 1.65rem 1.5rem;
  background: #ffffff;
  border: 1px solid #94a3b8;
  border-radius: 14px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.05),
    0 18px 40px rgba(15, 23, 42, 0.1);
  animation: fade-up 0.5s var(--ease-out) both;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  text-decoration: none;
  color: inherit;
  margin-bottom: 1.45rem;
}

.brand-logo {
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.brand-name {
  font-family: 'Songti SC', 'SimSun', 'STSong', 'Noto Serif SC', 'Source Han Serif SC', serif;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #0b1220;
}

.brand-sub {
  margin-top: 0.15rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
}

.title {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 720;
  letter-spacing: -0.02em;
  color: #0b1220;
}

.hint {
  margin: 0.4rem 0 0;
  font-size: 0.875rem;
  font-weight: 500;
  color: #475569;
}

.form {
  display: grid;
  gap: 0.9rem;
  margin-top: 1.35rem;
}

.error {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-destructive);
}

.submit {
  width: 100%;
  margin-top: 0.3rem;
  min-height: 42px;
  border-radius: 8px;
  transition: transform 160ms var(--ease-out), box-shadow 160ms;
}

.submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.2);
}

.footer {
  margin: 1.2rem 0 0;
  text-align: center;
  font-size: 0.85rem;
  color: #64748b;
}

.footer a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}

.footer a:hover {
  text-decoration: underline;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card,
  .submit {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}
</style>
