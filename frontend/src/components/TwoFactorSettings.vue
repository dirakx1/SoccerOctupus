<template>
  <div class="two-factor-settings">
    <div class="security-summary">
      <div v-if="username" class="security-row">
        <span>Username</span>
        <strong>{{ username }}</strong>
      </div>
      <div class="security-row">
        <span>Authenticator app</span>
        <strong>{{ totpEnabled ? 'Enabled' : 'Not enabled' }}</strong>
      </div>
      <div class="security-row">
        <span>Backup codes</span>
        <strong>{{ backupCodeEnabled ? 'Enabled' : 'Not generated' }}</strong>
      </div>
    </div>

    <p v-if="error" class="error-box">{{ error }}</p>
    <p v-if="success" class="success-box">{{ success }}</p>

    <form v-if="reverificationRequired" class="setup-panel" @submit.prevent="submitReverification">
      <div class="setup-heading">
        <h3>Verify it is you</h3>
        <p>{{ reverificationCopy }}</p>
      </div>
      <label v-if="reverificationStrategy === 'password'" class="field">
        <span>Password</span>
        <input
          v-model="reverificationPassword"
          type="password"
          autocomplete="current-password"
          placeholder="Enter your password"
        />
      </label>
      <label v-if="usesVerificationCode" class="field">
        <span>Verification code</span>
        <input
          v-model.trim="reverificationCode"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          placeholder="123456"
        />
      </label>
      <div class="action-row">
        <button
          class="btn-primary"
          type="submit"
          :disabled="loading || !canSubmitReverification"
        >
          {{ loadingAction === 'reverify' ? 'Verifying...' : 'Continue' }}
        </button>
        <button class="btn-secondary" type="button" :disabled="loading" @click="cancelReverification">Cancel</button>
      </div>
    </form>

    <div v-if="backupCodes.length" class="backup-panel" data-testid="backup-codes-panel">
      <div class="backup-heading">
        <h3>Save these backup codes</h3>
        <p>Each code can be used once if you lose access to your authenticator app.</p>
      </div>
      <pre>{{ backupCodesText }}</pre>
      <div class="action-row">
        <button class="btn-secondary" type="button" @click="copyBackupCodes">Copy codes</button>
        <button class="btn-secondary" type="button" @click="downloadBackupCodes">Download codes</button>
      </div>
      <label class="checkbox-field">
        <input v-model="backupSaved" type="checkbox" />
        <span>I saved these backup codes</span>
      </label>
      <button class="btn-primary" type="button" :disabled="!backupSaved" @click="closeBackupCodes">
        Done
      </button>
    </div>

    <div v-if="!reverificationRequired && setupResource" class="setup-panel">
      <div class="setup-heading">
        <h3>Connect authenticator app</h3>
        <p>Scan this QR code with your authenticator app, then enter the 6-digit code it shows.</p>
      </div>
      <div v-if="setupResource.uri" class="qr-setup">
        <AuthenticatorQrCode :value="setupResource.uri" />
      </div>
      <button
        v-if="setupResource.secret"
        class="btn-link"
        type="button"
        @click="showManualSetup = !showManualSetup"
      >
        {{ showManualSetup ? 'Hide setup key' : 'Use setup key instead' }}
      </button>
      <label v-if="showManualSetup && setupResource.secret" class="readonly-field">
        <span>Setup key</span>
        <code>{{ setupResource.secret }}</code>
        <button class="btn-link" type="button" @click="copyText(setupResource.secret)">Copy setup key</button>
      </label>
      <label class="field">
        <span>Authenticator code</span>
        <input
          v-model.trim="setupCode"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          placeholder="123456"
        />
      </label>
      <div class="action-row">
        <button class="btn-primary" type="button" :disabled="loading || !setupCode" @click="verifySetup">
          {{ loadingAction === 'verify' ? 'Verifying...' : 'Verify and generate backup codes' }}
        </button>
        <button class="btn-secondary" type="button" :disabled="loading" @click="cancelSetup">Cancel</button>
      </div>
    </div>

    <div v-else-if="!reverificationRequired" class="action-row">
      <button
        v-if="!totpEnabled"
        class="btn-primary"
        type="button"
        :disabled="!canManage || loading"
        @click="startSetup"
      >
        {{ loadingAction === 'setup' ? 'Starting setup...' : 'Enable authenticator app' }}
      </button>
      <template v-else>
        <button class="btn-secondary" type="button" :disabled="!canManage || loading" @click="regenerateBackupCodes">
          {{ loadingAction === 'backup' ? 'Generating...' : 'Regenerate backup codes' }}
        </button>
        <button class="btn-danger" type="button" :disabled="!canManage || loading" @click="disableAuthenticator">
          {{ loadingAction === 'disable' ? 'Disabling...' : 'Disable authenticator app' }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

import AuthenticatorQrCode from './AuthenticatorQrCode.vue'

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  isLoaded: {
    type: Boolean,
    default: false,
  },
  session: {
    type: Object,
    default: null,
  },
})

