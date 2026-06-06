<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-950 px-4">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-8">
        <p class="text-5xl mb-3">📧</p>
        <h1 class="text-2xl font-bold text-white">NettoyerGmail</h1>
        <p class="text-gray-500 text-sm mt-1">Accès sécurisé</p>
      </div>

      <!-- Formulaire -->
      <form @submit.prevent="submit" class="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div>
          <label class="block text-sm text-gray-400 mb-1.5">Mot de passe</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            autofocus
            placeholder="••••••••"
            class="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-600 transition"
            :class="error ? 'border-red-600' : ''"
          />
          <p v-if="error" class="text-red-400 text-xs mt-1.5">{{ error }}</p>
        </div>

        <button
          type="submit"
          :disabled="loading || !password"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition text-sm">
          <span v-if="loading" class="animate-pulse">Vérification...</span>
          <span v-else>Se connecter</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!password.value) return
  loading.value = true
  error.value = ''
  try {
    await axios.post('/auth/app-login', { password: password.value }, { withCredentials: true })
    await router.push('/')
  } catch (e) {
    error.value = e.response?.status === 401
      ? 'Mot de passe incorrect'
      : 'Erreur serveur, réessayez'
    password.value = ''
  } finally {
    loading.value = false
  }
}
</script>
