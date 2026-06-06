<template>
  <div class="h-[calc(100vh-57px)] flex flex-col">
    <!-- Barre d'actions -->
    <div class="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-4 flex-shrink-0">
      <RouterLink to="/" class="text-gray-400 hover:text-white text-sm transition">← Retour</RouterLink>
      <div class="flex-1 min-w-0">
        <h2 class="font-semibold text-white truncate">{{ group?.theme }}</h2>
        <p class="text-xs text-gray-400">{{ group?.total?.toLocaleString() }} emails • page {{ page }}</p>
      </div>
      <!-- Actions groupe -->
      <div class="flex gap-2">
        <button @click="setDecision('keep')"
          :class="decision === 'keep' ? 'ring-2 ring-green-500' : ''"
          class="bg-green-900 hover:bg-green-800 text-green-300 text-sm font-medium px-3 py-1.5 rounded-lg transition">
          ✓ Conserver
        </button>
        <button @click="setDecision('archive')"
          :class="decision === 'archive' ? 'ring-2 ring-indigo-500' : ''"
          class="bg-indigo-900 hover:bg-indigo-800 text-indigo-300 text-sm font-medium px-3 py-1.5 rounded-lg transition">
          📁 Archiver tout
        </button>
        <button @click="setDecision('trash')"
          :class="decision === 'trash' ? 'ring-2 ring-red-500' : ''"
          class="bg-red-900 hover:bg-red-800 text-red-300 text-sm font-medium px-3 py-1.5 rounded-lg transition">
          🗑 Supprimer tout
        </button>
      </div>
    </div>

    <!-- Corps : liste + aperçu -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Liste emails -->
      <div class="w-full md:w-1/2 lg:w-2/5 flex flex-col overflow-hidden border-r border-gray-800">
        <div v-if="loading" class="flex-1 flex items-center justify-center">
          <span class="text-gray-500 animate-pulse">Chargement...</span>
        </div>
        <ul v-else class="flex-1 overflow-y-auto divide-y divide-gray-800">
          <li v-for="email in emails" :key="email.msg_id"
            @click="selectedEmail = email"
            :class="selectedEmail?.msg_id === email.msg_id ? 'bg-blue-950 border-l-2 border-blue-500' : 'hover:bg-gray-800'"
            class="px-4 py-3 cursor-pointer transition">
            <p class="text-sm font-medium text-white truncate">{{ email.subject || '(sans objet)' }}</p>
            <p class="text-xs text-gray-400 truncate mt-0.5">{{ email.sender }}</p>
            <p class="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
              <span>{{ email.date?.slice(0, 16) }}</span>
              <span v-if="email.is_newsletter" class="text-yellow-600">Newsletter</span>
              <span class="ml-auto">{{ email.size_kb }} Ko</span>
            </p>
          </li>
        </ul>
        <!-- Pagination -->
        <div class="border-t border-gray-800 px-4 py-2 flex items-center justify-between flex-shrink-0">
          <button @click="prevPage" :disabled="page <= 1"
            class="text-sm text-gray-400 hover:text-white disabled:opacity-30 transition">← Préc.</button>
          <span class="text-xs text-gray-500">{{ page }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="page >= totalPages"
            class="text-sm text-gray-400 hover:text-white disabled:opacity-30 transition">Suiv. →</button>
        </div>
      </div>

      <!-- Aperçu email -->
      <div class="hidden md:flex flex-1 p-4">
        <div v-if="!selectedEmail" class="flex-1 flex items-center justify-center">
          <p class="text-gray-600 text-sm">Cliquez sur un email pour voir l'aperçu</p>
        </div>
        <EmailPreview v-else :email="selectedEmail" @close="selectedEmail = null" class="flex-1" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useDecisionsStore } from '../stores/decisions.js'
import EmailPreview from '../components/EmailPreview.vue'

const route = useRoute()
const store = useDecisionsStore()

const group = ref(null)
const emails = ref([])
const loading = ref(false)
const selectedEmail = ref(null)
const page = ref(1)
const perPage = 50

const decision = computed({
  get: () => store.decisions[Number(route.params.id)],
  set: (val) => store.setDecision(Number(route.params.id), val),
})

const totalPages = computed(() => Math.ceil((group.value?.total || 0) / perPage))

onMounted(() => loadPage())

watch(page, () => {
  selectedEmail.value = null
  loadPage()
})

async function loadPage() {
  loading.value = true
  try {
    const { data } = await axios.get(`/api/groups/${route.params.id}/emails`, {
      params: { page: page.value, per_page: perPage },
    })
    group.value = data
    emails.value = data.emails
  } finally {
    loading.value = false
  }
}

async function setDecision(action) {
  await store.setDecision(Number(route.params.id), action)
}

function prevPage() { if (page.value > 1) page.value-- }
function nextPage() { if (page.value < totalPages.value) page.value++ }
</script>
