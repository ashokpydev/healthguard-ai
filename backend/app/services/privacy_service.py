from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets


class PrivacyService:
    """Small app-level encryption helper for PHI persisted by the demo app.

    Production deployments should back HEALTHGUARD_ENCRYPTION_KEY with a KMS or
    vault-managed secret and rotate it through a proper envelope-encryption plan.
    """

    prefix = "enc:v1:"

    def __init__(self) -> None:
        key_material = os.getenv("HEALTHGUARD_ENCRYPTION_KEY", "healthguard-local-development-key")
        self._key = hashlib.sha256(key_material.encode("utf-8")).digest()

    def encrypt_text(self, value: str) -> str:
        if not value or value.startswith(self.prefix):
            return value
        plain = value.encode("utf-8")
        nonce = secrets.token_bytes(16)
        cipher = self._xor(plain, nonce)
        tag = hmac.new(self._key, nonce + cipher, hashlib.sha256).digest()
        return self.prefix + base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")

    def decrypt_text(self, value: str) -> str:
        if not value or not value.startswith(self.prefix):
            return value
        try:
            packed = base64.urlsafe_b64decode(value[len(self.prefix) :].encode("ascii"))
            nonce, tag, cipher = packed[:16], packed[16:48], packed[48:]
            expected = hmac.new(self._key, nonce + cipher, hashlib.sha256).digest()
            if not hmac.compare_digest(tag, expected):
                raise ValueError("Encrypted PHI failed integrity validation.")
            plain = self._xor(cipher, nonce)
            return plain.decode("utf-8")
        except Exception as exc:
            raise ValueError("Unable to decrypt stored PHI.") from exc

    def _xor(self, payload: bytes, nonce: bytes) -> bytes:
        stream = bytearray()
        counter = 0
        while len(stream) < len(payload):
            stream.extend(hashlib.sha256(self._key + nonce + counter.to_bytes(4, "big")).digest())
            counter += 1
        return bytes(item ^ stream[index] for index, item in enumerate(payload))
