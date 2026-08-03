import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { setUnauthorizedHandler } from './api/client'
import { router } from './router'
import './style.css'

setUnauthorizedHandler(() => {
  const current = router.currentRoute.value
  const onApp =
    current.matched.some(
      (record) => record.meta.requiresAuth || record.meta.layout === 'app',
    ) || current.meta.layout === 'app'
  if (!onApp || current.name === 'login') return
  return router.push({
    name: 'login',
    query: { redirect: current.fullPath },
  })
})

createApp(App).use(createPinia()).use(router).mount('#app')
