"""Encrypted storage for admin-managed runtime secrets."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .config import BASE_DIR

DEFAULT_KEY_PATH = BASE_DIR / "instance" / "settings-fernet.key"


class SecretStoreError(RuntimeError):
    """Base error for encrypted secret storage failures."""


class MissingSecretKeyError(SecretStoreError):
    """Raised when ciphertext exists but the root key file is unavailable."""


class InvalidSecretCiphertextError(SecretStoreError):
    """Raised when an encrypted secret cannot be authenticated or decrypted."""


class SecretStore:
    def __init__(self, key_path: Path | str | None = None):
        self.key_path = Path(key_path) if key_path is not None else DEFAULT_KEY_PATH
        self._fernet: Fernet | None = None

    def encrypt(self, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return self._get_fernet(create=True).encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str | None) -> str:
        if not token:
            return ""
        try:
            return self._get_fernet(create=False).decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise InvalidSecretCiphertextError(
                "Stored API key ciphertext could not be decrypted. Re-enter the key in admin settings."
            ) from exc

    def _get_fernet(self, create: bool) -> Fernet:
        if self._fernet is not None:
            return self._fernet

        if not self.key_path.exists():
            if not create:
                raise MissingSecretKeyError(
                    f"Encrypted API keys exist, but root key file is missing: {self.key_path}"
                )
            self._create_key_file()

        self._fernet = Fernet(self.key_path.read_bytes())
        return self._fernet

    def _create_key_file(self) -> None:
        self.key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.key_path.parent.chmod(0o700)
        except OSError:
            pass

        descriptor = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as key_file:
            key_file.write(Fernet.generate_key())
        try:
            self.key_path.chmod(0o600)
        except OSError:
            pass
