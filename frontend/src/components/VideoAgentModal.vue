<template>
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('close')">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">

        <button class="close-btn" aria-label="Close" @click="$emit('close')">✕</button>

        <div class="modal-header">
          <span class="modal-icon">🎥</span>
          <div>
            <h2 id="modal-title">Video Intelligence Agent</h2>
            <p class="modal-sub">
              Analyses YouTube highlights for engagement ratios, title sentiment, and
              tactical momentum signals — then blends them into the swarm prediction.
            </p>
          </div>
        </div>

        <!-- Screenshots -->
        <section class="section">
          <h3 class="section-title">How It Works</h3>
          <div class="screenshots-grid">
            <figure
              v-for="(shot, i) in screenshots"
              :key="i"
              class="screenshot-fig"
              @click="openLightbox(i)"
            >
              <div class="img-wrap">
                <img
                  v-if="shot.src"
                  :src="shot.src"
                  :alt="shot.caption"
                  class="screenshot-img"
                />
                <div v-else class="placeholder-img">
                  <span class="placeholder-icon">📷</span>
                  <span class="placeholder-label">{{ shot.caption }}</span>
                </div>
              </div>
              <figcaption>{{ shot.caption }}</figcaption>
            </figure>
          </div>
        </section>

        <!-- YouTube videos -->
        <section class="section">
          <h3 class="section-title">Watch It In Action</h3>
          <div class="videos-grid">
            <a
              v-for="(vid, i) in videos"
              :key="i"
              :href="vid.url || '#'"
              target="_blank"
              rel="noopener"
              class="video-card"
              :class="{ placeholder: !vid.url }"
            >
              <div class="thumb-wrap">
                <img
                  v-if="vid.thumbnail"
                  :src="vid.thumbnail"
                  :alt="vid.title"
                  class="thumb-img"
                />
                <div v-else class="placeholder-thumb">
                  <span class="yt-icon">▶</span>
                </div>
                <div class="play-overlay">▶</div>
              </div>
              <div class="video-meta">
                <span class="video-title">{{ vid.title }}</span>
                <span class="video-dur">{{ vid.duration }}</span>
              </div>
            </a>
          </div>
        </section>

      </div>
    </div>

    <!-- Lightbox -->
    <div v-if="lightboxIndex !== null" class="lightbox" @click.self="lightboxIndex = null">
      <button class="lb-close" @click="lightboxIndex = null">✕</button>
      <button class="lb-nav lb-prev" @click="prevShot" :disabled="lightboxIndex === 0">‹</button>
      <div class="lb-content">
        <img
          v-if="screenshots[lightboxIndex]?.src"
          :src="screenshots[lightboxIndex].src"
          :alt="screenshots[lightboxIndex].caption"
          class="lb-img"
        />
        <div v-else class="lb-placeholder">
          <span class="placeholder-icon">📷</span>
          <span>{{ screenshots[lightboxIndex]?.caption }}</span>
        </div>
        <p class="lb-caption">{{ screenshots[lightboxIndex]?.caption }}</p>
      </div>
      <button class="lb-nav lb-next" @click="nextShot" :disabled="lightboxIndex === screenshots.length - 1">›</button>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineEmits(['close'])

// ── Screenshots ───────────────────────────────────────────────────────────────
// Real thumbnails from videos the agent actually fetches and analyses.
// Query 1: search_match_videos  → "[team_a] vs [team_b] highlights 2025 FIFA"
// Query 2: get_tactical_analysis_score → "[team] tactical analysis 2025 formation"
const screenshots = [
  {
    src: 'https://img.youtube.com/vi/M4Ccsmk3gcE/hqdefault.jpg',
    caption: 'Highlights query result — "Argentina 2-0 Austria | FIFA WC 2026™". Agent reads title for positive keywords ("win", "victory") and pulls view/like count.',
  },
  {
    src: 'https://img.youtube.com/vi/TImmPYoLE-8/hqdefault.jpg',
    caption: 'Highlights query result — "Ecuador 2-1 Germany | FIFA WC 2026™". Upset result: negative keywords detected for Germany → lower momentum score.',
  },
  {
    src: 'https://img.youtube.com/vi/sI6eXY0bS1M/hqdefault.jpg',
    caption: 'Tactical analysis query result — "Complete Argentina 2026 WC Breakdown". High engagement ratio (likes/views) → strong momentum signal fed into the swarm.',
  },
  {
    src: 'https://img.youtube.com/vi/_gpvQLTGtsc/hqdefault.jpg',
    caption: 'Tactical analysis query result — "Messi Breaks Records | Argentina vs Austria". Positive title sentiment + high views boosts Argentina\'s predicted win probability.',
  },
]

