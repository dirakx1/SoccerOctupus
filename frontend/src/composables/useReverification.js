import { computed, ref, unref } from 'vue'

function valueOf(source) {
  return typeof source === 'function' ? source() : unref(source)
}

export function clerkError(err, fallback) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || fallback
}

export function isReverificationError(err) {
  return Boolean(
    err?.errors?.some?.((entry) => entry.code === 'session_reverification_required') ||
    err?.response?.data?.errors?.some?.((entry) => entry.code === 'session_reverification_required')
  )
}

export function useReverification({ session } = {}) {
  const isOpen = ref(false)
  const loading = ref(false)
  const error = ref('')
  const title = ref('Verify it is you')
  const message = ref('Verify your identity to continue.')
  const strategy = ref('')
  const password = ref('')
  const code = ref('')
  const target = ref('')
  const pending = ref(null)

  const usesVerificationCode = computed(() => ['email_code', 'phone_code'].includes(strategy.value))
  const copy = computed(() => {
    if (strategy.value === 'email_code') {
      return `Enter the code sent to ${target.value || 'your email address'} to continue.`
    }
    if (strategy.value === 'phone_code') {
      return `Enter the code sent to ${target.value || 'your phone'} to continue.`
    }
    if (strategy.value === 'passkey') {
      return 'Use your passkey to continue.'
    }
    return message.value
  })
  const canSubmit = computed(() => {
    if (strategy.value === 'password') return Boolean(password.value)
    if (usesVerificationCode.value) return Boolean(code.value)
    if (strategy.value === 'passkey') return true
    return false
  })

  function currentSession() {
    return valueOf(session)
  }

  function resetInputs() {
    strategy.value = ''
    password.value = ''
    code.value = ''
    target.value = ''
    error.value = ''
  }

  function close() {
    isOpen.value = false
    loading.value = false
    resetInputs()
    pending.value = null
  }

  function settle(err = null) {
    const active = pending.value
    pending.value = null
    if (err) {
      active?.reject(err)
    } else {
      active?.resolve()
    }
  }

  async function continueVerification(verification) {
    if (verification?.status === 'complete') {
      settle()
      close()
      return
    }

    const factors = verification?.supportedFirstFactors || []
    const passwordFactor = factors.find((factor) => factor.strategy === 'password')
    const emailFactor = factors.find((factor) => factor.strategy === 'email_code')
    const phoneFactor = factors.find((factor) => factor.strategy === 'phone_code')
    const passkeyFactor = factors.find((factor) => factor.strategy === 'passkey')

    if (passwordFactor) {
      strategy.value = 'password'
      return
    }

    if (emailFactor || phoneFactor) {
      const factor = emailFactor || phoneFactor
      strategy.value = factor.strategy
      target.value = factor.safeIdentifier || ''
      const prepareParams = factor.strategy === 'email_code'
        ? { strategy: factor.strategy, emailAddressId: factor.emailAddressId }
        : { strategy: factor.strategy, phoneNumberId: factor.phoneNumberId, channel: factor.channel }
      await currentSession().prepareFirstFactorVerification(prepareParams)
      return
    }

    if (passkeyFactor) {
      strategy.value = 'passkey'
      return
    }

    throw new Error('Please sign in again before changing account security settings.')
  }

  async function start(options = {}) {
    const activeSession = currentSession()
    if (!activeSession?.startVerification) {
      throw new Error('Please sign in again before changing account security settings.')
    }

    title.value = options.title || 'Verify it is you'
    message.value = options.message || 'Enter your password to continue.'
    resetInputs()
    isOpen.value = true
    loading.value = true

    return new Promise((resolve, reject) => {
      pending.value = { resolve, reject }
      activeSession.startVerification({ level: options.level || 'first_factor' })
        .then(continueVerification)
        .catch((err) => {
          settle(err)
          close()
        })
        .finally(() => {
          loading.value = false
        })
    })
  }

  async function submit() {
    const activeSession = currentSession()
    if (!activeSession) return

    loading.value = true
    error.value = ''

    try {
      let verification
      if (strategy.value === 'passkey') {
        verification = await activeSession.verifyWithPasskey()
      } else {
        const attempt = usesVerificationCode.value
          ? { strategy: strategy.value, code: code.value }
          : { strategy: 'password', password: password.value }
        verification = await activeSession.attemptFirstFactorVerification(attempt)
      }
      await continueVerification(verification)
    } catch (err) {
      error.value = clerkError(err, 'Unable to verify. Please try again.')
    } finally {
      loading.value = false
    }
  }

  function cancel() {
    const err = new Error('Verification was cancelled.')
    settle(err)
    close()
  }

  async function runWithReverification(operation, options = {}) {
    try {
      return await operation()
    } catch (err) {
      if (!isReverificationError(err)) throw err
      await start(options)
      return operation()
    }
  }

  return {
    canSubmit,
    cancel,
    code,
    copy,
    error,
    isOpen,
    loading,
    password,
    runWithReverification,
    start,
    strategy,
    submit,
    title,
    usesVerificationCode,
  }
}
