<template>
  <div class="max-w-6xl mx-auto px-6 py-8">

    <!-- Non authentifié -->
    <div v-if="!authenticated" class="text-center py-24">
      <p class="text-4xl mb-4">📧</p>
      <h1 class="text-2xl font-bold text-white mb-2">NettoyerGmail</h1>
      <p class="text-gray-400 mb-8">Connectez-vous avec votre compte Google pour analyser votre boîte Gmail.</p>
      <a href="/auth/login"
        class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-3 rounded-xl transition text-lg">
        Se connecter avec Google
      </a>
      <p v-if="authError" class="mt-4 text-red-400 text-sm">{{ authError }}</p>
    </div>

    <!-- Chargement en cours -->
    <div v-else-if="fetching" class="text-center py-24">
      <div class="text-5xl mb-6 animate-bounce">⏳</div>
      <h2 class="text-xl font-semibold text-white mb-2">Analyse de votre boîte Gmail...</h2>
      <p class="text-gray-400 mb-6">{{ fetchProgress }} / {{ fetchTotal || '?' }} emails traités</p>
      <div class="w-64 mx-auto bg-gray-800 rounded-full h-2">
        <div class="bg-blue-500 h-2 rounded-full transition-all duration-300"
          :style="{ width: fetchTotal ? `${(fetchProgress / fetchTotal) * 100}%` : '10%' }" />
      </div>
    </div>

    <!-- Aucune donnée — premier lancement -->
    <div v-else-if="!ready" class="text-center py-24">
      <p class="text-4xl mb-4">🔍</p>
      <h2 class="text-xl font-semibold text-white mb-2">Boîte non encore analysée</h2>
      <p class="text-gray-400 mb-8">L'analyse récupère les métadonnées de tous vos emails (sans télécharger les corps).</p>
      <button @click="startFetch"
        class="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-3 rounded-xl transition">
        Analyser ma boîte Gmail
      </button>
    </div>

    <!-- Dashboard des groupes -->
    <div v-else>
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-white">Groupes d'emails</h1>
          <p class="text-gray-400 text-sm mt-1">{{ groups.length }} groupes • {{ totalEmails.toLocaleString() }} emails au total</p>
        </div>
        <div class="flex gap-3">
          <select v-model="filterCategory"
            class="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500">
            <option value="">Tous les types</option>
            <option value="newsletter">Newsletters</option>
            <option value="commercial">Commercial</option>
            <option value="social">Réseaux sociaux</option>
            <option value="admin">Administratif</option>
            <option value="autre">Autre</option>
          </select>
          <button @click="refreshData"
            class="text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-2 rounded-lg text-sm transition">
            🔄 Rafraîchir
          </button>
        </div>
      </div>

      <!-- Grille des groupes -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <RouterLink v-for="g in filteredGroups" :key="g.group_id"
          :to="`/groups/${g.group_id}`"
          class="group bg-gray-900 border border-gray-800 hover:border-gray-600 rounded-xl p-5 transition cursor-pointer flex flex-col gap-3">

          <!-- Badge catégorie + décision -->
          <div class="flex items-center justify-between">
            <span :class="categoryBadge(g.category)" class="text-xs font-medium px-2 py-0.5 rounded-full">
              {{ categoryLabel(g.category) }}
            </span>
            <span v-if="g.decision && g.decision !== 'keep'" :class="decisionBadge(g.decision)" class="text-xs font-medium px-2 py-0.5 rounded-full">
              {{ decisionLabel(g.decision) }}
            </span>
            <span v-else-if="g.decision === 'keep'" class="text-xs text-green-400 font-medium">✓ Conservé</span>
          </div>

          <!-- Thème -->
          <h3 class="font-semibold text-white group-hover:text-blue-400 transition leading-snug">{{ g.theme }}</h3>

          <!-- Expéditeurs -->
          <p class="text-xs text-gray-500 truncate">{{ g.sample_senders.join(' • ') }}</p>

          <!-- Stats -->
          <div class="flex items-center justify-between text-sm mt-auto pt-2 border-t border-gray-800">
            <span class="text-gray-300 font-medium">{{ g.count.toLocaleString() }} emails</span>
            <span class="text-gray-500">{{ g.size_mb }} Mo</span>
          </div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useDecisionsStore } from '../stores/decisions.js'

const store = useDecisionsStore()

const authenticated = ref(false)
const authError = ref('')
const ready = ref(false)
const fetching = ref(false)
const fetchProgress = ref(0)
const fetchTotal = ref(0)
const groups = ref([])
const filterCategory = ref('')
let pollInterval = null

const totalEmails = computed(() => groups.value.reduce((s, g) => s + g.count, 0))

const filteredGroups = computed(() =>
  filterCategory.value
    ? groups.value.filter(g => g.category === filterCategory.value)
    : groups.value
)

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  if (params.get('error')) authError.value = params.get('error')

  const { data: status } = await axios.get('/auth/status')
  authenticated.value = status.authenticated
  if (authenticated.value) {
    await store.load()
    await loadGroups()
  }
})

onUnmounted(() => clearInterval(pollInterval))

async function loadGroups() {
  const { data } = await axios.get('/api/groups')
  if (data.ready) {
    ready.value = true
    fetching.value = false
    groups.value = data.groups.map(g => ({ ...g, decision: store.decisions[g.group_id] }))
    clearInterval(pollInterval)
  } else if (data.fetching) {
    fetching.value = true
    fetchProgress.value = data.progress || 0
    fetchTotal.value = data.total || 0
    startPolling()
  }
}

async function startFetch() {
  await axios.post('/api/groups/fetch')
  fetching.value = true
  startPolling()
}

function startPolling() {
  clearInterval(pollInterval)
  pollInterval = setInterval(async () => {
    const { data } = await axios.get('/api/groups/fetch-status')
    fetchProgress.value = data.progress || 0
    fetchTotal.value = data.total || 0
    if (!data.running && data.ready) {
      await loadGroups()
    } else if (data.error) {
      fetching.value = false
      clearInterval(pollInterval)
    }
  }, 2000)
}

async function refreshData() {
  ready.value = false
  await axios.get('/api/groups?refresh=true')
  await startFetch()
}

const categoryColors = {
  newsletter: 'bg-yellow-900 text-yellow-300',
  commercial: 'bg-cyan-900 text-cyan-300',
  social: 'bg-blue-900 text-blue-300',
  admin: 'bg-green-900 text-green-300',
  autre: 'bg-gray-700 text-gray-300',
}
const categoryLabels = {
  newsletter: 'Newsletter', commercial: 'Commercial',
  social: 'Réseau social', admin: 'Administratif', autre: 'Autre',
}
function categoryBadge(cat) { return categoryColors[cat] || categoryColors.autre }
function categoryLabel(cat) { return categoryLabels[cat] || cat }

function decisionBadge(d) {
  return d === 'trash' ? 'bg-red-900 text-red-300' : 'bg-indigo-900 text-indigo-300'
}
function decisionLabel(d) { return d === 'trash' ? '🗑 Supprimer' : '📁 Archiver' }
</script>
