<template>
  <aside class="w-64 flex-shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col overflow-hidden">
    <!-- Recherche -->
    <div class="px-3 py-3 border-b border-gray-800">
      <div class="relative">
        <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-sm">🔍</span>
        <input v-model="search" placeholder="Rechercher un groupe..."
          class="w-full bg-gray-800 border border-gray-700 text-gray-200 text-xs rounded-lg pl-7 pr-3 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-600" />
      </div>
    </div>

    <!-- Liste groupes scrollable -->
    <nav class="flex-1 overflow-y-auto py-2 space-y-0.5">

      <!-- Groupe custom en tête -->
      <div v-if="customGroups.length || !search">
        <button @click="toggle('__custom__')"
          class="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-purple-400 hover:text-purple-300 uppercase tracking-wider transition">
          <span>★ Mes groupes ({{ customGroups.length }})</span>
          <span class="text-gray-600">{{ collapsed['__custom__'] ? '▶' : '▼' }}</span>
        </button>
        <div v-if="!collapsed['__custom__']">
          <RouterLink v-for="g in customGroups" :key="g.group_id"
            :to="`/groups/${g.group_id}`"
            class="flex items-center justify-between px-4 py-1.5 text-sm transition rounded-lg mx-1 group"
            :class="isActive(g.group_id)
              ? 'bg-purple-900/50 text-purple-300'
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'">
            <span class="truncate flex-1">{{ g.theme }}</span>
            <span class="flex items-center gap-1 flex-shrink-0 ml-1">
              <span v-if="g.decision && g.decision !== 'keep'" :class="decisionDot(g.decision)" class="w-1.5 h-1.5 rounded-full"></span>
              <span class="text-xs text-gray-600">{{ g.count }}</span>
            </span>
          </RouterLink>
          <button @click="$emit('create-group')"
            class="w-full text-left px-4 py-1.5 text-xs text-purple-500 hover:text-purple-300 transition">
            + Nouveau groupe
          </button>
        </div>
      </div>

      <!-- Catégories auto -->
      <div v-for="cat in autoCategories" :key="cat.key">
        <button v-if="cat.groups.length" @click="toggle(cat.key)"
          class="w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition"
          :class="cat.color + ' hover:opacity-80'">
          <span>{{ cat.label }} ({{ cat.groups.length }})</span>
          <span class="text-gray-600">{{ collapsed[cat.key] ? '▶' : '▼' }}</span>
        </button>
        <div v-if="!collapsed[cat.key]">
          <RouterLink v-for="g in cat.groups" :key="g.group_id"
            :to="`/groups/${g.group_id}`"
            class="flex items-center justify-between px-4 py-1.5 text-sm transition rounded-lg mx-1 group"
            :class="isActive(g.group_id)
              ? 'bg-blue-900/40 text-blue-300'
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'">
            <span class="truncate flex-1">{{ g.theme }}</span>
            <span class="flex items-center gap-1 flex-shrink-0 ml-1">
              <span v-if="g.decision && g.decision !== 'keep'" :class="decisionDot(g.decision)" class="w-1.5 h-1.5 rounded-full"></span>
              <span class="text-xs text-gray-600">{{ g.count }}</span>
            </span>
          </RouterLink>
        </div>
      </div>

      <!-- Aucun résultat -->
      <p v-if="search && !customGroups.length && !autoCategories.some(c => c.groups.length)"
        class="px-4 py-3 text-xs text-gray-600 italic">
        Aucun groupe correspondant
      </p>
    </nav>

    <!-- Footer : total -->
    <div class="px-3 py-2 border-t border-gray-800 text-xs text-gray-600">
      {{ groupsStore.groups.length }} groupes · {{ groupsStore.totalEmails.toLocaleString() }} emails
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useGroupsStore } from '../stores/groups.js'

defineEmits(['create-group'])

const route = useRoute()
const groupsStore = useGroupsStore()

const search = ref('')
const collapsed = ref({})

function toggle(key) {
  collapsed.value[key] = !collapsed.value[key]
}

function isActive(groupId) {
  return route.params.id && Number(route.params.id) === groupId
}

function decisionDot(d) {
  return d === 'trash' ? 'bg-red-500' : 'bg-indigo-500'
}

const filteredGroups = computed(() => {
  if (!search.value) return groupsStore.groups
  const q = search.value.toLowerCase()
  return groupsStore.groups.filter(g =>
    g.theme.toLowerCase().includes(q) ||
    g.sample_senders?.some(s => s.toLowerCase().includes(q))
  )
})

const customGroups = computed(() =>
  filteredGroups.value.filter(g => g.is_custom)
)

const CATEGORY_META = [
  { key: 'newsletter',  label: 'Newsletters',     color: 'text-yellow-600' },
  { key: 'commercial',  label: 'Commercial',       color: 'text-cyan-600'   },
  { key: 'social',      label: 'Réseaux sociaux',  color: 'text-blue-500'   },
  { key: 'admin',       label: 'Administratif',    color: 'text-green-600'  },
  { key: 'autre',       label: 'Autre',            color: 'text-gray-500'   },
]

const autoCategories = computed(() =>
  CATEGORY_META.map(meta => ({
    ...meta,
    groups: filteredGroups.value.filter(g => !g.is_custom && g.category === meta.key),
  }))
)
</script>
