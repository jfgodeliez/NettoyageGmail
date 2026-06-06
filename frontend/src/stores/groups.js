import { defineStore } from 'pinia'
import axios from 'axios'

export const useGroupsStore = defineStore('groups', {
  state: () => ({
    groups: [],
    ready: false,
    fetching: false,
    fetchProgress: 0,
    fetchTotal: 0,
    error: null,
  }),
  getters: {
    byCategory: (s) => {
      const map = {}
      for (const g of s.groups) {
        const cat = g.is_custom ? '__custom__' : g.category
        if (!map[cat]) map[cat] = []
        map[cat].push(g)
      }
      return map
    },
    totalEmails: (s) => s.groups.reduce((acc, g) => acc + g.count, 0),
  },
  actions: {
    async load() {
      try {
        const { data } = await axios.get('/api/groups', { withCredentials: true })
        if (data.ready) {
          this.groups = data.groups
          this.ready = true
          this.fetching = false
        } else if (data.fetching) {
          this.fetching = true
          this.fetchProgress = data.progress || 0
          this.fetchTotal = data.total || 0
        } else {
          this.ready = false
        }
      } catch { /* non authentifié */ }
    },
    updateDecision(groupId, action) {
      const g = this.groups.find(g => g.group_id === groupId)
      if (g) g.decision = action
    },
    addGroup(group) {
      this.groups.push({ ...group, count: 0, size_mb: 0, sample_senders: [], decision: null })
    },
  },
})
