import { api } from './api'

export const getPlans = () => api.get('/api/billing/plans')

export const createCheckout = (tier) => api.post('/api/billing/checkout', { tier })

export const changePlan = (tier) => api.post('/api/billing/change-plan', { tier })

export const getSubscription = () => api.get('/api/billing/subscription')

export const getUsage = () => api.get('/api/billing/usage')

export const createPortalSession = (payload = {}) => api.post('/api/billing/portal', payload)

export const createPaymentMethodSession = (payload = {}) => api.post('/api/billing/payment-method', payload)
