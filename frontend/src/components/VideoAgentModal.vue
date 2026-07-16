<template>
  <Teleport to="body">
    <div class="video-overlay" @click.self="requestClose">
      <section
        data-testid="video-agent-dialog"
        class="video-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="video-agent-title"
        aria-describedby="video-agent-description"
      >
        <button
          ref="modalCloseRef"
          data-testid="modal-close"
          class="icon-button modal-close"
          type="button"
          :aria-label="t('overlays.video.close')"
          @click="requestClose"
        >
          <X :size="20" aria-hidden="true" />
        </button>

        <header class="modal-header">
          <div class="modal-heading-icon" aria-hidden="true">
            <Clapperboard :size="24" />
          </div>
          <div>
            <p class="modal-kicker">{{ t('overlays.video.eyebrow') }}</p>
            <h2 id="video-agent-title">{{ t('overlays.video.title') }}</h2>
            <p id="video-agent-description" class="modal-description">{{ t('overlays.video.description') }}</p>
          </div>
        </header>

        <section class="evidence-section" aria-labelledby="screenshots-title">
          <div class="section-heading">
            <h3 id="screenshots-title">{{ t('overlays.video.howItWorks') }}</h3>
            <span>{{ screenshots.length }}</span>
          </div>
          <div class="screenshots-grid">
            <figure v-for="(shot, index) in screenshots" :key="shot.src" class="screenshot-figure">
              <button
                :data-testid="`screenshot-${index}`"
                class="screenshot-button"
                type="button"
                :aria-label="t('overlays.video.openScreenshot', { number: index + 1, caption: t(shot.captionKey) })"
                @click="openLightbox(index)"
              >
                <img v-if="shot.src" :src="shot.src" :alt="t(shot.captionKey)" />
                <span v-else class="media-placeholder">
                  <Image :size="28" aria-hidden="true" />
                  <span>{{ t('overlays.video.imageUnavailable') }}</span>
                </span>
                <span class="screenshot-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="open-indicator" aria-hidden="true"><Expand :size="17" /></span>
              </button>
              <figcaption>{{ t(shot.captionKey) }}</figcaption>
            </figure>
          </div>
        </section>

        <section class="evidence-section" aria-labelledby="videos-title">
          <div class="section-heading">
            <h3 id="videos-title">{{ t('overlays.video.watchEvidence') }}</h3>
            <span>{{ videos.length }}</span>
          </div>
          <div class="videos-grid">
            <a
              v-for="video in videos"
              :key="video.url"
              :href="video.url"
              target="_blank"
              rel="noopener"
              class="video-card"
              :aria-label="t('overlays.video.openVideo', { title: video.title })"
            >
              <span class="video-category">{{ t(video.categoryKey) }}</span>
              <span class="thumbnail-wrap">
                <img :src="video.thumbnail" :alt="video.title" />
                <span class="play-indicator" aria-hidden="true"><Play :size="18" fill="currentColor" /></span>
              </span>
              <span class="video-meta">
                <strong>{{ video.title }}</strong>
                <span>{{ video.duration }}</span>
              </span>
            </a>
          </div>
        </section>
      </section>
    </div>

    <div
      v-if="lightboxIndex !== null"
      data-testid="video-lightbox"
      class="lightbox-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="video-lightbox-title"
      @click.self="closeLightbox"
    >
      <h2 id="video-lightbox-title" class="sr-only">{{ t('overlays.video.lightboxLabel') }}</h2>
      <button
        ref="lightboxCloseRef"
        class="icon-button lightbox-close"
        type="button"
        :aria-label="t('overlays.video.closeLightbox')"
        @click="closeLightbox"
      >
        <X :size="20" aria-hidden="true" />
      </button>
      <button
        data-testid="lightbox-previous"
        class="icon-button lightbox-nav lightbox-previous"
        type="button"
        :aria-label="t('overlays.video.previous')"
        :disabled="lightboxIndex === 0"
        @click="previousShot"
      >
        <ChevronLeft :size="22" aria-hidden="true" />
      </button>
      <figure class="lightbox-content">
        <img
          v-if="activeScreenshot.src"
          :src="activeScreenshot.src"
          :alt="t(activeScreenshot.captionKey)"
        />
        <div v-else class="media-placeholder lightbox-placeholder">
          <Image :size="32" aria-hidden="true" />
          <span>{{ t('overlays.video.imageUnavailable') }}</span>
        </div>
        <figcaption class="lightbox-caption">{{ t(activeScreenshot.captionKey) }}</figcaption>
      </figure>
      <button
        data-testid="lightbox-next"
        class="icon-button lightbox-nav lightbox-next"
        type="button"
        :aria-label="t('overlays.video.next')"
        :disabled="lightboxIndex === screenshots.length - 1"
        @click="nextShot"
      >
        <ChevronRight :size="22" aria-hidden="true" />
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Expand,
  Image,
  Play,
  X,
} from '@lucide/vue'

