<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold text-white mb-1">Révision des actions</h1>
    <p class="text-gray-400 text-sm mb-8">Vérifiez vos décisions avant de les appliquer.</p>

    <div v-if="!store.activeCount && !individualCount" class="text-center py-16 text-gray-500">
      Aucune action planifiée. <RouterLink to="/" class="text-blue-400 hover:underline">Retour au dashboard</RouterLink>
    </div>

    <template v-else-if="store.activeCount || individualCount">
      <!-- Tableau récapitulatif -->
      <div class="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden mb-6">
        <table class="w-full text-sm">
          <thead class="bg-gray-800 text-gray-400 text-xs uppercase">
            <tr>
              <th class="px-4 py-3 text-left">Groupe</th>
              <th class="px-4 py-3 text-center">Action</th>
              <th class="px-4 py-3 text-right">Emails</th>
              <th class="px-4 py-3 text-right w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-800">
            <tr v-for="g in actionableGroups" :key="g.group_id" class="hover:bg-gray-800/50">
              <td class="px-4 py-3 text-white font-medium">{{ g.theme }}</td>
              <td class="px-4 py-3 text-center">
                <span :class="actionBadge(g.decision)" class="text-xs font-semibold px-2 py-1 rounded-full">
                  {{ actionLabel(g.decision) }}
                </span>
              </td>
              <td class="px-4 py-3 text-right text-gray-300">{{ g.count.toLocaleString() }}</td>
              <td class="px-4 py-3 text-right">
                <button @click="store.setDecision(g.group_id, 'keep')"
                  class="text-gray-600 hover:text-red-400 text-lg leading-none transition" title="Annuler">✕</button>
              </td>
            </tr>
          </tbody>
          <tfoot class="bg-gray-800/50">
            <tr>
              <td colspan="2" class="px-4 py-3 text-gray-400 text-sm">Total</td>
              <td class="px-4 py-3 text-right font-bold text-white">{{ totalAffected.toLocaleString() }}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Emails marqués individuellement -->
      <div v-if="individualTrashCount || individualKeepCount"
        class="mb-6 p-4 bg-gray-900 border border-gray-700 rounded-xl space-y-1.5">
        <p v-if="individualTrashCount" class="text-red-300 text-sm">
          🗑 <strong>{{ individualTrashCount }}</strong> email(s) marqué(s) individuellement pour suppression
          <span class="text-gray-500 text-xs ml-1">(s'ajoutent aux décisions de groupe)</span>
        </p>
        <p v-if="individualKeepCount" class="text-green-300 text-sm">
          ✓ <strong>{{ individualKeepCount }}</strong> email(s) protégé(s) individuellement
          <span class="text-gray-500 text-xs ml-1">(exclus des suppressions de groupe)</span>
        </p>
      </div>

      <!-- Mode dry-run -->
      <div class="flex items-center gap-3 mb-6 p-4 bg-yellow-950 border border-yellow-800 rounded-xl">
        <input id="dryrun" type="checkbox" v-model="dryRun" class="w-4 h-4 accent-yellow-500" />
        <label for="dryrun" class="text-yellow-300 text-sm font-medium cursor-pointer">
          Mode simulation (dry-run) — aucune modification réelle
        </label>
      </div>

      <!-- Résultat -->
      <div v-if="result" class="mb-6 p-4 rounded-xl border"
        :class="result.errors > 0 ? 'bg-red-950 border-red-800' : 'bg-green-950 border-green-800'">
        <p class="font-semibold" :class="result.errors > 0 ? 'text-red-300' : 'text-green-300'">
          {{ result.dry_run ? '[Simulation] ' : '' }}{{ result.done }} email(s) traité(s), {{ result.errors }} erreur(s)
        </p>
        <p v-if="!result.dry_run && result.cache_remaining != null" class="text-xs text-gray-400 mt-1">
          Cache mis à jour — {{ result.cache_remaining.toLocaleString() }} emails restants, aucun rescan nécessaire.
        </p>
        <ul v-if="result.details?.length" class="mt-2 space-y-1">
          <li v-for="d in result.details" :key="d" class="text-xs text-gray-400">{{ d }}</li>
        </ul>
        <RouterLink v-if="!result.dry_run && result.done > 0" to="/"
          class="inline-block mt-3 text-sm text-blue-400 hover:underline">
          Retour au dashboard →
        </RouterLink>
      </div>

      <!-- Bouton exécuter -->
      <button @click="execute" :disabled="executing"
        class="w-full py-3 rounded-xl font-semibold text-white transition text-base"
        :class="dryRun ? 'bg-yellow-600 hover:bg-yellow-500' : 'bg-red-600 hover:bg-red-500'">
        <span v-if="executing" class="animate-pulse">Exécution en cours...</span>
        <span v-else-if="dryRun">Simuler les actions</span>
        <span v-else>Appliquer les actions ({{ totalAffected.toLocaleString() }} emails)</span>
      </button>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useDecisionsStore } from '../stores/decisions.js'
import { useGroupsStore } from '../stores/groups.js'

const store = useDecisionsStore()
const groupsStore = useGroupsStore()
const dryRun = ref(false)
const executing = ref(false)
const result = ref(null)
const groupsData = ref([])
const individualTrashCount = ref(0)
const individualKeepCount = ref(0)
const individualCount = computed(() => individualTrashCount.value + individualKeepCount.value)

onMounted(async () => {
  await store.load()
  const [groupsRes, countRes] = await Promise.all([
    axios.get('/api/groups', { withCredentials: true }),
    axios.get('/api/emails/decisions/count', { withCredentials: true }),
  ])
  if (groupsRes.data.ready) groupsData.value = groupsRes.data.groups
  individualTrashCount.value = countRes.data.trash_count ?? 0
  individualKeepCount.value = countRes.data.keep_count ?? 0
})

const actionableGroups = computed(() =>
  groupsData.value
    .map(g => ({ ...g, decision: store.decisions[g.group_id] }))
    .filter(g => g.decision && g.decision !== 'keep')
)

const totalAffected = computed(() => actionableGroups.value.reduce((s, g) => s + g.count, 0))

async function execute() {
  executing.value = true
  result.value = null
  try {
    const { data } = await axios.post('/api/execute', { dry_run: dryRun.value })
    result.value = data
    if (!dryRun.value && data.done > 0) {
      individualTrashCount.value = 0
      individualKeepCount.value = 0
      await groupsStore.load()
      groupsData.value = groupsStore.groups
    }
  } catch (e) {
    result.value = { done: 0, errors: 1, details: [e.response?.data?.detail || e.message] }
  } finally {
    executing.value = false
  }
}

function actionBadge(d) {
  return d === 'trash' ? 'bg-red-900 text-red-300' : 'bg-indigo-900 text-indigo-300'
}
function actionLabel(d) { return d === 'trash' ? '🗑 Supprimer' : '📁 Archiver' }
</script>
