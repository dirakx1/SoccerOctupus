import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AuthenticatorQrCode from './AuthenticatorQrCode.vue'

const setupUri = 'otpauth://totp/SoccerOctopus:alexmorgan?secret=SECRET123&issuer=SoccerOctopus'

describe('AuthenticatorQrCode', () => {
  it('renders a standards-compliant local SVG QR code without exposing the setup URI text', async () => {
    const wrapper = mount(AuthenticatorQrCode, {
      props: { value: setupUri },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.findAll('path').length).toBeGreaterThan(0)
    expect(wrapper.html()).not.toContain('otpauth://')
    expect(wrapper.text()).not.toContain('SECRET123')
  })

  it('renders longer authenticator setup URIs', async () => {
    const longSetupUri = `otpauth://totp/SoccerOctopus:${'a'.repeat(80)}?secret=${'A'.repeat(32)}&issuer=SoccerOctopus`
    const wrapper = mount(AuthenticatorQrCode, {
      props: { value: longSetupUri },
    })

    await flushPromises()

    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
    expect(wrapper.find('svg').exists()).toBe(true)
  })
})
