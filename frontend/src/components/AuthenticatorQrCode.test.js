import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AuthenticatorQrCode from './AuthenticatorQrCode.vue'
import { createQrMatrix } from '../lib/qrCode'

const setupUri = 'otpauth://totp/SoccerOctopus:alexmorgan?secret=SECRET123&issuer=SoccerOctopus'

describe('AuthenticatorQrCode', () => {
  it('renders a local SVG QR code without exposing the setup URI text', () => {
    const wrapper = mount(AuthenticatorQrCode, {
      props: { value: setupUri },
    })

    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
    expect(wrapper.findAll('rect').length).toBeGreaterThan(100)
    expect(wrapper.html()).not.toContain('otpauth://')
    expect(wrapper.text()).not.toContain('SECRET123')
  })

  it('generates square QR matrices for longer authenticator setup URIs', () => {
    const longSetupUri = `otpauth://totp/SoccerOctopus:${'a'.repeat(80)}?secret=${'A'.repeat(32)}&issuer=SoccerOctopus`
    const matrix = createQrMatrix(longSetupUri)

    expect(matrix).toBeTruthy()
    expect(matrix.length).toBeGreaterThanOrEqual(21)
    expect(matrix.every((row) => row.length === matrix.length)).toBe(true)
    expect(matrix.flat().some(Boolean)).toBe(true)
  })
})
