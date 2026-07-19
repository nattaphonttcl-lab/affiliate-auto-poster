from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from app.core.exceptions import AppException


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _keystream(*, key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_secret(*, plaintext: str, secret_key: str) -> str:
    if not plaintext:
        raise AppException(status_code=400, detail="Credential cannot be empty")

    key = _derive_key(secret_key)
    nonce = secrets.token_bytes(16)
    payload = plaintext.encode("utf-8")
    stream = _keystream(key=key, nonce=nonce, length=len(payload))
    cipher = bytes(a ^ b for a, b in zip(payload, stream))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(nonce + tag + cipher)
    return token.decode("utf-8")


def decrypt_secret(*, ciphertext: str, secret_key: str) -> str:
    try:
        key = _derive_key(secret_key)
        raw = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
        if len(raw) < 48:
            raise ValueError("invalid payload")

        nonce = raw[:16]
        tag = raw[16:48]
        cipher = raw[48:]
        expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("invalid signature")

        stream = _keystream(key=key, nonce=nonce, length=len(cipher))
        plain = bytes(a ^ b for a, b in zip(cipher, stream))
        return plain.decode("utf-8")
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
        raise AppException(
            status_code=500, detail="Failed to decrypt provider credentials"
        ) from exc
