import { mount } from '@vue/test-utils'
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
  return mount(CompetitionShell, {
    props: { ...baseProps, ...props },
    global: { plugins: [i18n], stubs: { RouterLink } },
  })
}

describe('CompetitionShell', () => {
  it('renders localized signed-in workspace navigation and competition context', () => {
    applyLocale('en')
    const wrapper = mountShell()

    expect(wrapper.find('[data-testid="competition-context"]').text()).toContain('FIFA World Cup 2026')
    expect(wrapper.find('[data-testid="workspace-navigation"]').text()).toContain('Overview')
    expect(wrapper.find('[data-testid="workspace-navigation"]').text()).toContain('Bracket')
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

    await wrapper.find('[data-testid="locale-control"]').setValue('es')
    await wrapper.find('[data-testid="theme-control"]').setValue('dark')

    expect(wrapper.emitted('locale-change')).toEqual([['es']])
    expect(wrapper.emitted('theme-change')).toEqual([['dark']])
  })
})