const setupResource = ref(null)
const setupCode = ref('')
const showManualSetup = ref(false)
const reverificationResource = ref(null)
const reverificationStrategy = ref('')
const reverificationPassword = ref('')
const reverificationCode = ref('')
const reverificationTarget = ref('')
const pendingAction = ref('')
const backupCodes = ref([])
const backupSaved = ref(false)
const loadingAction = ref('')
const error = ref('')
const success = ref('')

const canManage = computed(() => props.isLoaded && Boolean(props.user))
const loading = computed(() => Boolean(loadingAction.value))
const username = computed(() => props.user?.username || '')
const totpEnabled = computed(() => Boolean(props.user?.totpEnabled))
const backupCodeEnabled = computed(() => Boolean(props.user?.backupCodeEnabled || backupCodes.value.length))
const backupCodesText = computed(() => backupCodes.value.join('\n'))
const reverificationRequired = computed(() => Boolean(reverificationResource.value || reverificationStrategy.value))
const usesVerificationCode = computed(() => ['email_code', 'phone_code'].includes(reverificationStrategy.value))
const canSubmitReverification = computed(() => {
  if (reverificationStrategy.value === 'password') return Boolean(reverificationPassword.value)
  if (usesVerificationCode.value) return Boolean(reverificationCode.value)
  if (reverificationStrategy.value === 'passkey') return true
  return false
})
const reverificationCopy = computed(() => {
  if (reverificationStrategy.value === 'email_code') {
    return `Enter the code sent to ${reverificationTarget.value || 'your email address'} to continue.`
  }
  if (reverificationStrategy.value === 'phone_code') {
    return `Enter the code sent to ${reverificationTarget.value || 'your phone'} to continue.`
  }
  if (reverificationStrategy.value === 'passkey') {
    return 'Use your passkey to continue with authenticator setup.'
  }
  return 'Enter your password to continue with authenticator setup.'
})

function clerkError(err, fallback) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || fallback
}

function isReverificationError(err) {
  return err?.errors?.some?.((entry) => entry.code === 'session_reverification_required') ||
    err?.response?.data?.errors?.some?.((entry) => entry.code === 'session_reverification_required')
}

function clearBackupCodes() {
  backupCodes.value = []
  backupSaved.value = false
}

function resetMessages() {
  error.value = ''
  success.value = ''
}

function clearReverification() {
  reverificationResource.value = null
  reverificationStrategy.value = ''
  reverificationPassword.value = ''
  reverificationCode.value = ''
  reverificationTarget.value = ''
  pendingAction.value = ''
}

async function reloadUser() {
  await props.user?.reload?.()
}

