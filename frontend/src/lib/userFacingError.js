function extractErrorMessage(err) {
  return err?.response?.data?.error
    || err?.errors?.[0]?.longMessage
    || err?.errors?.[0]?.message
    || err?.message
    || ''
}

export function userFacingError(err, fallback) {
  const message = extractErrorMessage(err)
  if (!message || /\bclerk\b/i.test(message)) return fallback
  return message
}
