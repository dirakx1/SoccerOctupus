import { api } from './api'

export const getPlans = () => api.get('/api/billing/plans')

export const createCheckout = (tier) => api.post('/api/billing/checkout', { tier })

export const getSubscription = () => api.get('/api/billing/subscription')

export const getUsage = () => api.get('/api/billing/usage')

export const createPortalSession = (payload = {}) => api.post('/api/billing/portal', payload)
