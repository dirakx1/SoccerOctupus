import { describe, expect, it } from 'vitest'

import router from './index.js'

describe('router meta', () => {
  it('marks admin settings as admin-only', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/admin/settings')
    expect(route.meta.admin).toBe(true)
  })

  it('marks sign-in as public', () => {
    const route = router.getRoutes().find((entry) => entry.path === '/sign-in')
    expect(route.meta.public).toBe(true)
  })
})
