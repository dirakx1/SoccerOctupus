<template>
  <div>
    <h1 class="title">🏆 FIFA World Cup 2026 — Groups</h1>
    <p class="subtitle">48 teams across 12 groups. Hosted in USA 🇺🇸 · Canada 🇨🇦 · Mexico 🇲🇽</p>

    <div v-if="loading" class="loading">Loading groups…</div>
    <div v-else class="groups-grid">
      <div class="group-card" v-for="(teams, gLetter) in groups" :key="gLetter">
        <div class="group-header">Group {{ gLetter }}</div>
        <div class="team-row" v-for="t in sortedTeams(teams)" :key="t.team">
          <span class="team-name">{{ t.team }}</span>
          <span class="elo-badge">ELO {{ t.elo }}</span>
          <span class="rank-badge">#{{ t.rank }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const groups = ref({})
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await axios.get('/api/predictions/groups')
    groups.value = res.data.groups
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

const sortedTeams = (teams) => [...teams].sort((a, b) => b.elo - a.elo)
</script>

<style scoped>
.title { color: #e2b714; font-size: 26px; margin-bottom: 8px; }
.subtitle { color: #8888aa; font-size: 14px; margin-bottom: 28px; }
.loading { color: #a0aec0; }

.groups-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.group-card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 10px;
  overflow: hidden;
}
.group-header {
  background: #0f3460;
  color: #e2b714;
  font-weight: 700;
  font-size: 15px;
  padding: 10px 14px;
  letter-spacing: 1px;
}
.team-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-bottom: 1px solid #0f1e35;
}
.team-row:last-child { border-bottom: none; }
.team-name { flex: 1; font-size: 13px; color: #e0e0e0; }
.elo-badge {
  font-size: 11px;
  background: #1e3a5f;
  color: #a0c0ff;
  border-radius: 4px;
  padding: 2px 6px;
}
.rank-badge {
  font-size: 11px;
  color: #8888aa;
  min-width: 30px;
  text-align: right;
}
</style>
