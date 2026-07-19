import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { i18n, applyLocale } from '../../i18n/index.js'
import { worldCup2026 } from '../../competition/editions/worldCup2026.js'
import { getCompetitionNavigation } from '../../competition/navigation.js'
import AppShell from './AppShell.vue'

const RouterLink = {
  props: ['to'],
  template: '<a :data-route="typeof to === \'string\' ? to : to.name"><slot /></a>',
}

const props = {
  edition: worldCup2026,
  editions: [worldCup2026],
  navigation: getCompetitionNavigation(worldCup2026, { locale: 'en' }),
  homeLocation: { name: 'competition-workspace-overview' },
  locale: 'en',
  themePreference: 'system',
  effectiveTheme: 'light',
  workspaceRoute: true,
  signedIn: true,
  isAdmin: false,
  userDisplayName: 'Alex Morgan',
  userEmail: 'alex@example.com',
  userInitials: 'AM',
  mobileMenuOpen: false,
  userMenuOpen: false,
}

describe('AppShell', () => {
  it('renders the localized shell, route content, and footer labels', () => {
    applyLocale('es')
    const wrapper = mount(AppShell, {
      props: { ...props, locale: 'es' },
      slots: { default: '<div data-testid="page-content">Groups page</div>' },
      global: { plugins: [i18n], stubs: { RouterLink } },
    })

    expect(wrapper.find('[data-testid="competition-toggle"]').text()).toContain('Copa Mundial de la FIFA 2026')
    expect(wrapper.find('[data-testid="page-content"]').text()).toBe('Groups page')
    expect(wrapper.find('footer').text()).toContain('Aviso legal')
    expect(wrapper.find('footer').text()).toContain('Política de cookies')
  })

  it('keeps recovery, billing, and cookie regions as explicit slots', () => {
    applyLocale('en')
    const wrapper = mount(AppShell, {
      props,
      slots: {
        'billing-notice': '<div data-testid="billing-slot">Billing</div>',
        'auth-recovery': '<div data-testid="recovery-slot">Recovery</div>',
        cookie: '<div data-testid="cookie-slot">Cookie</div>',
      },
      global: { plugins: [i18n], stubs: { RouterLink } },
    })

    expect(wrapper.find('[data-testid="billing-slot"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="recovery-slot"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cookie-slot"]').exists()).toBe(true)
  })
})
