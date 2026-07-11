"""Transparent envelope encryption for secrets stored at rest.

Third-party credentials (GitHub PATs, CMS API keys/secrets) must not sit in the
database in plaintext. This encrypts them with a key from the environment
(SECRET_ENCRYPTION_KEY, a Fernet key) before storage and decrypts on read.

Design goals:
- Backward compatible: values are tagged with a version prefix, so legacy
  plaintext rows (no prefix) still read correctly and get re-encrypted on next
  write.
- Graceful degradation: if no key is configured (or the `cryptography` package
  is unavailable, e.g. a minimal local install), values are stored as-is and a
  warning is logged - the app keeps working, just without at-rest encryption.

Generate a key:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Set it as:       SECRET_ENCRYPTION_KEY=<that value>
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("omnirank.crypto")

_PREFIX = "enc:v1:"
_warned = False


def _fernet():
    key = os.environ.get("SECRET_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except BaseException as exc:  # missing lib, broken native backend, or bad key
        # note: a broken `cryptography` native build raises pyo3 PanicException,
        # which is a BaseException, so we must catch broadly here.
        logger.warning("Secret encryption unavailable (%s); storing plaintext", exc)
        return None


def encrypt(plaintext: str | None) -> str:
    """Encrypt a secret for storage. Returns plaintext unchanged if no key set."""
    global _warned
    if not plaintext:
        return plaintext or ""
    if plaintext.startswith(_PREFIX):
        return plaintext  # already encrypted
    f = _fernet()
    if f is None:
        if not _warned:
            logger.warning(
                "SECRET_ENCRYPTION_KEY not set - third-party tokens are stored "
                "UNENCRYPTED. Set it before handling real customer credentials."
            )
            _warned = True
        return plaintext
    token = f.encrypt(plaintext.encode()).decode()
    return _PREFIX + token


def decrypt(value: str | None) -> str:
    """Decrypt a stored secret. Legacy plaintext (no prefix) is returned as-is."""
    if not value or not value.startswith(_PREFIX):
        return value or ""
    f = _fernet()
    if f is None:
        logger.error("Encrypted secret present but SECRET_ENCRYPTION_KEY missing/invalid")
        raise RuntimeError("Cannot decrypt secret: encryption key not configured")
    try:
        return f.decrypt(value[len(_PREFIX):].encode()).decode()
    except Exception as exc:
        raise RuntimeError("Cannot decrypt secret: wrong key or corrupt data") from exc


def is_configured() -> bool:
    return _fernet() is not None
