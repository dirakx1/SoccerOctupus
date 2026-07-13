<template>
  <div class="two-factor-settings">
    <div v-if="!setupResource" class="security-control-row">
      <div class="security-control-copy">
        <strong>Authenticator app</strong>
        <span>Use a verification code when you sign in.</span>
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
              ? "Starting setup..."
              : "Enable authenticator app"
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
                ? "Generating..."
                : "Regenerate backup codes"
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
                ? "Disabling..."
                : "Disable authenticator app"
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
        <strong>Replace existing backup codes?</strong>
        <p>
          Generating new codes immediately invalidates every current backup
          code. This cannot be undone.
        </p>
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
              ? "Generating..."
              : "Generate new codes"
          }}
        </button>
        <button
          class="btn-secondary"
          type="button"
          :disabled="loading"
          @click="cancelBackupRegeneration"
        >
          Cancel
        </button>
      </div>
    </div>

    <div
      v-if="backupCodes.length"
      class="backup-panel"
      data-testid="backup-codes-panel"
    >
      <div class="backup-heading">
        <h3>Save these backup codes</h3>
        <p>
          Each code can be used once if you lose access to your authenticator
          app. They are shown only now and are never stored by this app. Any
          copy or download you create is yours to keep secure.
        </p>
      </div>
      <pre>{{ backupCodesText }}</pre>
      <div class="action-row">
        <button class="btn-secondary" type="button" @click="copyBackupCodes">
          Copy codes
        </button>
        <button
          class="btn-secondary"
          type="button"
          @click="downloadBackupCodes"
        >
          Download codes
        </button>
      </div>
      <label class="checkbox-field">
        <input v-model="backupSaved" type="checkbox" />
        <span>I saved these backup codes</span>
      </label>
      <button
        class="btn-primary"
        type="button"
        :disabled="!backupSaved"
        @click="closeBackupCodes"
      >
        Done
      </button>
    </div>

    <div v-if="setupResource" class="setup-panel">
      <div class="setup-heading">
        <h3>Connect authenticator app</h3>
        <p>
          Scan this QR code with your authenticator app, then enter the 6-digit
          code it shows.
        </p>
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
            {{ showManualSetup ? "Hide setup key" : "Use setup key instead" }}
          </button>
        </div>
        <div class="setup-confirmation">
          <label
            v-if="showManualSetup && setupResource.secret"
            class="readonly-field"
          >
            <span>Setup key</span>
            <code>{{ setupResource.secret }}</code>
            <button
              class="btn-link"
              type="button"
              @click="copyText(setupResource.secret)"
            >
              Copy setup key
            </button>
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
            <button
              class="btn-primary"
              type="button"
              :disabled="loading || !setupCode"
              @click="verifySetup"
            >
              {{
                loadingAction === "verify"
                  ? "Verifying..."
                  : "Verify and continue"
              }}
            </button>
            <button
              class="btn-secondary"
              type="button"
              :disabled="loading"
              @click="cancelSetup"
            >
              Cancel
            </button>
          </div>
          <p class="setup-note">
            Backup codes are generated after verification.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";

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

const setupResource = ref(null);
const setupCode = ref("");
const showManualSetup = ref(false);
const backupCodes = ref([]);
const backupSaved = ref(false);
const confirmingBackupRegeneration = ref(false);
const loadingAction = ref("");
const error = ref("");
const success = ref("");

const canManage = computed(() => props.isLoaded && Boolean(props.user));
const loading = computed(() => Boolean(loadingAction.value));
const totpEnabled = computed(() => Boolean(props.user?.totpEnabled));
const backupCodesText = computed(() => backupCodes.value.join("\n"));

function clerkError(err, fallback) {
  return (
    err?.response?.data?.error ||
    err?.errors?.[0]?.longMessage ||
    err?.errors?.[0]?.message ||
    err?.message ||
    fallback
  );
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

async function runProtected(operation, message, options = {}) {
  if (!props.reverification?.runWithReverification) return operation();
  return props.reverification.runWithReverification(operation, {
    message,
    title: "Verify it is you",
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
      "Enter your password to continue with authenticator setup.",
    );
    setupCode.value = "";
  } catch (err) {
    error.value = clerkError(err, "Unable to start authenticator setup.");
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
      "Enter your password to continue with authenticator setup.",
    );
    await showBackupCodes(verified);
    setupResource.value = null;
    setupCode.value = "";
    showManualSetup.value = false;
    success.value = "Authenticator app enabled.";
    await reloadUser();
  } catch (err) {
    error.value = clerkError(err, "Unable to verify this authenticator code.");
  } finally {
    loadingAction.value = "";
  }
}

async function showBackupCodes(source = null, options = {}) {
  const generated = props.user?.createBackupCode
    ? await runProtected(
        () => props.user.createBackupCode(),
        "Enter your password to generate new backup codes.",
        options,
      )
    : null;
  backupCodes.value = generated?.codes?.length
    ? generated.codes
    : source?.backupCodes || [];
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
    success.value = "New backup codes generated.";
    await reloadUser();
  } catch (err) {
    error.value = clerkError(err, "Unable to generate backup codes.");
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
      "Enter your password to disable authenticator app sign-in.",
      { level: "multi_factor" },
    );
    setupResource.value = null;
    setupCode.value = "";
    showManualSetup.value = false;
    clearBackupCodes();
    success.value = "Authenticator app disabled.";
    await reloadUser();
  } catch (err) {
    error.value = clerkError(err, "Unable to disable authenticator app.");
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
  gap: 16px;
}

.security-control-row {
  align-items: center;
  display: flex;
  gap: 24px;
  justify-content: space-between;
}

.security-control-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.security-control-copy strong {
  color: #e0e0e0;
  font-size: 15px;
}

.security-control-copy span {
  color: #a0aec0;
  font-size: 13px;
  line-height: 1.45;
}

.security-control-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .security-control-row {
    align-items: stretch;
    flex-direction: column;
    gap: 16px;
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
  border-top: 1px solid #0f3460;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 20px;
}

.regeneration-confirmation {
  align-items: flex-start;
  background: #2f2510;
  border: 1px solid #8a6d1d;
  border-radius: 8px;
  display: flex;
  gap: 20px;
  justify-content: space-between;
  padding: 16px;
}

.regeneration-confirmation strong {
  color: #f6d860;
  display: block;
  font-size: 14px;
  margin-bottom: 5px;
}

.regeneration-confirmation p {
  color: #d7cba4;
  font-size: 13px;
  line-height: 1.5;
  max-width: 620px;
}

@media (max-width: 640px) {
  .regeneration-confirmation {
    flex-direction: column;
  }
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

.setup-content {
  align-items: center;
  display: grid;
  gap: 36px;
  grid-template-columns: minmax(260px, 0.8fr) minmax(300px, 1.2fr);
}

.setup-qr-column,
.setup-confirmation {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.setup-qr-column {
  align-items: center;
}

.setup-confirmation {
  justify-content: center;
}

.setup-note {
  color: #8888aa;
  font-size: 12px;
  line-height: 1.45;
}

@media (max-width: 760px) {
  .setup-content {
    align-items: stretch;
    gap: 24px;
    grid-template-columns: 1fr;
  }
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