const emit = defineEmits(['close'])
const { t } = useI18n()
const lightboxIndex = ref(null)
const modalCloseRef = ref(null)
const lightboxCloseRef = ref(null)
let previouslyFocused = null
let lightboxTrigger = null
let previousBodyOverflow = ''

const screenshots = [
  {
    src: 'https://img.youtube.com/vi/M4Ccsmk3gcE/hqdefault.jpg',
    captionKey: 'overlays.video.captions.highlightsArgentina',
  },
  {
    src: 'https://img.youtube.com/vi/TImmPYoLE-8/hqdefault.jpg',
    captionKey: 'overlays.video.captions.highlightsGermany',
  },
  {
    src: 'https://img.youtube.com/vi/sI6eXY0bS1M/hqdefault.jpg',
    captionKey: 'overlays.video.captions.tacticalArgentina',
  },
  {
    src: 'https://img.youtube.com/vi/_gpvQLTGtsc/hqdefault.jpg',
    captionKey: 'overlays.video.captions.tacticalMessi',
  },
]

const videos = [
  {
    url: 'https://www.youtube.com/watch?v=M4Ccsmk3gcE',
    thumbnail: 'https://img.youtube.com/vi/M4Ccsmk3gcE/hqdefault.jpg',
    title: 'Highlights | Argentina 2-0 Austria | FIFA World Cup 2026™',
    duration: '4:03',
    categoryKey: 'overlays.video.categories.highlights',
  },
  {
    url: 'https://www.youtube.com/watch?v=TImmPYoLE-8',
    thumbnail: 'https://img.youtube.com/vi/TImmPYoLE-8/hqdefault.jpg',
    title: 'Highlights | Ecuador 2-1 Germany | FIFA World Cup 2026™',
    duration: '3:51',
    categoryKey: 'overlays.video.categories.highlights',
  },
  {
    url: 'https://www.youtube.com/watch?v=ABdniNBWtRs',
    thumbnail: 'https://img.youtube.com/vi/ABdniNBWtRs/hqdefault.jpg',
    title: 'Highlights | Norway 1-4 France | FIFA World Cup 2026™',
    duration: '4:18',
    categoryKey: 'overlays.video.categories.highlights',
  },
  {
    url: 'https://www.youtube.com/watch?v=sI6eXY0bS1M',
    thumbnail: 'https://img.youtube.com/vi/sI6eXY0bS1M/hqdefault.jpg',
    title: 'The Complete Argentina 2026 World Cup Breakdown | Tactical Analysis',
    duration: '18:42',
    categoryKey: 'overlays.video.categories.tactical',
  },
  {
    url: 'https://www.youtube.com/watch?v=_gpvQLTGtsc',
    thumbnail: 'https://img.youtube.com/vi/_gpvQLTGtsc/hqdefault.jpg',
    title: 'Messi Breaks Records | Argentina vs Austria | Tactical Analysis',
    duration: '11:27',
    categoryKey: 'overlays.video.categories.tactical',
  },
  {
    url: 'https://www.youtube.com/watch?v=ch2FFSpxGwU',
    thumbnail: 'https://img.youtube.com/vi/ch2FFSpxGwU/hqdefault.jpg',
    title: 'Argentina 3-0 Algeria | FIFA WC 2026 | Tactical Analysis & Highlights',
    duration: '9:14',
    categoryKey: 'overlays.video.categories.tactical',
  },
]

