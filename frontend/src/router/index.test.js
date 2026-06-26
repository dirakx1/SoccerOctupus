import { beforeEach, describe, expect, it } from 'vitest'

import router from './index.js'
import { clearAuthState, setAuthState } from '../lib/auth'

describe('router meta', () => {
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

  it('marks home as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/')
    expect(route.meta.public).toBe(true)
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

  it('redirects protected routes when cached auth is loaded as signed out', async () => {
    clearAuthState()
    await router.push('/profile')
    expect(router.currentRoute.value.path).toBe('/sign-in')
  })

  it('redirects signed-in non-admin users away from admin routes', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    await router.push('/admin/settings')
    expect(router.currentRoute.value.path).toBe('/')
  })
})
