import { beforeEach, describe, expect, it } from 'vitest'

import router from './index.js'
import { WORKSPACE_ROUTE_NAMES } from './workspace.js'
import { clearAuthState, setAuthState } from '../lib/auth'
import { applyLocale, i18n, LOCALE_STORAGE_KEY } from '../i18n/index.js'
import { consumePostAuthRedirect } from '../lib/postAuthRedirect.js'

describe('router', () => {
  beforeEach(async () => {
    clearAuthState()
    await router.push('/')
  })

  it('marks admin settings as admin-only', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/admin/settings')
    expect(route.meta.admin).toBe(true)
  })

  it('marks sign-in as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/sign-in')
    expect(route.meta.public).toBe(true)
  })

  it('marks complete-username as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/complete-username')
    expect(route.meta.public).toBe(true)
  })

  it('marks home as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/')
    expect(route.meta.public).toBe(true)
  })

  it('keeps design-lab routes public and unchanged', () => {
    const paths = ['/design-lab', '/design-lab/atlas', '/design-lab/orbit']

    for (const path of paths) {
      const resolved = router.resolve(path)
      expect(resolved.path).toBe(path)
      expect(resolved.meta.public).toBe(true)
    }
  })

  it('resolves the localized Competition Workspace overview', async () => {
    await router.push('/es/competitions/world-cup-2026')

    expect(router.currentRoute.value.name).toBe(WORKSPACE_ROUTE_NAMES.overview)
    expect(router.currentRoute.value.params).toEqual({
      locale: 'es',
      competitionEditionSlug: 'world-cup-2026',
    })
    expect(router.currentRoute.value.meta.public).toBe(true)
  })

  it('resolves protected Competition Workspace areas through stable route names', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })

    const routes = [
      ['/es/competitions/world-cup-2026/groups', WORKSPACE_ROUTE_NAMES.groups],
      ['/es/competitions/world-cup-2026/predict', WORKSPACE_ROUTE_NAMES.predict],
      ['/es/competitions/world-cup-2026/bracket', WORKSPACE_ROUTE_NAMES.bracket],
      ['/es/competitions/world-cup-2026/markets', WORKSPACE_ROUTE_NAMES.markets],
    ]

    for (const [path, name] of routes) {
      await router.push(path)
      expect(router.currentRoute.value.name).toBe(name)
      expect(router.currentRoute.value.meta.requiresAuth).toBe(true)
    }
  })

  it('redirects legacy workspace paths while preserving query and hash', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })

    const redirects = [
      ['/', '/en/competitions/world-cup-2026'],
      ['/groups', '/en/competitions/world-cup-2026/groups'],
      ['/predict', '/en/competitions/world-cup-2026/predict'],
      ['/tournament', '/en/competitions/world-cup-2026/bracket'],
      ['/markets', '/en/competitions/world-cup-2026/markets'],
    ]

    for (const [source, target] of redirects) {
      await router.push({ path: source, query: { source: 'legacy' }, hash: '#details' })
      expect(router.currentRoute.value.fullPath).toBe(`${target}?source=legacy#details`)
    }
  })

  it('applies the URL locale over the saved preference on workspace navigation', async () => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, 'en')
    document.documentElement.lang = 'en'

    await router.push('/es/competitions/world-cup-2026')

    expect(i18n.global.locale.value).toBe('es')
    expect(document.documentElement.lang).toBe('es')
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('es')
  })

  it('keeps flat routes, query, and hash stable when their locale preference changes', async () => {
    await router.push('/pricing?plan=pro#compare')

    applyLocale('es', {
      storage: window.localStorage,
      documentElement: document.documentElement,
    })

    expect(router.currentRoute.value.fullPath).toBe('/pricing?plan=pro#compare')
    expect(i18n.global.locale.value).toBe('es')
    expect(document.documentElement.lang).toBe('es')
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('es')
  })

  it('redirects unknown and blank Competition Editions to localized World Cup home', async () => {
    const paths = [
      '/es/competitions/not-registered/groups',
      '/es/competitions',
      '/es/competitions//groups',
    ]

    for (const path of paths) {
      await router.push({ path, query: { source: 'fallback' }, hash: '#overview' })
      expect(router.currentRoute.value.fullPath).toBe(
        '/es/competitions/world-cup-2026?source=fallback#overview'
      )
    }
  })

  it('marks profile as signed-in only', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/profile')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('marks pricing as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/pricing')
    expect(route.meta.public).toBe(true)
  })

  it('redirects the old billing route to profile', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/billing')
    expect(route.redirect).toBe('/profile')
  })

  it('marks billing success as signed-in only', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/billing/success')
    expect(route.meta.requiresAuth).toBe(true)
  })

  it('lazy-loads route views', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/profile')
    expect(typeof route.components.default).toBe('function')
  })

  it('lazy-loads the username completion view', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/complete-username')
    expect(typeof route.components.default).toBe('function')
  })

  it('redirects protected routes when cached auth is loaded as signed out', async () => {
    clearAuthState()
    await router.push('/profile')
    expect(router.currentRoute.value.path).toBe('/sign-in')
  })

  it('preserves the full canonical destination when workspace auth is required', async () => {
    clearAuthState()
    consumePostAuthRedirect()

    await router.push('/es/competitions/world-cup-2026/predict?stage=group#match-form')

    expect(router.currentRoute.value.path).toBe('/sign-in')
    expect(consumePostAuthRedirect()).toBe(
      '/es/competitions/world-cup-2026/predict?stage=group#match-form'
    )
  })

  it('redirects signed-in non-admin users away from admin routes', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    await router.push('/admin/settings')
    expect(router.currentRoute.value.path).toBe('/en/competitions/world-cup-2026')
  })
})