const activeScreenshot = computed(() => screenshots[lightboxIndex.value] || screenshots[0])

function requestClose() {
  emit('close')
}

function openLightbox(index) {
  lightboxTrigger = document.activeElement
  lightboxIndex.value = index
  nextTick(() => lightboxCloseRef.value?.focus())
}

function closeLightbox() {
  lightboxIndex.value = null
  nextTick(() => lightboxTrigger?.focus?.())
}

function previousShot() {
  if (lightboxIndex.value > 0) lightboxIndex.value -= 1
}

function nextShot() {
  if (lightboxIndex.value !== null && lightboxIndex.value < screenshots.length - 1) {
    lightboxIndex.value += 1
  }
}

function onKey(event) {
  if (event.key === 'Escape') {
    if (lightboxIndex.value !== null) closeLightbox()
    else requestClose()
    return
  }

  if (lightboxIndex.value === null) return
  if (event.key === 'ArrowLeft') previousShot()
  if (event.key === 'ArrowRight') nextShot()
}

onMounted(() => {
  previouslyFocused = document.activeElement
  previousBodyOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKey)
  modalCloseRef.value?.focus()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = previousBodyOverflow
  previouslyFocused?.focus?.()
})
</script>

<style scoped>
.video-overlay,
.lightbox-overlay {
  align-items: center;
  background: color-mix(in srgb, var(--color-background) 88%, transparent);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: var(--space-4);
  position: fixed;
  z-index: var(--z-modal);
}

.video-modal {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border-strong);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  max-height: calc(100vh - var(--space-8));
  max-width: 58rem;
  overflow-y: auto;
  padding: var(--space-8);
  position: relative;
  width: 100%;
}

.icon-button {
  align-items: center;
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  cursor: pointer;
  display: inline-flex;
  height: var(--control-height-lg);
  justify-content: center;
  padding: 0;
  width: var(--control-height-lg);
}

.icon-button:hover:not(:disabled) { border-color: var(--color-accent); color: var(--color-accent); }
.icon-button:focus-visible,
.screenshot-button:focus-visible,
.video-card:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.icon-button:disabled { color: var(--color-text-subtle); cursor: not-allowed; opacity: 0.45; }

.modal-close { position: absolute; right: var(--space-5); top: var(--space-5); z-index: 1; }

.modal-header { align-items: flex-start; display: grid; gap: var(--space-4); grid-template-columns: auto minmax(0, 1fr); padding-right: var(--space-12); }
.modal-heading-icon { align-items: center; background: var(--color-surface-inset); color: var(--color-accent); display: inline-flex; height: var(--control-height-lg); justify-content: center; width: var(--control-height-lg); }
.modal-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-2); text-transform: uppercase; }
.modal-header h2 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); line-height: var(--line-height-tight); margin: 0; }
.modal-description { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 64ch; }

.evidence-section { display: flex; flex-direction: column; gap: var(--space-4); }
.section-heading { align-items: baseline; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-3); }
.section-heading h3 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.section-heading > span { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }

.screenshots-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.screenshot-figure { display: flex; flex-direction: column; gap: var(--space-2); margin: 0; min-width: 0; }
.screenshot-button { aspect-ratio: 16 / 9; background: var(--color-surface-inset); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); cursor: pointer; display: block; overflow: hidden; padding: 0; position: relative; width: 100%; }
.screenshot-button:hover { border-color: var(--color-accent); }
.screenshot-button img { display: block; height: 100%; object-fit: cover; width: 100%; }
.screenshot-index { background: var(--color-surface-raised); bottom: var(--space-2); color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); left: var(--space-2); padding: var(--space-1) var(--space-2); position: absolute; }
.open-indicator { align-items: center; background: var(--color-surface-raised); color: var(--color-accent); display: inline-flex; height: var(--control-height-md); justify-content: center; position: absolute; right: var(--space-2); top: var(--space-2); width: var(--control-height-md); }
.screenshot-figure figcaption { color: var(--color-text-muted); font-size: var(--font-size-xs); line-height: var(--line-height-relaxed); }

