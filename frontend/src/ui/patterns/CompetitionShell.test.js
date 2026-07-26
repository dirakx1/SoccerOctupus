import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'

import { i18n, applyLocale } from '../../i18n/index.js'
import { worldCup2026 } from '../../competition/editions/worldCup2026.js'
import { getCompetitionNavigation } from '../../competition/navigation.js'
import CompetitionShell from './CompetitionShell.vue'

const RouterLink = {
  props: ['to'],
  template: '<a :data-route="typeof to === \'string\' ? to : to.name"><slot /></a>',
}

const baseProps = {
  edition: worldCup2026,
  editions: [worldCup2026],
  navigation: getCompetitionNavigation(worldCup2026, { locale: 'en' }),
  homeLocation: { name: 'competition-workspace-overview' },
  locale: 'en',
  themePreference: 'system',
  effectiveTheme: 'light',
  workspaceRoute: true,
  signedIn: true,
  isAdmin: true,
  userDisplayName: 'Alex Morgan',
  userEmail: 'alex@example.com',
  userInitials: 'AM',
  userAvatarUrl: '',
  mobileMenuOpen: false,
  userMenuOpen: false,
}

function mountShell(props = {}) {
  const resolvedProps = { ...baseProps, ...props }
  applyLocale(resolvedProps.locale)
  return mount(CompetitionShell, {
    props: resolvedProps,
    global: { plugins: [i18n], stubs: { RouterLink } },
  })
}

describe('CompetitionShell', () => {
  it('renders localized signed-in workspace navigation and competition context', () => {
    applyLocale('en')
    const wrapper = mountShell()

    expect(wrapper.find('[data-testid="competition-toggle"]').text()).toContain('FIFA World Cup 2026')
    expect(wrapper.find('[data-testid="brand-mark"]').attributes('src')).toBe('/favicon.svg')
    expect(wrapper.find('.shell-brand-copy small').exists()).toBe(false)
    expect(wrapper.find('[data-testid="competition-context-label"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="workspace-navigation"]').text()).toContain('Overview')
    expect(wrapper.find('[data-testid="workspace-navigation"]').text()).toContain('Bracket')
    expect(wrapper.find('[data-testid="workspace-navigation"] svg').exists()).toBe(false)
    expect(wrapper.find('.shell-subbar').exists()).toBe(false)
    expect(wrapper.text()).toContain('AM')
    expect(wrapper.text()).toContain('Admin')
  })

  it('renders signed-out navigation in Spanish and exposes closed controls', () => {
    applyLocale('es')
    const wrapper = mountShell({
      locale: 'es',
      navigation: getCompetitionNavigation(worldCup2026, { locale: 'es' }),
      signedIn: false,
      isAdmin: false,
    })

    expect(wrapper.find('[data-testid="workspace-navigation"]').text()).toContain('Precios')
    expect(wrapper.text()).toContain('Iniciar sesión')
    expect(wrapper.find('[data-testid="mobile-menu-toggle"]').attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('[data-testid="account-menu-toggle"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="locale-toggle"]').text()).toContain('ES')
    expect(wrapper.find('[data-testid="locale-toggle"]').attributes('aria-haspopup')).toBe('menu')
    expect(wrapper.find('[data-testid="theme-toggle"]').attributes('title')).toContain('Cambiar tema')
  })

  it('exposes the locale menu on flat public and auth routes', async () => {
    const wrapper = mountShell({ workspaceRoute: false, signedIn: false })

    expect(wrapper.find('[data-testid="locale-toggle"]').exists()).toBe(true)
    await wrapper.find('[data-testid="locale-toggle"]').trigger('click')

    expect(wrapper.find('[data-testid="locale-menu"]').exists()).toBe(true)
    await wrapper.find('[data-testid="locale-option-es"]').trigger('click')
    expect(wrapper.emitted('locale-change')).toEqual([['es']])
  })

  it('emits mobile and account menu actions with expanded state', async () => {
    const wrapper = mountShell({ mobileMenuOpen: true, userMenuOpen: true })

    expect(wrapper.find('[data-testid="mobile-menu-toggle"]').attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(true)

    await wrapper.find('[data-testid="mobile-menu-toggle"]').trigger('click')
    await wrapper.find('[data-testid="account-menu-toggle"]').trigger('click')

    expect(wrapper.emitted('toggle-mobile')).toHaveLength(1)
    expect(wrapper.emitted('toggle-account')).toHaveLength(1)
  })

  it('emits locale and theme preference changes from keyboard-selectable controls', async () => {
    const wrapper = mountShell()

    await wrapper.find('[data-testid="locale-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="locale-toggle"]').attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('[data-testid="locale-menu"]').text()).toContain('English')
    expect(wrapper.find('[data-testid="locale-menu"]').text()).toContain('Español')
    await wrapper.find('[data-testid="locale-option-es"]').trigger('click')

    await wrapper.find('[data-testid="theme-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="theme-toggle"]').attributes('aria-haspopup')).toBe('menu')
    expect(wrapper.find('[data-testid="theme-menu"]').text()).toContain('Light')
    expect(wrapper.find('[data-testid="theme-menu"]').text()).toContain('System')
    await wrapper.find('[data-testid="theme-option-dark"]').trigger('click')

    expect(wrapper.emitted('locale-change')).toEqual([['es']])
    expect(wrapper.emitted('theme-change')).toEqual([['dark']])
  })

  it('opens a registered Competition Edition menu without inventing editions', async () => {
    const wrapper = mountShell()

    await wrapper.find('[data-testid="competition-toggle"]').trigger('click')

    expect(wrapper.find('[data-testid="competition-menu"]').text()).toContain('FIFA World Cup 2026')
    expect(wrapper.findAll('[data-testid^="competition-option-"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="competition-toggle"]').attributes('aria-expanded')).toBe('true')

    await wrapper.find('[data-testid="competition-option-world-cup-2026"]').trigger('click')
    expect(wrapper.emitted('edition-change')).toEqual([[worldCup2026]])
    expect(wrapper.find('[data-testid="competition-menu"]').exists()).toBe(false)
  })

  it('lists and selects the current Premier League Competition Edition', async () => {
    const premierLeague = {
      id: 'premier-league-2026-27',
      slug: 'premier-league',
      displayName: 'Premier League 2026-27',
      capabilities: ['table', 'fixtures', 'predictions', 'markets'],
    }
    const wrapper = mountShell({ editions: [worldCup2026, premierLeague] })

    await wrapper.find('[data-testid="competition-toggle"]').trigger('click')

    expect(wrapper.find('[data-testid="competition-menu"]').text()).toContain('Premier League 2026-27')
    await wrapper.find('[data-testid="competition-option-premier-league"]').trigger('click')
    expect(wrapper.emitted('edition-change')).toContainEqual([premierLeague])
  })

  it('closes an open control menu when focus moves outside the shell', async () => {
    const wrapper = mountShell()

    await wrapper.find('[data-testid="theme-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="theme-menu"]').exists()).toBe(true)

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()

    expect(wrapper.find('[data-testid="theme-menu"]').exists()).toBe(false)
  })
})
