<template>
  <div class="profile-page">
    <header class="profile-header">
      <div>
        <div class="eyebrow">Account</div>
        <h1>Profile settings</h1>
        <p>Update your Clerk profile and password for SoccerOctopus.</p>
      </div>
      <img v-if="avatarUrl" class="avatar" :src="avatarUrl" alt="Profile avatar" />
    </header>

    <div class="profile-grid">
      <section class="profile-card">
        <h2>Personal details</h2>
        <p class="card-copy">These fields are stored in Clerk and synced into the local account table.</p>

        <form class="profile-form" @submit.prevent="updateProfile">
          <div class="name-grid">
            <label class="field">
              <span>First name</span>
              <input v-model.trim="profileForm.firstName" type="text" autocomplete="given-name" placeholder="Alex" />
            </label>

            <label class="field">
              <span>Last name</span>
              <input v-model.trim="profileForm.lastName" type="text" autocomplete="family-name" placeholder="Morgan" />
            </label>
          </div>

          <label class="field">
            <span>Email address</span>
            <input :value="emailAddress" type="email" disabled />
          </label>

          <p v-if="profileError" class="error-box">{{ profileError }}</p>
          <p v-if="profileSuccess" class="success-box">{{ profileSuccess }}</p>

          <button class="btn-primary" :disabled="profileLoading || !isLoaded || !user">
            {{ profileLoading ? 'Saving...' : 'Save profile' }}
          </button>
        </form>
      </section>

      <section class="profile-card">
        <h2>Change password</h2>
        <p class="card-copy">Enter your current password, then confirm your new password twice.</p>

        <form class="profile-form" @submit.prevent="updatePassword">
          <label class="field">
            <span>Current password</span>
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              autocomplete="current-password"
              required
              placeholder="Enter current password"
            />
          </label>

          <label class="field">
            <span>New password</span>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              autocomplete="new-password"
              required
              minlength="8"
              placeholder="Enter new password"
            />
          </label>

          <label class="field">
            <span>Confirm new password</span>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              autocomplete="new-password"
              required
              minlength="8"
              placeholder="Repeat new password"
            />
          </label>

          <p v-if="passwordError" class="error-box">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success-box">{{ passwordSuccess }}</p>

          <button class="btn-primary" :disabled="passwordLoading || !isLoaded || !user">
            {{ passwordLoading ? 'Updating...' : 'Update password' }}
          </button>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useUser } from '@clerk/vue'

import { api } from '../lib/api'
import { setAuthState } from '../lib/auth'

const { isLoaded, user } = useUser()

const profileLoading = ref(false)
const passwordLoading = ref(false)
const profileError = ref('')
const passwordError = ref('')
const profileSuccess = ref('')
const passwordSuccess = ref('')

const profileForm = reactive({
  firstName: '',
  lastName: '',
})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const emailAddress = computed(() => user.value?.primaryEmailAddress?.emailAddress || '')
const avatarUrl = computed(() => user.value?.imageUrl || '')

watch(
  user,
  (currentUser) => {
    profileForm.firstName = currentUser?.firstName || ''
    profileForm.lastName = currentUser?.lastName || ''
  },
  { immediate: true }
)

function clerkError(err, fallback) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || fallback
}

async function refreshLocalUser() {
  const res = await api.get('/api/me')
  setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
}

async function updateProfile() {
  if (!isLoaded.value || !user.value) return

  profileLoading.value = true
  profileError.value = ''
  profileSuccess.value = ''

  try {
    await user.value.update({
      firstName: profileForm.firstName,
      lastName: profileForm.lastName,
    })
    await user.value.reload()
    await refreshLocalUser()
    profileSuccess.value = 'Profile updated.'
  } catch (err) {
    profileError.value = clerkError(err, 'Unable to update your profile. Please try again.')
  } finally {
    profileLoading.value = false
  }
}

function validatePasswordForm() {
  if (!passwordForm.currentPassword) {
    return 'Enter your current password.'
  }

  if (passwordForm.newPassword.length < 8) {
    return 'New password must be at least 8 characters.'
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    return 'New passwords do not match.'
  }

  if (passwordForm.currentPassword === passwordForm.newPassword) {
    return 'New password must be different from your current password.'
  }

  return ''
}

async function updatePassword() {
  if (!isLoaded.value || !user.value) return

  passwordError.value = validatePasswordForm()
  passwordSuccess.value = ''
  if (passwordError.value) return

  passwordLoading.value = true

  try {
    await user.value.updatePassword({
      currentPassword: passwordForm.currentPassword,
      newPassword: passwordForm.newPassword,
      signOutOfOtherSessions: true,
    })
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordSuccess.value = 'Password updated. Other sessions were signed out.'
  } catch (err) {
    passwordError.value = clerkError(err, 'Unable to update your password. Check your current password and try again.')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.profile-header {
  align-items: center;
  background: linear-gradient(135deg, #16213e, #0f3460);
  border: 1px solid #1f4c7a;
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  padding: 28px;
}

.eyebrow {
  color: #e2b714;
  font-size: 12px;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  text-transform: uppercase;
}

h1,
h2 {
  color: #e0e0e0;
}

h1 {
  font-size: 34px;
  margin-bottom: 8px;
}

h2 {
  font-size: 22px;
  margin-bottom: 8px;
}

.profile-header p,
.card-copy {
  color: #a0aec0;
  font-size: 14px;
  line-height: 1.5;
}

.avatar {
  border: 2px solid #e2b714;
  border-radius: 999px;
  height: 72px;
  object-fit: cover;
  width: 72px;
}

.profile-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  padding: 28px;
}

.profile-form {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 16px;
  margin-top: 22px;
}

.name-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #8888aa;
  font-size: 13px;
}

input {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  padding: 12px 14px;
}

input:disabled {
  color: #8888aa;
  cursor: not-allowed;
  opacity: 0.8;
}

input:focus {
  border-color: #e2b714;
  outline: none;
}

.btn-primary {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  border: none;
  border-radius: 10px;
  color: #0a0a1a;
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
  padding: 13px 24px;
  transition: opacity 0.2s;
}

.profile-form .btn-primary {
  margin-top: auto;
}

.btn-primary:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box,
.success-box {
  border-radius: 8px;
  font-size: 13px;
  padding: 12px 14px;
}

.error-box {
  background: #3d1a1a;
  border: 1px solid #c53030;
  color: #fc8181;
}

.success-box {
  background: #123322;
  border: 1px solid #38a169;
  color: #9ae6b4;
}

@media (max-width: 860px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .profile-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 20px;
  }

  .name-grid {
    grid-template-columns: 1fr;
  }
}
</style>