async function startSetup() {
  if (!props.user?.createTOTP) return

  loadingAction.value = 'setup'
  resetMessages()
  clearBackupCodes()
  showManualSetup.value = false

  try {
    setupResource.value = await props.user.createTOTP()
    setupCode.value = ''
  } catch (err) {
    if (isReverificationError(err)) {
      await startReverification('setup')
      return
    }
    error.value = clerkError(err, 'Unable to start authenticator setup.')
  } finally {
    loadingAction.value = ''
  }
}

async function startReverification(action) {
  if (!props.session?.startVerification) {
    error.value = 'Please sign in again before changing authenticator settings.'
    return
  }

  loadingAction.value = 'reverify'
  resetMessages()
  clearBackupCodes()
  setupResource.value = null
  setupCode.value = ''
  showManualSetup.value = false
  pendingAction.value = action

  try {
    const verification = await props.session.startVerification({ level: 'first_factor' })
    await continueReverification(verification)
  } catch (err) {
    clearReverification()
    error.value = clerkError(err, 'Unable to start verification. Please try again.')
  } finally {
    loadingAction.value = ''
  }
}

async function continueReverification(verification) {
  if (verification?.status === 'complete') {
    const action = pendingAction.value
    clearReverification()
    if (action === 'setup') await startSetup()
    return
  }

  reverificationResource.value = verification
  const factors = verification?.supportedFirstFactors || []
  const passwordFactor = factors.find((factor) => factor.strategy === 'password')
  const emailFactor = factors.find((factor) => factor.strategy === 'email_code')
  const phoneFactor = factors.find((factor) => factor.strategy === 'phone_code')
  const passkeyFactor = factors.find((factor) => factor.strategy === 'passkey')

  if (passwordFactor) {
    reverificationStrategy.value = 'password'
    return
  }

  if (emailFactor || phoneFactor) {
    const factor = emailFactor || phoneFactor
    reverificationStrategy.value = factor.strategy
    reverificationTarget.value = factor.safeIdentifier || ''
    const prepareParams = factor.strategy === 'email_code'
      ? { strategy: factor.strategy, emailAddressId: factor.emailAddressId }
      : { strategy: factor.strategy, phoneNumberId: factor.phoneNumberId, channel: factor.channel }
    reverificationResource.value = await props.session.prepareFirstFactorVerification(prepareParams)
    return
  }

  if (passkeyFactor) {
    reverificationStrategy.value = 'passkey'
    return
  }

  clearReverification()
  error.value = 'Please sign in again before changing authenticator settings.'
}

async function submitReverification() {
  if (!props.session) return

  loadingAction.value = 'reverify'
  resetMessages()

  try {
    let verification
    if (reverificationStrategy.value === 'passkey') {
      verification = await props.session.verifyWithPasskey()
    } else {
      const attempt = usesVerificationCode.value
        ? { strategy: reverificationStrategy.value, code: reverificationCode.value }
        : { strategy: 'password', password: reverificationPassword.value }
      verification = await props.session.attemptFirstFactorVerification(attempt)
    }
    await continueReverification(verification)
  } catch (err) {
    error.value = clerkError(err, 'Unable to verify. Please try again.')
  } finally {
    loadingAction.value = ''
  }
}

async function verifySetup() {
  if (!props.user?.verifyTOTP) return

  loadingAction.value = 'verify'
  resetMessages()

  try {
    const verified = await props.user.verifyTOTP({ code: setupCode.value })
    await showBackupCodes(verified)
    setupResource.value = null
    setupCode.value = ''
    showManualSetup.value = false
    success.value = 'Authenticator app enabled.'
    await reloadUser()
  } catch (err) {
    error.value = clerkError(err, 'Unable to verify this authenticator code.')
  } finally {
    loadingAction.value = ''
  }
}

async function showBackupCodes(source = null) {
  const generated = props.user?.createBackupCode
    ? await props.user.createBackupCode()
    : null
  backupCodes.value = generated?.codes?.length ? generated.codes : source?.backupCodes || []
  backupSaved.value = false
}

