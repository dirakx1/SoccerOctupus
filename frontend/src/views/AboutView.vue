<template>
  <div class="legal">
    <h1>About SoccerOctopus</h1>

    <section>
      <h2>What is SoccerOctopus?</h2>
      <p>
        SoccerOctopus is an open-source swarm AI engine built to predict every match of the
        FIFA World Cup 2026. A coordinated ensemble of specialised agents — each analysing a
        different data source — votes on match outcomes, and an aggregator agent synthesises
        their predictions into final probabilities, goal forecasts, and tournament simulations.
      </p>
    </section>

    <section>
      <h2>Tech Stack</h2>
      <ul>
        <li><strong>Frontend:</strong> Vue 3 + Vite, Vue Router, Clerk auth</li>
        <li><strong>Backend:</strong> Python 3.11 / 3.12, Flask 3, SQLAlchemy 2, Alembic</li>
        <li><strong>Inference:</strong> OpenAI API (GPT-4o) — aggregator narrative synthesis</li>
        <li><strong>Serving:</strong> Gunicorn (sync workers, 240 s timeout) behind Nginx</li>
        <li><strong>Simulation:</strong> Monte Carlo (Poisson goal model) as swarm fallback</li>
        <li><strong>Database:</strong> PostgreSQL via psycopg3</li>
      </ul>
    </section>

    <section>
      <h2>Swarm Agents</h2>
      <ul>
        <li>
          <strong>Statistical Agent (weight 1.8×)</strong> — ELO ratings, Poisson model,
          SofaScore attack / defence stats, head-to-head records.
        </li>
        <li>
          <strong>Video Intelligence Agent (weight 1.0×)</strong> — YouTube highlight
          engagement ratios, title sentiment, tactical momentum scores derived from
          recent match footage.
        </li>
        <li>
          <strong>Recent Form Agent (weight 1.3×)</strong> — Points earned in last 10
          official matches, goal rates adjusted by form trajectory.
        </li>
        <li>
          <strong>Tactical Agent (weight 1.2×)</strong> — Style-matchup matrix
          (high-press vs counter, tiki-taka vs defensive block, etc.).
        </li>
        <li>
          <strong>Aggregator Agent</strong> — Confidence-weighted ensemble + LLM-synthesised
          narrative and key factor extraction.
        </li>
      </ul>
    </section>

    <section>
      <h2>Data Sources</h2>
      <ul>
        <li>SofaScore — static team attack / defence ratings and ELO</li>
        <li>YouTube Data API v3 — video engagement and sentiment</li>
        <li>FotMob — xG and heatmaps</li>
        <li>FlashScore — form history and head-to-head results</li>
        <li>ESPN public API — live WC 2026 group stage results</li>
        <li>Opta — squad quality metrics</li>
      </ul>
    </section>

    <section>
      <h2>Open Source</h2>
      <p>
        SoccerOctopus is free software. The full source code is available on GitHub:
      </p>
      <p class="repo-link">
        <a href="https://github.com/dirakx1/SoccerOctupus" target="_blank" rel="noopener noreferrer">
          github.com/dirakx1/SoccerOctupus ↗
        </a>
      </p>
      <p>
        Licensed under the
        <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank" rel="noopener noreferrer">
          GNU Affero General Public License v3.0 (AGPL-3.0)
        </a>.
        Copyright © 2026 Rafael Ortiz / KubeAIllc.
      </p>
      <p>
        The AGPL-3.0 requires that any modified version deployed as a network service
        must also publish its source code. See the
        <a href="https://github.com/dirakx1/SoccerOctupus/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">
          LICENSE file
        </a>
        for the full terms.
      </p>
    </section>

    <div class="back">
      <router-link to="/">← Back to Home</router-link>
    </div>
  </div>
</template>

<style scoped>
.legal {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

h1 { color: #e2b714; font-size: 28px; }

section {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 10px;
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

h2 { color: #a0c0ff; font-size: 16px; font-weight: 700; }

p { color: #c0c0d8; font-size: 14px; line-height: 1.7; margin: 0; }

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

li { color: #c0c0d8; font-size: 14px; line-height: 1.7; padding-left: 16px; position: relative; }
li::before { content: '›'; position: absolute; left: 0; color: #e2b714; }
li strong { color: #e0e0e0; }

a { color: #a0c0ff; text-decoration: none; }
a:hover { text-decoration: underline; }

.repo-link a {
  font-size: 15px;
  font-weight: 600;
  color: #e2b714;
}

.back { font-size: 14px; }
.back a { color: #e2b714; }
</style>
