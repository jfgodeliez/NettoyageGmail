<template>
  <div class="flex flex-col h-full bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
    <!-- Header -->
    <div class="px-5 py-4 border-b border-gray-700 flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-white truncate">{{ email.subject }}</p>
        <p class="text-xs text-gray-400 mt-0.5 truncate">{{ email.sender }}</p>
        <p class="text-xs text-gray-500 mt-0.5">{{ email.date }}</p>
      </div>
      <button @click="$emit('close')" class="text-gray-500 hover:text-gray-300 text-xl leading-none flex-shrink-0">✕</button>
    </div>

    <!-- Corps -->
    <div class="flex-1 overflow-hidden relative">
      <div v-if="loading" class="flex items-center justify-center h-full">
        <span class="text-gray-400 animate-pulse">Chargement de l'aperçu...</span>
      </div>
      <div v-else-if="error" class="flex items-center justify-center h-full">
        <span class="text-red-400 text-sm">{{ error }}</span>
      </div>
      <!-- HTML : iframe sandboxée -->
      <iframe v-else-if="mime === 'html'"
        :srcdoc="sanitizedHtml"
        sandbox=""
        class="w-full h-full border-0 bg-white"
        referrerpolicy="no-referrer"
      />
      <!-- Texte brut -->
      <pre v-else class="p-4 text-sm text-gray-300 whitespace-pre-wrap overflow-auto h-full font-mono">{{ body }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'

const props = defineProps({ email: Object })
defineEmits(['close'])

const loading = ref(false)
const error = ref(null)
const body = ref('')
const mime = ref('text')

const sanitizedHtml = ref('')

watch(() => props.email?.msg_id, async (id) => {
  if (!id) return
  loading.value = true
  error.value = null
  body.value = ''
  try {
    const { data } = await axios.get(`/api/emails/${id}/preview`)
    mime.value = data.mime
    body.value = data.content
    // Injecter un reset CSS minimal pour l'iframe
    if (data.mime === 'html') {
      sanitizedHtml.value = `
        <style>body{font-family:sans-serif;font-size:14px;padding:12px;margin:0;color:#111;background:#fff}</style>
        ${data.content}
      `
    }
  } catch (e) {
    error.value = "Impossible de charger l'aperçu"
  } finally {
    loading.value = false
  }
}, { immediate: true })
</script>
