<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { login as loginRequest } from '../api/client'
import { setSession } from '../lib/auth'
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
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const safe =
      redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : ''
    await router.replace(safe || '/overview')
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
        <img :src="logoUrl" alt="" class="brand-logo" width="36" height="36" />
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
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background:
    radial-gradient(900px 420px at 20% 0%, rgba(15, 118, 110, 0.1), transparent 55%),
    linear-gradient(180deg, #f8fafc, var(--bg-base));
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 1.6rem 1.5rem 1.35rem;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: inherit;
  margin-bottom: 1.35rem;
}

.brand-logo {
  border-radius: 8px;
}

.brand-name {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-sub {
  margin-top: 0.1rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.hint {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.form {
  display: grid;
  gap: 0.85rem;
  margin-top: 1.25rem;
}

.error {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-destructive);
}

.submit {
  width: 100%;
  margin-top: 0.25rem;
  min-height: 40px;
}

.footer {
  margin: 1.1rem 0 0;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.footer a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.footer a:hover {
  text-decoration: underline;
}
</style>
