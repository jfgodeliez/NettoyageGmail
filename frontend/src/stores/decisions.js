import { defineStore } from 'pinia'
import axios from 'axios'

export const useDecisionsStore = defineStore('decisions', {
  state: () => ({
    decisions: {},   // { group_id: action }
  }),
  getters: {
    count: (s) => Object.keys(s.decisions).length,
    activeCount: (s) => Object.values(s.decisions).filter(a => a !== 'keep').length,
  },
  actions: {
    async load() {
      const { data } = await axios.get('/api/decisions')
      this.decisions = data
    },
    async setDecision(groupId, action) {
      await axios.post('/api/decisions', { group_id: groupId, action })
      this.decisions[groupId] = action
    },
    async clear() {
      await axios.delete('/api/decisions')
      this.decisions = {}
    },
  },
})
