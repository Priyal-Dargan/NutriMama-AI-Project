"""
utils/security.py
Password hashing helpers using bcrypt directly. Never store or compare plain-text passwords.

Note: we call bcrypt directly rather than via passlib's CryptContext. passlib 1.7.4's
bcrypt backend-detection routine is incompatible with bcrypt>=4.1 (it probes a
`__about__` attribute that newer bcrypt removed), which raises spurious errors at
hash time. Calling bcrypt directly avoids that broken detection path entirely.
"""

import bcrypt

# bcrypt has a hard 72-byte input limit; truncate defensively so long passphrases
# don't raise instead of silently failing security expectations.
_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
