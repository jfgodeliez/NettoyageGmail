<template>
  <div class="h-[calc(100vh-57px)] flex flex-col">
    <!-- Barre d'actions -->
    <div class="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-4 flex-shrink-0">
      <RouterLink to="/" class="text-gray-400 hover:text-white text-sm transition">← Retour</RouterLink>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="font-semibold text-white truncate">{{ group?.theme }}</h2>
          <span v-if="group?.is_custom" class="text-xs bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded-full">Custom</span>
        </div>
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
            :class="[
              selectedEmail?.msg_id === email.msg_id ? 'bg-blue-950 border-l-2 border-blue-500' : 'hover:bg-gray-800',
              email.email_decision === 'trash' ? 'border-l-2 border-red-700 bg-red-950/20' : '',
              email.email_decision === 'keep'  ? 'border-l-2 border-green-700 bg-green-950/10' : '',
            ]"
            class="px-4 py-3 transition group/item">
            <!-- Ligne principale cliquable -->
            <div @click="selectedEmail = email" class="cursor-pointer">
              <div class="flex items-start justify-between gap-2">
                <p class="text-sm font-medium truncate flex-1"
                  :class="email.email_decision === 'trash' ? 'text-red-400 line-through' : 'text-white'">
                  {{ email.subject || '(sans objet)' }}
                </p>
                <!-- Badges -->
                <span v-if="email.email_decision === 'trash'"
                  class="text-xs bg-red-900 text-red-300 px-1.5 py-0.5 rounded-full flex-shrink-0">🗑</span>
                <span v-else-if="email.email_decision === 'keep'"
                  class="text-xs bg-green-900 text-green-300 px-1.5 py-0.5 rounded-full flex-shrink-0">✓</span>
                <span v-else-if="email.overridden"
                  class="text-xs bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded-full flex-shrink-0">↪</span>
              </div>
              <p class="text-xs text-gray-400 truncate mt-0.5">{{ email.sender }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs text-gray-500">{{ email.date?.slice(0, 16) }}</span>
                <span v-if="email.is_newsletter" class="text-xs text-yellow-600">Newsletter</span>
                <span class="ml-auto text-xs text-gray-500">{{ email.size_kb }} Ko</span>
              </div>
            </div>
            <!-- Actions (visible au hover) -->
            <div class="mt-1.5 flex gap-2 opacity-0 group-hover/item:opacity-100 transition">
              <button @click.stop="toggleKeep(email)"
                :class="email.email_decision === 'keep'
                  ? 'text-green-400 border-green-700 hover:text-gray-300 hover:border-gray-600'
                  : 'text-green-600 hover:text-green-400 border-green-900 hover:border-green-700'"
                class="text-xs border px-2 py-0.5 rounded transition">
                {{ email.email_decision === 'keep' ? '↩ Annuler' : '✓ Conserver' }}
              </button>
              <button @click.stop="toggleTrash(email)"
                :class="email.email_decision === 'trash'
                  ? 'text-red-400 border-red-700 hover:text-gray-300 hover:border-gray-600'
                  : 'text-red-500 hover:text-red-400 border-red-900 hover:border-red-700'"
                class="text-xs border px-2 py-0.5 rounded transition">
                {{ email.email_decision === 'trash' ? '↩ Annuler' : '🗑 Supprimer' }}
              </button>
              <button @click.stop="openMoveModal(email)"
                class="text-xs text-blue-400 hover:text-blue-300 border border-blue-800 hover:border-blue-600 px-2 py-0.5 rounded transition">
                ↪ Déplacer
              </button>
              <button v-if="email.overridden" @click.stop="resetMove(email)"
                class="text-xs text-gray-400 hover:text-gray-300 border border-gray-700 px-2 py-0.5 rounded transition">
                ↩ Remettre
              </button>
            </div>
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

    <!-- Modal déplacement -->
    <MoveEmailModal
      v-if="emailToMove"
      :email="emailToMove"
      :current-group-id="Number(route.params.id)"
      @close="emailToMove = null"
      @moved="onEmailMoved"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useDecisionsStore } from '../stores/decisions.js'
import EmailPreview from '../components/EmailPreview.vue'
import MoveEmailModal from '../components/MoveEmailModal.vue'

const route = useRoute()
const store = useDecisionsStore()

const group = ref(null)
const emails = ref([])
const loading = ref(false)
const selectedEmail = ref(null)
const emailToMove = ref(null)
const page = ref(1)
const perPage = 50

const decision = computed({
  get: () => store.decisions[Number(route.params.id)],
  set: (val) => store.setDecision(Number(route.params.id), val),
})

const totalPages = computed(() => Math.ceil((group.value?.total || 0) / perPage))

onMounted(() => loadPage())
watch(page, () => { selectedEmail.value = null; loadPage() })

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

function openMoveModal(email) {
  emailToMove.value = email
}

async function resetMove(email) {
  await axios.delete(`/api/emails/${email.msg_id}/move`)
  email.overridden = false
  // Retirer l'email de la liste si c'est un groupe custom (il n'y est plus)
  if (group.value?.is_custom) {
    emails.value = emails.value.filter(e => e.msg_id !== email.msg_id)
    group.value.total = Math.max(0, group.value.total - 1)
  }
}

function onEmailMoved({ msg_id }) {
  // Marquer l'email comme déplacé ou le retirer si c'est un groupe custom
  const email = emails.value.find(e => e.msg_id === msg_id)
  if (email) {
    if (group.value?.is_custom) {
      emails.value = emails.value.filter(e => e.msg_id !== msg_id)
      group.value.total = Math.max(0, group.value.total - 1)
    } else {
      email.overridden = true
    }
  }
}

async function toggleKeep(email) {
  if (email.email_decision === 'keep') {
    await axios.delete(`/api/emails/${email.msg_id}/decision`, { withCredentials: true })
    email.email_decision = null
  } else {
    await axios.post(`/api/emails/${email.msg_id}/decision`, { action: 'keep' }, { withCredentials: true })
    email.email_decision = 'keep'
  }
}

async function toggleTrash(email) {
  if (email.email_decision === 'trash') {
    await axios.delete(`/api/emails/${email.msg_id}/decision`, { withCredentials: true })
    email.email_decision = null
  } else {
    await axios.post(`/api/emails/${email.msg_id}/decision`, { action: 'trash' }, { withCredentials: true })
    email.email_decision = 'trash'
  }
}

function prevPage() { if (page.value > 1) page.value-- }
function nextPage() { if (page.value < totalPages.value) page.value++ }
</script>
