"""Security helpers for ESP-RFID V3."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from .const import DEFAULT_PIN_ITERATIONS

_NON_HEX = re.compile(r"[^0-9A-Fa-f]")
_USER_ID_SAFE = re.compile(r"[^a-z0-9_-]+")


def generate_site_secret() -> str:
    """Generate a new site secret."""
    return secrets.token_hex(32)


def normalize_rfid_uid(rfid_uid: str) -> str:
    """Normalize a presented RFID UID."""
    return _NON_HEX.sub("", rfid_uid).upper()


def normalize_user_id(user_id: str) -> str:
    """Normalize a user identifier for storage."""
    return _USER_ID_SAFE.sub("_", user_id.strip().lower()).strip("_")


def derive_tag_digest(site_secret: str, rfid_uid: str) -> str:
    """Derive a stable HMAC digest for an RFID credential."""
    normalized_uid = normalize_rfid_uid(rfid_uid)
    return hmac.new(
        bytes.fromhex(site_secret),
        normalized_uid.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def derive_pin_material(
    pin: str,
    *,
    salt_hex: str | None = None,
    iterations: int = DEFAULT_PIN_ITERATIONS,
) -> tuple[str, str, int]:
    """Derive a PBKDF2 hash for a PIN."""
    salt = bytes.fromhex(salt_hex) if salt_hex is not None else secrets.token_bytes(16)
    pin_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        iterations,
    )
    return pin_hash.hex(), salt.hex(), iterations
