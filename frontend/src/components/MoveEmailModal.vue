<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
    <div class="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md shadow-2xl">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
        <h3 class="font-semibold text-white">Déplacer l'email</h3>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-300 text-xl">✕</button>
      </div>

      <div class="px-6 py-4 space-y-4">
        <!-- Sujet de l'email -->
        <p class="text-sm text-gray-400 truncate">{{ email.subject }}</p>

        <!-- Recherche + sélecteur de groupe existant -->
        <div>
          <label class="block text-xs text-gray-500 mb-1">Déplacer vers un groupe existant</label>
          <!-- Filtre de recherche -->
          <div class="relative mb-1.5">
            <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">🔍</span>
            <input v-model="groupSearch" placeholder="Filtrer les groupes..."
              class="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg pl-7 pr-3 py-1.5 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-600" />
          </div>
          <!-- Liste filtrée (max-height scrollable) -->
          <div class="bg-gray-800 border border-gray-700 rounded-lg max-h-40 overflow-y-auto divide-y divide-gray-700">
            <button v-for="g in filteredGroupList" :key="g.group_id"
              @click="selectedGroupId = g.group_id"
              :disabled="g.group_id === currentGroupId"
              class="w-full text-left px-3 py-2 text-sm transition flex items-center justify-between"
              :class="g.group_id === selectedGroupId
                ? 'bg-blue-900/50 text-blue-300'
                : g.group_id === currentGroupId
                  ? 'text-gray-600 cursor-not-allowed'
                  : 'text-gray-300 hover:bg-gray-700'">
              <span>{{ g.is_custom ? '★ ' : '' }}{{ g.theme }}</span>
              <span v-if="g.group_id === currentGroupId" class="text-xs text-gray-600">actuel</span>
              <span v-else-if="g.group_id === selectedGroupId" class="text-xs text-blue-400">✓</span>
            </button>
            <p v-if="filteredGroupList.length === 0" class="px-3 py-2 text-xs text-gray-600 italic">
              Aucun groupe correspondant
            </p>
          </div>
        </div>

        <!-- Séparateur -->
        <div class="flex items-center gap-3 text-gray-600 text-xs">
          <div class="flex-1 border-t border-gray-800"></div>
          ou créer
          <div class="flex-1 border-t border-gray-800"></div>
        </div>

        <!-- Créer un nouveau groupe -->
        <div>
          <label class="block text-xs text-gray-500 mb-1">Nouveau groupe custom</label>
          <div class="flex gap-2">
            <input v-model="newGroupName" @keyup.enter="createAndMove"
              placeholder="Nom du groupe (ex: Famille)"
              class="flex-1 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-600" />
            <select v-model="newGroupCategory"
              class="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-2 py-2">
              <option value="autre">Autre</option>
              <option value="perso">Personnel</option>
              <option value="admin">Admin</option>
              <option value="commercial">Commercial</option>
              <option value="newsletter">Newsletter</option>
              <option value="social">Social</option>
            </select>
          </div>
        </div>

        <!-- Erreur -->
        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>
      </div>

      <!-- Actions -->
      <div class="px-6 py-4 border-t border-gray-800 flex gap-3 justify-end">
        <button @click="$emit('close')"
          class="text-gray-400 hover:text-white text-sm px-4 py-2 rounded-lg transition">
          Annuler
        </button>
        <!-- Déplacer vers groupe existant -->
        <button v-if="selectedGroupId && !newGroupName" @click="moveToExisting"
          :disabled="saving"
          class="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition disabled:opacity-50">
          {{ saving ? 'Déplacement...' : 'Déplacer' }}
        </button>
        <!-- Créer + déplacer -->
        <button v-else-if="newGroupName" @click="createAndMove"
          :disabled="saving"
          class="bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition disabled:opacity-50">
          {{ saving ? 'Création...' : 'Créer et déplacer' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({ email: Object, currentGroupId: Number })
const emit = defineEmits(['close', 'moved'])

const allGroups = ref([])
const selectedGroupId = ref('')
const newGroupName = ref('')
const newGroupCategory = ref('autre')
const saving = ref(false)
const error = ref('')
const groupSearch = ref('')

const filteredGroupList = computed(() => {
  if (!groupSearch.value) return allGroups.value
  const q = groupSearch.value.toLowerCase()
  return allGroups.value.filter(g => g.theme.toLowerCase().includes(q))
})

onMounted(async () => {
  const { data } = await axios.get('/api/groups/list', { withCredentials: true })
  allGroups.value = data
})

async function moveToExisting() {
  if (!selectedGroupId.value) return
  saving.value = true
  error.value = ''
  try {
    await axios.post(`/api/emails/${props.email.msg_id}/move`, { target_group_id: selectedGroupId.value }, { withCredentials: true })
    emit('moved', { msg_id: props.email.msg_id, group_id: selectedGroupId.value })
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du déplacement'
  } finally {
    saving.value = false
  }
}

async function createAndMove() {
  if (!newGroupName.value.trim()) return
  saving.value = true
  error.value = ''
  try {
    const { data: group } = await axios.post('/api/groups', {
      theme: newGroupName.value.trim(),
      category: newGroupCategory.value,
    }, { withCredentials: true })
    await axios.post(`/api/emails/${props.email.msg_id}/move`, { target_group_id: group.group_id }, { withCredentials: true })
    emit('moved', { msg_id: props.email.msg_id, group_id: group.group_id, new_group: group })
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors de la création'
  } finally {
    saving.value = false
  }
}
</script>
