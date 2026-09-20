"""Password hashing utilities.

WARNING (VULN-5 — Weak Password Storage): passwords are hashed with MD5 and
NO salt / NO key-derivation function. This is an intentional, educational
vulnerability. Do NOT use this in any real application.
"""

import hashlib


def hash_password(password: str) -> str:
    """Return the MD5 hex digest of ``password`` (no salt — intentional)."""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` hashes (MD5) to ``hashed``."""
    return hash_password(plain) == hashed
