<template>
  <div class="home">
    <div class="hero">
      <div class="hero-icon">🐙</div>
      <h1>SoccerOctopus</h1>
      <p class="tagline">
        A swarm of AI agents analyses <strong>SofaScore statistics</strong>,
        <strong>YouTube video intelligence</strong>, <strong>team form</strong>,
        and <strong>tactical profiles</strong> to predict every match of the
        <strong>FIFA World Cup 2026</strong>.
      </p>
    </div>

    <div class="cards">
      <div class="card" @click="$router.push('/groups')">
        <div class="card-icon">🏆</div>
        <h3>WC 2026 Groups</h3>
        <p>Browse the 12 groups and team ELO ratings</p>
      </div>
      <div class="card" @click="$router.push('/predict')">
        <div class="card-icon">⚡</div>
        <h3>Predict a Match</h3>
        <p>Run the swarm on any fixture — get instant probabilities</p>
      </div>
      <div class="card" @click="$router.push('/tournament')">
        <div class="card-icon">🌍</div>
        <h3>Full Tournament</h3>
        <p>Simulate the entire bracket from groups to the final</p>
      </div>
      <div class="card markets-card" @click="$router.push('/markets')">
        <div class="card-icon">📈</div>
        <h3>Prediction Markets</h3>
        <p>Generate Kalshi & Polymarket contracts — match props and tournament futures</p>
      </div>
    </div>

    <div class="swarm-info">
      <h2>How the Swarm Works</h2>
      <div class="agents-grid">
        <div class="agent-card" v-for="a in agents" :key="a.name">
          <span class="agent-icon">{{ a.icon }}</span>
          <div>
            <strong>{{ a.name }}</strong>
            <p>{{ a.desc }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const agents = [
  { icon: '📊', name: 'Statistical Agent (weight 1.8×)', desc: 'ELO ratings, Poisson model, SofaScore attack/defence stats, H2H records' },
  { icon: '🎥', name: 'Video Intelligence Agent (weight 1.0×)', desc: 'YouTube highlights engagement ratios, title sentiment, tactical momentum scores' },
  { icon: '🔥', name: 'Recent Form Agent (weight 1.3×)', desc: 'Points earned in last 10 official matches, goal rates adjusted by form trajectory' },
  { icon: '🧠', name: 'Tactical Agent (weight 1.2×)', desc: 'Style-matchup matrix (high-press vs counter, tiki-taka vs defensive block, etc.)' },
  { icon: '🤝', name: 'Aggregator Agent', desc: 'Confidence-weighted ensemble + LLM-synthesised narrative and key factor extraction' },
]
</script>

<style scoped>
.home { display: flex; flex-direction: column; gap: 48px; }

.hero { text-align: center; padding: 48px 0 24px; }
.hero-icon { font-size: 64px; margin-bottom: 16px; }
.hero h1 { font-size: 48px; font-weight: 800; color: #e2b714; margin-bottom: 16px; }
.tagline { font-size: 16px; color: #a0aec0; max-width: 640px; margin: 0 auto; line-height: 1.7; }
.tagline strong { color: #e0e0e0; }

.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 28px;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s;
  text-align: center;
}
.card:hover { transform: translateY(-4px); border-color: #e2b714; }
.markets-card:hover { border-color: #4ade80; }
.markets-card h3 { color: #4ade80; }
.card-icon { font-size: 40px; margin-bottom: 12px; }
.card h3 { color: #e2b714; margin-bottom: 8px; }
.card p { color: #8888aa; font-size: 14px; }

.swarm-info h2 { color: #e2b714; margin-bottom: 20px; font-size: 22px; }
.agents-grid { display: flex; flex-direction: column; gap: 12px; }
.agent-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: #16213e;
  border-radius: 10px;
  padding: 16px 20px;
  border: 1px solid #0f3460;
}
.agent-icon { font-size: 28px; flex-shrink: 0; }
.agent-card strong { color: #e0e0e0; font-size: 15px; }
.agent-card p { color: #8888aa; font-size: 13px; margin-top: 4px; }
</style>
