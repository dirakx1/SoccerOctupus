import { computed } from 'vue'
import { useUser } from '@clerk/vue'

import { useAuthState } from '../lib/auth'

export function useCurrentUserProfile() {
  const auth = useAuthState()
  const { isLoaded, user } = useUser()

  const firstName = computed(() => {
    return user.value?.firstName || auth.state.user?.first_name || ''
  })

  const lastName = computed(() => {
    return user.value?.lastName || auth.state.user?.last_name || ''
  })

  const email = computed(() => {
    return user.value?.primaryEmailAddress?.emailAddress || auth.state.user?.email || ''
  })

  const avatarUrl = computed(() => {
    return user.value?.imageUrl || auth.state.user?.avatar_url || ''
  })

  const displayName = computed(() => {
    const fullName = `${firstName.value} ${lastName.value}`.trim()
    return user.value?.fullName || fullName || email.value || 'Account'
  })

  const initials = computed(() => {
    const source = displayName.value || email.value || 'A'
    return source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('') || 'A'
  })

  return {
    avatarUrl,
    displayName,
    email,
    firstName,
    initials,
    isLoaded,
    lastName,
    user,
  }
}
