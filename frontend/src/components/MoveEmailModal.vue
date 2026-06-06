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

        <!-- Sélecteur de groupe existant -->
        <div>
          <label class="block text-xs text-gray-500 mb-1">Déplacer vers un groupe existant</label>
          <select v-model="selectedGroupId"
            class="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500">
            <option value="">— Choisir un groupe —</option>
            <option v-for="g in allGroups" :key="g.group_id" :value="g.group_id"
              :disabled="g.group_id === currentGroupId">
              {{ g.is_custom ? '★ ' : '' }}{{ g.theme }}
              {{ g.group_id === currentGroupId ? '(groupe actuel)' : '' }}
            </option>
          </select>
        </div>

        <!-- Séparateur -->
        <div class="flex items-center gap-3 text-gray-600 text-xs">
          <div class="flex-1 border-t border-gray-800"></div>
          ou
          <div class="flex-1 border-t border-gray-800"></div>
        </div>

        <!-- Créer un nouveau groupe -->
        <div>
          <label class="block text-xs text-gray-500 mb-1">Créer un nouveau groupe custom</label>
          <div class="flex gap-2">
            <input v-model="newGroupName" @keyup.enter="createAndMove"
              placeholder="Nom du groupe (ex: Famille)"
              class="flex-1 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-600" />
            <select v-model="newGroupCategory"
              class="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-2 py-2">
              <option value="autre">Autre</option>
              <option value="perso">Personnel</option>
              <option value="admin">Administratif</option>
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
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({ email: Object, currentGroupId: Number })
const emit = defineEmits(['close', 'moved'])

const allGroups = ref([])
const selectedGroupId = ref('')
const newGroupName = ref('')
const newGroupCategory = ref('autre')
const saving = ref(false)
const error = ref('')

onMounted(async () => {
  const { data } = await axios.get('/api/groups/list')
  allGroups.value = data
})

async function moveToExisting() {
  if (!selectedGroupId.value) return
  saving.value = true
  error.value = ''
  try {
    await axios.post(`/api/emails/${props.email.msg_id}/move`, { target_group_id: selectedGroupId.value })
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
    })
    await axios.post(`/api/emails/${props.email.msg_id}/move`, { target_group_id: group.group_id })
    emit('moved', { msg_id: props.email.msg_id, group_id: group.group_id, new_group: group })
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors de la création'
  } finally {
    saving.value = false
  }
}
</script>
