import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import VideoAgentModal from './VideoAgentModal.vue'
import { applyLocale, i18n } from '../i18n/index.js'

let wrapper

function mountModal() {
  wrapper = mount(VideoAgentModal, {
    attachTo: document.body,
    global: {
      plugins: [i18n],
      stubs: { teleport: true },
    },
  })
  return wrapper
}

function pressKey(key) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }))
}

describe('VideoAgentModal', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    document.body.style.overflow = ''
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
    document.body.style.overflow = ''
  })

  it('exposes an accessible dialog and preserves every source video link', async () => {
    const modal = mountModal()
    await modal.vm.$nextTick()

    const dialog = modal.find('[data-testid="video-agent-dialog"]')
    expect(dialog.attributes('role')).toBe('dialog')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(dialog.attributes('aria-labelledby')).toBe('video-agent-title')
    expect(modal.find('[data-testid="modal-close"]').attributes('aria-label')).toBe('Close video evidence')

    const links = modal.findAll('.video-card')
    expect(links).toHaveLength(6)
    expect(links[0].attributes('href')).toBe('https://www.youtube.com/watch?v=M4Ccsmk3gcE')
    expect(links[5].attributes('href')).toBe('https://www.youtube.com/watch?v=ch2FFSpxGwU')
    expect(links.every((link) => link.attributes('rel') === 'noopener')).toBe(true)
    expect(modal.text()).toContain('Highlights | Argentina 2-0 Austria | FIFA World Cup 2026™')

    await modal.find('[data-testid="modal-close"]').trigger('click')
    expect(modal.emitted('close')).toHaveLength(1)
  })

  it('captures focus, locks scrolling, and restores both when unmounted', async () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()

    const modal = mountModal()
    await modal.vm.$nextTick()

    expect(document.activeElement).toBe(modal.find('[data-testid="modal-close"]').element)
    expect(document.body.style.overflow).toBe('hidden')

    modal.unmount()
    wrapper = undefined
    expect(document.activeElement).toBe(trigger)
    expect(document.body.style.overflow).toBe('')
  })

  it('closes the lightbox first and emits close on the next Escape press', async () => {
    const modal = mountModal()
    await modal.find('[data-testid="screenshot-0"]').trigger('click')

    expect(modal.find('[data-testid="video-lightbox"]').attributes('role')).toBe('dialog')
    pressKey('Escape')
    await modal.vm.$nextTick()
    expect(modal.find('[data-testid="video-lightbox"]').exists()).toBe(false)
    expect(modal.emitted('close')).toBeUndefined()

    pressKey('Escape')
    expect(modal.emitted('close')).toHaveLength(1)
  })

  it('uses semantic screenshot controls and supports lightbox keyboard navigation', async () => {
    const modal = mountModal()
    const firstScreenshot = modal.find('[data-testid="screenshot-0"]')

    expect(firstScreenshot.element.tagName).toBe('BUTTON')
    expect(firstScreenshot.attributes('aria-label')).toContain('Open screenshot 1')
    await firstScreenshot.trigger('click')

    expect(modal.find('[data-testid="lightbox-previous"]').attributes('disabled')).toBeDefined()
    expect(modal.find('[data-testid="lightbox-next"]').attributes('aria-label')).toBe('Next screenshot')
    expect(modal.find('.lightbox-caption').text()).toContain('Argentina 2-0 Austria')

    pressKey('ArrowRight')
    await modal.vm.$nextTick()
    expect(modal.find('.lightbox-caption').text()).toContain('Ecuador 2-1 Germany')

    pressKey('ArrowLeft')
    await modal.vm.$nextTick()
    expect(modal.find('.lightbox-caption').text()).toContain('Argentina 2-0 Austria')
  })

  it('localizes modal copy, captions, and control labels in Spanish', async () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const modal = mountModal()
    await modal.vm.$nextTick()

    expect(modal.text()).toContain('Agente de inteligencia de vídeo')
    expect(modal.text()).toContain('Cómo funciona')
    expect(modal.find('[data-testid="screenshot-0"]').attributes('aria-label')).toContain('Abrir captura 1')
    expect(modal.find('figcaption').text()).toContain('Resultado de búsqueda de resúmenes')
    expect(modal.find('[data-testid="modal-close"]').attributes('aria-label')).toBe('Cerrar evidencia de vídeo')
  })
})
