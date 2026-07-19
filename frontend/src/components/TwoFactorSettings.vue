<template>
  <div class="two-factor-settings">
    <div v-if="!setupResource" class="security-control-row">
      <div class="security-control-copy">
        <strong>{{ t("profile.twoFactor.authenticator") }}</strong>
        <span>{{ t("profile.twoFactor.description") }}</span>
      </div>
      <div class="security-control-actions">
        <button
          v-if="!totpEnabled"
          class="btn-primary"
          type="button"
          :disabled="!canManage || loading"
          @click="startSetup"
        >
          {{
            loadingAction === "setup"
              ? t("profile.twoFactor.starting")
              : t("profile.twoFactor.enable")
          }}
        </button>
        <template v-else>
          <button
            class="btn-secondary"
            type="button"
            :disabled="!canManage || loading || confirmingBackupRegeneration"
            @click="requestBackupRegeneration"
          >
            {{
              loadingAction === "backup"
                ? t("profile.twoFactor.generating")
                : t("profile.twoFactor.regenerate")
            }}
          </button>
          <button
            class="btn-danger"
            type="button"
            :disabled="!canManage || loading"
            @click="disableAuthenticator"
          >
            {{
              loadingAction === "disable"
                ? t("profile.twoFactor.disabling")
                : t("profile.twoFactor.disable")
            }}
          </button>
        </template>
      </div>
    </div>

    <p v-if="error" class="error-box">{{ error }}</p>
    <p v-if="success" class="success-box">{{ success }}</p>

    <div
      v-if="confirmingBackupRegeneration"
      class="regeneration-confirmation"
      role="alert"
      data-testid="backup-regeneration-confirmation"
    >
      <div>
        <strong>{{ t("profile.twoFactor.replaceTitle") }}</strong>
        <p>{{ t("profile.twoFactor.replaceDescription") }}</p>
      </div>
      <div class="action-row">
        <button
          class="btn-danger"
          type="button"
          :disabled="loading"
          @click="regenerateBackupCodes"
        >
          {{
            loadingAction === "backup"
              ? t("profile.twoFactor.generating")
              : t("profile.twoFactor.generate")
          }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="loading"
          @click="cancelBackupRegeneration"
        >
          {{ t("profile.twoFactor.cancel") }}
        </button>
      </div>
    </div>

    <div
      v-if="backupCodes.length"
      class="backup-panel"
      data-testid="backup-codes-panel"
    >
      <div class="backup-heading">
        <h3>{{ t("profile.twoFactor.backupTitle") }}</h3>
        <p>{{ t("profile.twoFactor.backupDescription") }}</p>
      </div>
      <pre>{{ backupCodesText }}</pre>
      <div class="action-row">
        <button class="btn-secondary" type="button" @click="copyBackupCodes">
          {{ t("profile.twoFactor.copyCodes") }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          @click="downloadBackupCodes"
        >
          {{ t("profile.twoFactor.downloadCodes") }}
        </button>
      </div>
      <label class="checkbox-field">
        <input v-model="backupSaved" type="checkbox" />
        <span>{{ t("profile.twoFactor.savedCodes") }}</span>
      </label>
      <button
        class="btn-primary"
        type="button"
        :disabled="!backupSaved"
        @click="closeBackupCodes"
      >
        {{ t("profile.twoFactor.done") }}
      </button>
    </div>

    <div v-if="setupResource" class="setup-panel">
      <div class="setup-heading">
        <h3>{{ t("profile.twoFactor.connectTitle") }}</h3>
        <p>{{ t("profile.twoFactor.connectDescription") }}</p>
      </div>
      <div class="setup-content">
        <div class="setup-qr-column">
          <div v-if="setupResource.uri" class="qr-setup">
            <AuthenticatorQrCode :value="setupResource.uri" />
          </div>
          <button
            v-if="setupResource.secret"
            class="btn-link"
            type="button"
            @click="showManualSetup = !showManualSetup"
          >
            {{
              showManualSetup
                ? t("profile.twoFactor.hideSetupKey")
                : t("profile.twoFactor.useSetupKey")
            }}
          </button>
        </div>
        <div class="setup-confirmation">
          <label
            v-if="showManualSetup && setupResource.secret"
            class="readonly-field"
          >
            <span>{{ t("profile.twoFactor.setupKey") }}</span>
            <code>{{ setupResource.secret }}</code>
            <button
              class="btn-link"
              type="button"
              @click="copyText(setupResource.secret)"
            >
              {{ t("profile.twoFactor.copySetupKey") }}
            </button>
          </label>
          <label class="field">
            <span>{{ t("profile.twoFactor.authenticatorCode") }}</span>
            <input
              v-model.trim="setupCode"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              placeholder="123456"
            />
          </label>
          <div class="action-row">
            <button
              class="btn-primary"
              type="button"
              :disabled="loading || !setupCode"
              @click="verifySetup"
            >
              {{
                loadingAction === "verify"
                  ? t("profile.twoFactor.verifying")
                  : t("profile.twoFactor.verify")
              }}
            </button>
            <button
              class="btn-secondary"
              type="button"
              :disabled="loading"
              @click="cancelSetup"
            >
              {{ t("profile.twoFactor.cancel") }}
            </button>
          </div>
          <p class="setup-note">
            {{ t("profile.twoFactor.backupAfterVerification") }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";

import { userFacingError } from "../lib/userFacingError";
import AuthenticatorQrCode from "./AuthenticatorQrCode.vue";

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  isLoaded: {
    type: Boolean,
    default: false,
  },
  reverification: {
    type: Object,
    default: null,
  },
});

const { t } = useI18n();

const setupResource = ref(null);
const setupCode = ref("");
const showManualSetup = ref(false);
const backupCodes = ref([]);
const backupSaved = ref(false);
const confirmingBackupRegeneration = ref(false);
const loadingAction = ref("");
const error = ref("");
const success = ref("");
const committedTotpEnabled = ref(null);

const canManage = computed(() => props.isLoaded && Boolean(props.user));
const loading = computed(() => Boolean(loadingAction.value));
const totpEnabled = computed(() =>
  committedTotpEnabled.value === null
    ? Boolean(props.user?.totpEnabled)
    : committedTotpEnabled.value,
);
const backupCodesText = computed(() => backupCodes.value.join("\n"));

function clerkError(err, fallback) {
  return userFacingError(err, fallback);
}

function clearBackupCodes() {
  backupCodes.value = [];
  backupSaved.value = false;
}

function requestBackupRegeneration() {
  resetMessages();
  clearBackupCodes();
  confirmingBackupRegeneration.value = true;
}

function cancelBackupRegeneration() {
  confirmingBackupRegeneration.value = false;
}

function resetMessages() {
  error.value = "";
  success.value = "";
}

async function reloadUser() {
  await props.user?.reload?.();
}

function isAlreadyConnectedError(err) {
  const message = clerkError(err, "").toLowerCase();
  return (
    message.includes("already") &&
    (message.includes("connect") || message.includes("enabled"))
  );
}

async function runProtected(operation, message, options = {}) {
  if (!props.reverification?.runWithReverification) return operation();
  return props.reverification.runWithReverification(operation, {
    message,
    retryPolicy: "verify_first",
    title: t("profile.twoFactor.verifyIdentityTitle"),
    ...options,
  });
}

async function startSetup() {
  if (!props.user?.createTOTP) return;

  loadingAction.value = "setup";
  resetMessages();
  clearBackupCodes();
  showManualSetup.value = false;

  try {
    setupResource.value = await runProtected(
      () => props.user.createTOTP(),
      t("profile.twoFactor.reverifySetup"),
    );
    setupCode.value = "";
  } catch (err) {
    if (isAlreadyConnectedError(err)) {
      try {
        await reloadUser();
        if (props.user?.totpEnabled) {
          committedTotpEnabled.value = true;
          setupResource.value = null;
          error.value = t("profile.twoFactor.alreadyEnabled");
          return;
        }
      } catch (reloadErr) {
        error.value = clerkError(
          reloadErr,
          t("profile.twoFactor.setupRefreshError"),
        );
        return;
      }
    }
    error.value = clerkError(err, t("profile.twoFactor.startError"));
  } finally {
    loadingAction.value = "";
  }
}

async function verifySetup() {
  if (!props.user?.verifyTOTP) return;

  loadingAction.value = "verify";
  resetMessages();

  try {
    const verified = await runProtected(
      () => props.user.verifyTOTP({ code: setupCode.value }),
      t("profile.twoFactor.reverifySetup"),
    );
    committedTotpEnabled.value = true;
    setupResource.value = null;
    setupCode.value = "";
    showManualSetup.value = false;

    let backupError = null;
    try {
      await showBackupCodes(verified);
    } catch (err) {
      backupError = clerkError(err, t("profile.twoFactor.backupError"));
    }

    let refreshError = null;
    try {
      await reloadUser();
    } catch (err) {
      refreshError = t("profile.twoFactor.enabledRefreshError", {
        error: clerkError(err, t("profile.twoFactor.refreshStateError")),
      });
    }

    if (backupError && refreshError) {
      error.value = `${backupError} ${refreshError}`;
    } else if (backupError) {
      error.value = t("profile.twoFactor.enabledBackupError", {
        error: backupError.toLowerCase(),
      });
    } else if (refreshError) {
      error.value = refreshError;
    } else {
      success.value = t("profile.twoFactor.enabled");
    }
  } catch (err) {
    error.value = clerkError(err, t("profile.twoFactor.verifyError"));
  } finally {
    loadingAction.value = "";
  }
}

async function showBackupCodes(source = null, options = {}) {
  if (source?.backupCodes?.length) {
    backupCodes.value = source.backupCodes;
    backupSaved.value = false;
    return;
  }

  const generated = props.user?.createBackupCode
    ? await runProtected(
        () => props.user.createBackupCode(),
        t("profile.twoFactor.reverifyBackup"),
        options,
      )
    : null;
  if (!generated?.codes?.length) {
    throw new Error(t("profile.twoFactor.missingBackupCodes"));
  }
  backupCodes.value = generated.codes;
  backupSaved.value = false;
}

async function regenerateBackupCodes() {
  if (!props.user?.createBackupCode) return;

  loadingAction.value = "backup";
  resetMessages();
  clearBackupCodes();

  try {
    await showBackupCodes(null, { level: "multi_factor" });
    confirmingBackupRegeneration.value = false;
    committedTotpEnabled.value = true;
    try {
      await reloadUser();
      success.value = t("profile.twoFactor.backupGenerated");
    } catch (err) {
      error.value = t("profile.twoFactor.backupRefreshError", {
        error: clerkError(err, t("profile.twoFactor.refreshStateError")),
      });
    }
  } catch (err) {
    error.value = clerkError(err, t("profile.twoFactor.generateError"));
  } finally {
    loadingAction.value = "";
  }
}

async function disableAuthenticator() {
  if (!props.user?.disableTOTP) return;

  loadingAction.value = "disable";
  resetMessages();

  try {
    await runProtected(
      () => props.user.disableTOTP(),
      t("profile.twoFactor.reverifyDisable"),
      { level: "multi_factor" },
    );
    committedTotpEnabled.value = false;
    setupResource.value = null;
    setupCode.value = "";
    showManualSetup.value = false;
    clearBackupCodes();
    try {
      await reloadUser();
      success.value = t("profile.twoFactor.disabled");
    } catch (err) {
      error.value = t("profile.twoFactor.disabledRefreshError", {
        error: clerkError(err, t("profile.twoFactor.refreshStateError")),
      });
    }
  } catch (err) {
    error.value = clerkError(err, t("profile.twoFactor.disableError"));
  } finally {
    loadingAction.value = "";
  }
}

function cancelSetup() {
  setupResource.value = null;
  setupCode.value = "";
  showManualSetup.value = false;
  resetMessages();
}

function closeBackupCodes() {
  if (!backupSaved.value) return;
  clearBackupCodes();
}

async function copyText(value) {
  if (!value || !navigator.clipboard?.writeText) return;
  await navigator.clipboard.writeText(value);
}

async function copyBackupCodes() {
  await copyText(backupCodesText.value);
}

function downloadBackupCodes() {
  if (
    !backupCodes.value.length ||
    typeof Blob === "undefined" ||
    !URL.createObjectURL
  )
    return;

  const blob = new Blob([`${backupCodesText.value}\n`], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "socceroctopus-backup-codes.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

onBeforeUnmount(() => {
  confirmingBackupRegeneration.value = false;
  clearBackupCodes();
});

defineExpose({
  backupCodes,
  clearBackupCodes,
});
</script>

<style scoped>
.two-factor-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.security-control-row {
  align-items: center;
  border-top: var(--border-width-thin) solid var(--color-border);
  display: grid;
  gap: var(--space-6);
  grid-template-columns: minmax(15rem, 32rem) auto;
  padding-top: var(--space-5);
}

.security-control-copy {
  border-left: var(--border-width-strong) solid var(--color-accent);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-left: var(--space-3);
}

.security-control-copy strong {
  color: var(--color-text);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
}

.security-control-copy span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.security-control-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .security-control-row {
    align-items: stretch;
    gap: var(--space-4);
    grid-template-columns: 1fr;
  }

  .security-control-actions,
  .security-control-actions .btn-primary,
  .security-control-actions .btn-secondary,
  .security-control-actions .btn-danger {
    width: 100%;
  }
}

.setup-panel,
.backup-panel {
  border-top: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-top: var(--space-5);
}

.regeneration-confirmation {
  align-items: flex-start;
  background: var(--color-warning-surface);
  border-left: var(--border-width-strong) solid var(--color-warning);
  display: flex;
  gap: var(--space-5);
  justify-content: space-between;
  padding: var(--space-4);
}

.regeneration-confirmation strong {
  color: var(--color-warning);
  display: block;
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-1);
}

.regeneration-confirmation p {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  max-width: 620px;
}

@media (max-width: 640px) {
  .regeneration-confirmation {
    flex-direction: column;
  }
}

.backup-heading h3,
.setup-heading h3 {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  margin-bottom: var(--space-1);
}

.backup-heading p,
.setup-heading p {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.qr-setup {
  align-items: center;
  display: flex;
  justify-content: center;
  padding: var(--space-1) 0;
}

.setup-content {
  align-items: center;
  display: grid;
  gap: var(--space-8);
  grid-template-columns: minmax(260px, 0.8fr) minmax(300px, 1.2fr);
}

.setup-qr-column,
.setup-confirmation {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.setup-qr-column {
  align-items: center;
}

.setup-confirmation {
  justify-content: center;
}

.setup-note {
  color: var(--color-text-subtle);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-relaxed);
}

@media (max-width: 760px) {
  .setup-content {
    align-items: stretch;
    gap: var(--space-6);
    grid-template-columns: 1fr;
  }
}

pre,
code {
  background: var(--color-surface-inset);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-family: var(--font-family-data);
  font-size: var(--font-size-sm);
  overflow-x: auto;
  padding: var(--space-3);
  white-space: pre-wrap;
  word-break: break-word;
}

.readonly-field,
.field,
.checkbox-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.readonly-field span,
.field span,
.checkbox-field span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.checkbox-field {
  align-items: center;
  flex-direction: row;
}

input {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: var(--font-size-sm);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
}

input:focus-visible,
button:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.btn-primary,
.btn-secondary,
.btn-danger,
.btn-link {
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-4);
}

.btn-primary {
  background: var(--color-accent);
  border: 0;
  color: var(--color-accent-contrast);
}

.btn-secondary {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border-strong);
  color: var(--color-text);
}

.btn-danger {
  background: var(--color-danger-surface);
  border: var(--border-width-thin) solid var(--color-danger);
  color: var(--color-danger);
}

.btn-link {
  align-items: center;
  background: transparent;
  border: none;
  color: var(--color-accent);
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
  font-size: var(--font-size-sm);
  padding: var(--space-3);
}

.error-box {
  background: var(--color-danger-surface);
  border: var(--border-width-thin) solid var(--color-danger);
  color: var(--color-danger);
}

.success-box {
  background: var(--color-success-surface);
  border: var(--border-width-thin) solid var(--color-success);
  color: var(--color-success);
}
</style>
