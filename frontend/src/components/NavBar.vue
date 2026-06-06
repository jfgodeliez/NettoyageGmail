<template>
  <nav class="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
    <RouterLink to="/" class="flex items-center gap-2 text-white font-semibold text-lg hover:text-blue-400 transition">
      <span>📧</span> NettoyerGmail
    </RouterLink>
    <div class="flex items-center gap-4">
      <RouterLink v-if="store.activeCount > 0" to="/review"
        class="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition">
        Réviser les actions
        <span class="bg-blue-400 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">{{ store.activeCount }}</span>
      </RouterLink>
      <button @click="logout" class="text-gray-400 hover:text-red-400 text-sm transition">
        Déconnexion
      </button>
    </div>
  </nav>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useDecisionsStore } from '../stores/decisions.js'

const store = useDecisionsStore()
const router = useRouter()

onMounted(async () => {
  try {
    const { data } = await axios.get('/auth/status', { withCredentials: true })
    if (data.authenticated) store.load()
  } catch { /* non connecté à Gmail, pas grave */ }
})

async function logout() {
  await axios.post('/auth/app-logout', {}, { withCredentials: true })
  store.decisions = {}
  router.push('/login')
}
</script>
