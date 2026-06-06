<template>
  <div class="min-h-screen flex flex-col bg-gray-950">
    <NavBar v-if="!route.meta.public" />
    <div class="flex flex-1 overflow-hidden" :class="route.meta.public ? 'h-screen' : 'h-[calc(100vh-57px)]'">
      <GroupSidebar v-if="!route.meta.public" @create-group="showCreateGroupModal = true" />
      <main class="flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>

    <!-- Modal créer groupe global (déclenché depuis sidebar) -->
    <div v-if="showCreateGroupModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div class="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm shadow-2xl p-6 space-y-4">
        <h3 class="font-semibold text-white">Créer un groupe custom</h3>
        <input v-model="newGroupName" @keyup.enter="createGroup" placeholder="Nom du groupe (ex: Famille)"
          class="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:ring-purple-500 focus:border-purple-500 placeholder-gray-600" />
        <select v-model="newGroupCategory"
          class="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2">
          <option value="autre">Autre</option>
          <option value="perso">Personnel</option>
          <option value="admin">Administratif</option>
          <option value="commercial">Commercial</option>
          <option value="newsletter">Newsletter</option>
          <option value="social">Social</option>
        </select>
        <p v-if="createError" class="text-red-400 text-sm">{{ createError }}</p>
        <div class="flex gap-3 justify-end">
          <button @click="showCreateGroupModal = false" class="text-gray-400 hover:text-white text-sm px-4 py-2 rounded-lg">Annuler</button>
          <button @click="createGroup" :disabled="!newGroupName.trim()"
            class="bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50">
            Créer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import NavBar from './components/NavBar.vue'
import GroupSidebar from './components/GroupSidebar.vue'
import { useGroupsStore } from './stores/groups.js'

const route = useRoute()
const groupsStore = useGroupsStore()

const showCreateGroupModal = ref(false)
const newGroupName = ref('')
const newGroupCategory = ref('autre')
const createError = ref('')

async function createGroup() {
  if (!newGroupName.value.trim()) return
  createError.value = ''
  try {
    const { data: group } = await axios.post('/api/groups', {
      theme: newGroupName.value.trim(),
      category: newGroupCategory.value,
    }, { withCredentials: true })
    groupsStore.addGroup(group)
    newGroupName.value = ''
    newGroupCategory.value = 'autre'
    showCreateGroupModal.value = false
  } catch (e) {
    createError.value = e.response?.data?.detail || 'Erreur lors de la création'
  }
}
</script>