// ── YouTube videos ────────────────────────────────────────────────────────────
// Real WC 2026 videos returned by the agent's YouTube Data API v3 queries.
const videos = [
  {
    url: 'https://www.youtube.com/watch?v=M4Ccsmk3gcE',
    thumbnail: 'https://img.youtube.com/vi/M4Ccsmk3gcE/hqdefault.jpg',
    title: 'Highlights | Argentina 2-0 Austria | FIFA World Cup 2026™',
    duration: '4:03',
  },
  {
    url: 'https://www.youtube.com/watch?v=TImmPYoLE-8',
    thumbnail: 'https://img.youtube.com/vi/TImmPYoLE-8/hqdefault.jpg',
    title: 'Highlights | Ecuador 2-1 Germany | FIFA World Cup 2026™',
    duration: '3:51',
  },
  {
    url: 'https://www.youtube.com/watch?v=ABdniNBWtRs',
    thumbnail: 'https://img.youtube.com/vi/ABdniNBWtRs/hqdefault.jpg',
    title: 'Highlights | Norway 1-4 France | FIFA World Cup 2026™',
    duration: '4:18',
  },
  {
    url: 'https://www.youtube.com/watch?v=sI6eXY0bS1M',
    thumbnail: 'https://img.youtube.com/vi/sI6eXY0bS1M/hqdefault.jpg',
    title: 'The Complete Argentina 2026 World Cup Breakdown | Tactical Analysis',
    duration: '18:42',
  },
  {
    url: 'https://www.youtube.com/watch?v=_gpvQLTGtsc',
    thumbnail: 'https://img.youtube.com/vi/_gpvQLTGtsc/hqdefault.jpg',
    title: 'Messi Breaks Records | Argentina vs Austria | Tactical Analysis',
    duration: '11:27',
  },
  {
    url: 'https://www.youtube.com/watch?v=ch2FFSpxGwU',
    thumbnail: 'https://img.youtube.com/vi/ch2FFSpxGwU/hqdefault.jpg',
    title: 'Argentina 3-0 Algeria | FIFA WC 2026 | Tactical Analysis & Highlights',
    duration: '9:14',
  },
]

// ── Lightbox ──────────────────────────────────────────────────────────────────
const lightboxIndex = ref(null)

function openLightbox(i) { lightboxIndex.value = i }
function prevShot() { if (lightboxIndex.value > 0) lightboxIndex.value-- }
function nextShot() { if (lightboxIndex.value < screenshots.length - 1) lightboxIndex.value++ }

