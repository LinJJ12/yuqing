<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { fetchHealthReady, logoutApi } from './api/client'
import { clearSession, getUsername } from './lib/auth'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppTopBar from './components/layout/AppTopBar.vue'

const route = useRoute()
const router = useRouter()

const backendOk = ref(null)
const refreshing = ref(false)
const loggingOut = ref(false)
const username = ref('')

const isPublic = computed(() => route.meta.layout === 'public')

watch(
  () => [route.fullPath, route.meta.layout],
  () => {
    username.value = getUsername()
  },
  { immediate: true },
)

async function checkBackend() {
  refreshing.value = true
  backendOk.value = null
  try {
    const res = await fetchHealthReady()
    backendOk.value = !!res.ok
  } catch {
    backendOk.value = false
  } finally {
    refreshing.value = false
  }
}

async function onLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logoutApi()
  } catch {
    /* ignore */
  } finally {
    clearSession()
    loggingOut.value = false
    await router.push({ name: 'login' })
  }
}

onMounted(checkBackend)
</script>

<template>
  <div v-if="isPublic" class="public-shell">
    <RouterView v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </RouterView>
  </div>
  <div v-else class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopBar
        :backend-ok="backendOk"
        :refreshing="refreshing"
        :username="username"
        :logging-out="loggingOut"
        @refresh="checkBackend"
        @logout="onLogout"
      />
      <main id="main" class="app-content">
        <RouterView v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.public-shell {
  height: 100%;
  overflow: auto;
}
</style>