.media-placeholder { align-items: center; background: var(--color-surface-inset); color: var(--color-text-muted); display: flex; flex-direction: column; gap: var(--space-2); height: 100%; justify-content: center; width: 100%; }

.videos-grid { display: grid; gap: var(--space-3); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.video-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); display: flex; flex-direction: column; min-width: 0; text-decoration: none; transition: border-color var(--duration-fast) var(--easing-standard), transform var(--duration-fast) var(--easing-standard); }
.video-card:hover { border-color: var(--color-accent); transform: translateY(-2px); }
.video-category { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding: var(--space-3) var(--space-3) var(--space-2); text-transform: uppercase; }
.thumbnail-wrap { aspect-ratio: 16 / 9; background: var(--color-surface-inset); display: block; overflow: hidden; position: relative; }
.thumbnail-wrap img { display: block; height: 100%; object-fit: cover; width: 100%; }
.play-indicator { align-items: center; background: color-mix(in srgb, var(--color-background) 68%, transparent); color: var(--color-text); display: inline-flex; height: var(--control-height-lg); inset: 50% auto auto 50%; justify-content: center; position: absolute; transform: translate(-50%, -50%); width: var(--control-height-lg); }
.video-meta { display: grid; gap: var(--space-2); padding: var(--space-3); }
.video-meta strong { font-size: var(--font-size-xs); line-height: var(--line-height-normal); }
.video-meta > span { color: var(--color-text-subtle); font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }

.lightbox-overlay { background: color-mix(in srgb, var(--color-background) 95%, transparent); gap: var(--space-4); z-index: calc(var(--z-modal) + 1); }
.lightbox-close { position: absolute; right: var(--space-5); top: var(--space-5); }
.lightbox-nav { flex: 0 0 auto; }
.lightbox-content { align-items: center; display: flex; flex-direction: column; gap: var(--space-3); margin: 0; max-width: 64rem; min-width: 0; width: 100%; }
.lightbox-content img { max-height: 72vh; max-width: 100%; object-fit: contain; }
.lightbox-caption { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: 0; max-width: 78ch; text-align: center; }
.lightbox-placeholder { aspect-ratio: 16 / 9; max-height: 72vh; }

.sr-only { border: 0; clip: rect(0 0 0 0); height: 1px; margin: -1px; overflow: hidden; padding: 0; position: absolute; white-space: nowrap; width: 1px; }

@media (max-width: 760px) {
  .video-modal { padding: var(--space-6) var(--space-4); }
  .modal-close { right: var(--space-3); top: var(--space-3); }
  .modal-header { grid-template-columns: 1fr; padding-right: var(--space-12); }
  .modal-heading-icon { display: none; }
  .videos-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .lightbox-overlay { align-items: stretch; display: grid; gap: var(--space-2); grid-template-columns: var(--control-height-lg) minmax(0, 1fr) var(--control-height-lg); grid-template-rows: minmax(0, 1fr) auto; padding: var(--space-4); }
  .lightbox-content { grid-column: 1 / -1; grid-row: 1; justify-self: center; }
  .lightbox-nav { align-self: center; grid-row: 2; }
  .lightbox-previous { grid-column: 1; }
  .lightbox-next { grid-column: 3; }
}

@media (max-width: 520px) {
  .video-overlay { padding: var(--space-2); }
  .video-modal { max-height: calc(100vh - var(--space-4)); }
  .modal-header h2 { font-size: var(--font-size-2xl); }
  .screenshots-grid,
  .videos-grid { grid-template-columns: 1fr; }
  .lightbox-close { right: var(--space-3); top: var(--space-3); }
}

@media (prefers-reduced-motion: reduce) {
  .video-card { transition: none; }
}
</style>