async function regenerateBackupCodes() {
  if (!props.user?.createBackupCode) return

  loadingAction.value = 'backup'
  resetMessages()
  clearBackupCodes()

  try {
    await showBackupCodes()
    success.value = 'New backup codes generated.'
    await reloadUser()
  } catch (err) {
    error.value = clerkError(err, 'Unable to generate backup codes.')
  } finally {
    loadingAction.value = ''
  }
}

async function disableAuthenticator() {
  if (!props.user?.disableTOTP) return

  loadingAction.value = 'disable'
  resetMessages()

  try {
    await props.user.disableTOTP()
    setupResource.value = null
    setupCode.value = ''
    showManualSetup.value = false
    clearBackupCodes()
    success.value = 'Authenticator app disabled.'
    await reloadUser()
  } catch (err) {
    error.value = clerkError(err, 'Unable to disable authenticator app.')
  } finally {
    loadingAction.value = ''
  }
}

function cancelSetup() {
  setupResource.value = null
  setupCode.value = ''
  showManualSetup.value = false
  resetMessages()
}

function cancelReverification() {
  clearReverification()
  resetMessages()
}

function closeBackupCodes() {
  if (!backupSaved.value) return
  clearBackupCodes()
}

async function copyText(value) {
  if (!value || !navigator.clipboard?.writeText) return
  await navigator.clipboard.writeText(value)
}

async function copyBackupCodes() {
  await copyText(backupCodesText.value)
}

function downloadBackupCodes() {
  if (!backupCodes.value.length || typeof Blob === 'undefined' || !URL.createObjectURL) return

  const blob = new Blob([`${backupCodesText.value}\n`], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'socceroctopus-backup-codes.txt'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

onBeforeUnmount(() => {
  clearBackupCodes()
  clearReverification()
})

defineExpose({
  backupCodes,
  clearBackupCodes,
})
</script>

<style scoped>
.two-factor-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.security-summary {
  display: grid;
  gap: 10px;
}

.security-row {
  align-items: center;
  border-bottom: 1px solid #0f3460;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding-bottom: 10px;
}

.security-row span {
  color: #a0aec0;
  font-size: 13px;
}

.security-row strong {
  color: #e0e0e0;
  font-size: 13px;
}

.setup-panel,
.backup-panel {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
}

.backup-heading h3,
.setup-heading h3 {
  color: #e0e0e0;
  font-size: 16px;
  margin-bottom: 4px;
}

.backup-heading p,
.setup-heading p {
  color: #a0aec0;
  font-size: 13px;
  line-height: 1.5;
}

.qr-setup {
  align-items: center;
  display: flex;
  justify-content: center;
  padding: 4px 0;
}

pre,
code {
  background: #050511;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #e0e0e0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  overflow-x: auto;
  padding: 10px 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.readonly-field,
.field,
.checkbox-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.readonly-field span,
.field span,
.checkbox-field span {
  color: #8888aa;
  font-size: 13px;
}

.checkbox-field {
  align-items: center;
  flex-direction: row;
}

input {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  padding: 12px 14px;
}

input:focus {
  border-color: #e2b714;
  outline: none;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.btn-primary,
.btn-secondary,
.btn-danger,
.btn-link {
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  min-height: 40px;
  padding: 10px 14px;
}

.btn-primary {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  border: none;
  color: #0a0a1a;
}

.btn-secondary {
  background: #0f3460;
  border: 1px solid #1f4c7a;
  color: #e0e0e0;
}

.btn-danger {
  background: #3d1a1a;
  border: 1px solid #c53030;
  color: #fc8181;
}

.btn-link {
  align-items: center;
  background: transparent;
  border: none;
  color: #e2b714;
  display: inline-flex;
  min-height: auto;
  padding: 0;
  text-decoration: none;
}

button:disabled {
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
</style>