function onKey(e) {
  if (e.key === 'Escape') lightboxIndex.value = null
  if (e.key === 'ArrowLeft') prevShot()
  if (e.key === 'ArrowRight') nextShot()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
/* ── Overlay + modal ─────────────────────────────────────────────────────────── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}

.modal {
  background: #0f1a2e;
  border: 1px solid #0f3460;
  border-radius: 16px;
  max-width: 820px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: 32px;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 50%;
  color: #a0aec0;
  cursor: pointer;
  font-size: 16px;
  height: 32px;
  width: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s, border-color 0.2s;
}
.close-btn:hover { color: #e2b714; border-color: #e2b714; }

/* ── Header ──────────────────────────────────────────────────────────────────── */
.modal-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding-right: 40px;
}
.modal-icon { font-size: 40px; flex-shrink: 0; }
.modal-header h2 { color: #e2b714; font-size: 22px; margin-bottom: 6px; }
.modal-sub { color: #8888aa; font-size: 14px; line-height: 1.6; }

/* ── Sections ────────────────────────────────────────────────────────────────── */
.section { display: flex; flex-direction: column; gap: 14px; }
.section-title {
  color: #a0c0ff;
  font-size: 15px;
  font-weight: 700;
  border-left: 3px solid #e2b714;
  padding-left: 10px;
}

/* ── Screenshots grid ────────────────────────────────────────────────────────── */
.screenshots-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.screenshot-fig {
  margin: 0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.img-wrap {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #0f3460;
  aspect-ratio: 16 / 9;
  transition: border-color 0.2s;
}
.screenshot-fig:hover .img-wrap { border-color: #e2b714; }

.screenshot-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.placeholder-img {
  width: 100%;
  height: 100%;
  background: #16213e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3a4a6a;
}
.placeholder-icon { font-size: 28px; opacity: 0.5; }
.placeholder-label { font-size: 11px; text-align: center; padding: 0 8px; line-height: 1.4; }

figcaption {
  font-size: 12px;
  color: #6a6a8a;
  line-height: 1.4;
}

/* ── Videos grid ─────────────────────────────────────────────────────────────── */
.videos-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
/* Label rows: first 3 = match highlights, last 3 = tactical analysis */
.video-card:nth-child(1)::before,
.video-card:nth-child(2)::before,
.video-card:nth-child(3)::before {
  content: 'Match Highlights';
  display: block;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #4ade80;
  padding: 4px 10px 0;
}
.video-card:nth-child(4)::before,
.video-card:nth-child(5)::before,
.video-card:nth-child(6)::before {
  content: 'Tactical Analysis';
  display: block;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #a0c0ff;
  padding: 4px 10px 0;
}

.video-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-decoration: none;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #0f3460;
  background: #16213e;
  transition: border-color 0.2s, transform 0.2s;
}
.video-card:hover { border-color: #e2b714; transform: translateY(-2px); }
.video-card.placeholder { pointer-events: none; opacity: 0.5; }

.thumb-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #0a0a1a;
  overflow: hidden;
}
.thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder-thumb {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.yt-icon { font-size: 24px; color: #3a4a6a; }

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  color: white;
  font-size: 20px;
  opacity: 0;
  transition: opacity 0.2s;
}
.video-card:hover .play-overlay { opacity: 1; }

.video-meta {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.video-title { font-size: 12px; color: #c0c0d0; line-height: 1.4; }
.video-dur { font-size: 11px; color: #6a6a8a; }

/* ── Lightbox ────────────────────────────────────────────────────────────────── */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  gap: 16px;
  padding: 24px;
}

.lb-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255,255,255,0.1);
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
  font-size: 18px;
  height: 36px;
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lb-close:hover { background: rgba(255,255,255,0.2); }

.lb-nav {
  background: rgba(255,255,255,0.08);
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
  font-size: 28px;
  height: 48px;
  width: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s;
}
.lb-nav:hover:not(:disabled) { background: rgba(255,255,255,0.18); }
.lb-nav:disabled { opacity: 0.2; cursor: default; }

.lb-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 900px;
  width: 100%;
}

.lb-img {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 8px;
  object-fit: contain;
}

.lb-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #16213e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #3a4a6a;
  font-size: 14px;
  max-height: 70vh;
}
.lb-placeholder .placeholder-icon { font-size: 48px; }

.lb-caption {
  color: #a0aec0;
  font-size: 13px;
  text-align: center;
}

/* ── Responsive ──────────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .modal { padding: 20px 16px; }
  .screenshots-grid { grid-template-columns: 1fr; }
  .videos-grid { grid-template-columns: 1fr; }
  .modal-header { flex-direction: column; gap: 10px; }
  .lb-nav { display: none; }
}
@media (max-width: 480px) {
  .videos-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
