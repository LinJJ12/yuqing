<script setup>
import { onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import { fetchHealthReady } from './api/client'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppTopBar from './components/layout/AppTopBar.vue'

const backendOk = ref(null)
const refreshing = ref(false)

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

onMounted(checkBackend)
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopBar
        :backend-ok="backendOk"
        :refreshing="refreshing"
        @refresh="checkBackend"
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
