import { computed, getCurrentScope, onScopeDispose, ref, shallowRef, unref } from 'vue'

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
  const verificationStage = ref('first_factor')
  const password = ref('')
  const code = ref('')
  const target = ref('')
  const availableSecondFactors = ref([])
  const activeRequest = shallowRef(null)
  let requestId = 0

  const usesVerificationCode = computed(() => ['email_code', 'phone_code', 'totp', 'backup_code'].includes(strategy.value))
  const verificationCodeLabel = computed(() => {
    if (strategy.value === 'totp') return 'Authenticator code'
    if (strategy.value === 'backup_code') return 'Backup code'
    return 'Verification code'
  })
  const codePlaceholder = computed(() => strategy.value === 'backup_code' ? 'Enter backup code' : '123456')
  const codeInputMode = computed(() => strategy.value === 'backup_code' ? 'text' : 'numeric')
  const alternativeSecondFactor = computed(() => {
    if (verificationStage.value !== 'second_factor') return null
    if (strategy.value === 'totp') {
      return availableSecondFactors.value.find((factor) => factor.strategy === 'backup_code') || null
    }
    if (strategy.value === 'backup_code') {
      return availableSecondFactors.value.find((factor) => factor.strategy === 'totp') || null
    }
    return null
  })
  const canSwitchSecondFactor = computed(() => Boolean(alternativeSecondFactor.value))
  const alternativeSecondFactorLabel = computed(() => {
    if (alternativeSecondFactor.value?.strategy === 'backup_code') return 'Use a backup code instead'
    if (alternativeSecondFactor.value?.strategy === 'totp') return 'Use authenticator app instead'
    return ''
  })
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
    if (strategy.value === 'totp') {
      return 'Enter the 6-digit code from your authenticator app to continue.'
    }
    if (strategy.value === 'backup_code') {
      return 'Enter one of your backup codes to continue.'
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
    verificationStage.value = 'first_factor'
    password.value = ''
    code.value = ''
    target.value = ''
    availableSecondFactors.value = []
    error.value = ''
  }

  function isCurrent(request) {
    return activeRequest.value === request && !request.cancelled
  }

  function close() {
    isOpen.value = false
    loading.value = false
    resetInputs()
    activeRequest.value = null
  }

  function settle(request, err = null) {
    if (!request || request.settled) return
    request.settled = true
    if (err) {
      request.reject(err)
    } else {
      request.resolve()
    }
  }

  function rejectActiveRequest(message) {
    const request = activeRequest.value
    if (!request) return
    request.cancelled = true
    settle(request, new Error(message))
    activeRequest.value = null
  }

  async function continueVerification(verification, request) {
    if (!isCurrent(request)) return

    if (verification?.status === 'complete') {
      settle(request)
      close()
      return
    }

    if (verification?.status === 'needs_second_factor') {
      verificationStage.value = 'second_factor'
      const factors = verification?.supportedSecondFactors || []
      availableSecondFactors.value = factors
      const totpFactor = factors.find((factor) => factor.strategy === 'totp')
      const phoneFactor = factors.find((factor) => factor.strategy === 'phone_code')
      const backupCodeFactor = factors.find((factor) => factor.strategy === 'backup_code')
      const factor = totpFactor || phoneFactor || backupCodeFactor

      if (!factor) {
        throw new Error('Please sign in again before changing account security settings.')
      }

      strategy.value = factor.strategy
      code.value = ''
      target.value = factor.safeIdentifier || ''

      if (factor.strategy === 'phone_code') {
        await currentSession().prepareSecondFactorVerification({
          strategy: factor.strategy,
          phoneNumberId: factor.phoneNumberId,
        })
      }
      if (!isCurrent(request)) return
      return
    }

    verificationStage.value = 'first_factor'
    availableSecondFactors.value = []
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
      if (!isCurrent(request)) return
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

    rejectActiveRequest('Verification was superseded by a newer request.')
    title.value = options.title || 'Verify it is you'
    message.value = options.message || 'Enter your password to continue.'
    resetInputs()
    isOpen.value = true
    loading.value = true

    return new Promise((resolve, reject) => {
      const request = {
        id: ++requestId,
        resolve,
        reject,
        settled: false,
        cancelled: false,
      }
      activeRequest.value = request
      Promise.resolve()
        .then(() => activeSession.startVerification({ level: options.level || 'first_factor' }))
        .then((verification) => continueVerification(verification, request))
        .catch((err) => {
          if (!isCurrent(request)) return
          settle(request, err)
          close()
        })
        .finally(() => {
          if (isCurrent(request)) loading.value = false
        })
    })
  }

  async function submit() {
    const activeSession = currentSession()
    const request = activeRequest.value
    if (!activeSession || !isCurrent(request)) return

    loading.value = true
    error.value = ''

    let verification
    try {
      if (strategy.value === 'passkey') {
        verification = await activeSession.verifyWithPasskey()
      } else if (verificationStage.value === 'second_factor') {
        verification = await activeSession.attemptSecondFactorVerification({
          strategy: strategy.value,
          code: code.value,
        })
      } else {
        const attempt = usesVerificationCode.value
          ? { strategy: strategy.value, code: code.value }
          : { strategy: 'password', password: password.value }
        verification = await activeSession.attemptFirstFactorVerification(attempt)
      }
    } catch (err) {
      if (isCurrent(request)) error.value = clerkError(err, 'Unable to verify. Please try again.')
      if (isCurrent(request)) loading.value = false
      return
    }

    try {
      await continueVerification(verification, request)
    } catch (err) {
      if (isCurrent(request)) {
        settle(request, err)
        close()
      }
    } finally {
      if (isCurrent(request)) loading.value = false
    }
  }

  function switchSecondFactor() {
    const factor = alternativeSecondFactor.value
    if (!factor) return
    strategy.value = factor.strategy
    code.value = ''
    target.value = factor.safeIdentifier || ''
    error.value = ''
  }

  function cancel() {
    const request = activeRequest.value
    if (request) {
      request.cancelled = true
      settle(request, new Error('Verification was cancelled.'))
    }
    close()
  }

  async function runWithReverification(operation, options = {}) {
    const maxReverificationAttempts = Number.isInteger(options.maxReverificationAttempts)
      ? Math.max(0, options.maxReverificationAttempts)
      : 2
    const retryPolicy = typeof options.retryPolicy === 'string'
      ? { mode: options.retryPolicy }
      : (options.retryPolicy || { mode: 'reject' })

    if (retryPolicy.mode === 'verify_first') {
      await start(options)
      return operation()
    }
    let reverificationAttempts = 0
    let operationError = null

    while (true) {
      try {
        if (retryPolicy.mode === 'reconcile' && reverificationAttempts > 0) {
          return await retryPolicy.reconcile({
            attempt: reverificationAttempts,
            operationError,
          })
        }
        return await operation()
      } catch (err) {
        if (!isReverificationError(err) || reverificationAttempts >= maxReverificationAttempts) throw err
        if (retryPolicy.mode === 'reconcile' && typeof retryPolicy.reconcile !== 'function') {
          throw new TypeError('A reconcile function is required for the reconcile retry policy.')
        }
        operationError = err
        reverificationAttempts += 1
        await start(options)
        if (retryPolicy.mode === 'reject') throw operationError
      }
    }
  }

  if (getCurrentScope()) {
    onScopeDispose(() => {
      rejectActiveRequest('Verification was cancelled because the security screen was closed.')
      close()
    })
  }

  return {
    alternativeSecondFactorLabel,
    canSubmit,
    canSwitchSecondFactor,
    cancel,
    code,
    codeInputMode,
    codePlaceholder,
    copy,
    error,
    isOpen,
    loading,
    password,
    runWithReverification,
    start,
    strategy,
    submit,
    switchSecondFactor,
    title,
    usesVerificationCode,
    verificationCodeLabel,
    verificationStage,
  }
}
