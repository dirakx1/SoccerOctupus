import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AtlasAuthLayout from './AtlasAuthLayout.vue'

describe('AtlasAuthLayout', () => {
  it('keeps the branded match intelligence composition decorative and exposes both content slots', () => {
    const wrapper = mount(AtlasAuthLayout, {
      slots: {
        intro: '<h1>Welcome back</h1><p>Continue to the tournament.</p>',
        default: '<form><label>Email <input type="email" /></label></form>',
      },
    })

    expect(wrapper.find('.atlas-auth-layout').exists()).toBe(true)
    expect(wrapper.find('.atlas-auth-visual').exists()).toBe(true)
    expect(wrapper.find('.atlas-auth-analysis').attributes('aria-hidden')).toBe('true')
    expect(wrapper.find('.analysis-card-score').text()).toContain('World Cup 2026')
    expect(wrapper.find('.analysis-card-stat').text()).toContain('48')
    expect(wrapper.find('.atlas-auth-brand img').attributes('aria-hidden')).toBe('true')
    expect(wrapper.find('h1').text()).toBe('Welcome back')
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('uses a composed desktop split and collapses visual detail before forms become cramped', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/ui/patterns/AtlasAuthLayout.vue'), 'utf8')

    expect(source).toContain('@media (max-width: 760px)')
    expect(source).toContain('grid-template-columns: minmax(23rem, .72fr) minmax(20rem, 1fr);')
    expect(source).toContain('.atlas-auth-visual::before, .atlas-auth-visual::after, .atlas-auth-copy, .atlas-auth-analysis, .atlas-auth-footnote { display: none; }')
    expect(source).toContain('.atlas-auth-layout { display: block;')
  })
})
