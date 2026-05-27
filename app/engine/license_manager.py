"""
License management and usage tracking.

Implements the freemium model:
  - Free tier: 5 document conversions
  - Licensed: unlimited conversions with a valid license key

Usage data is stored locally in the app data directory.
No network calls — all validation is offline.
"""

import base64
import hashlib
import hmac
import json
import os
import datetime
import threading
from typing import Optional

from .logger import appdata_dir

_LICENSE_FILE = "license.json"
_FREE_TIER_LIMIT = 999
_io_lock = threading.Lock()

# Key format constants
_PFX = "DS-"
_SEG_COUNT = 4
_SEG_LEN = 4

# ── Internal validation machinery ────────────────────────────────
# Secrets are derived at runtime from encoded components to prevent
# static analysis and simple string searches in the source.

_C0 = b'ZHNxLXByb2QtdjEtbWQ='
_C1 = b'NjRhZTg4OGEtYzJmNy00NzI0'
_C2 = b'YjhlNS1kMWEzZjk3MDBjNjI='


def _dk() -> bytes:
    """Derive the signing key at runtime."""
    p0 = base64.b64decode(_C0)
    p1 = base64.b64decode(_C1)
    p2 = base64.b64decode(_C2)
    return hashlib.sha512(p0 + b':' + p1 + b':' + p2).digest()


def _compute_tag(segments: list[str]) -> str:
    """Compute the verification tag for the given key segments."""
    payload = "|".join(segments).encode()
    h = hmac.new(_dk(), payload, hashlib.sha256)
    # Multi-round derivation
    for _ in range(3):
        h = hmac.new(h.digest(), payload, hashlib.sha256)
    raw = h.hexdigest()
    # Extract non-sequential characters to form the tag
    indices = [2, 7, 13, 19]
    return "".join(raw[i] for i in indices).upper()


def _check_format(k: str) -> bool:
    """Validate structural format only."""
    k = k.strip().upper()
    if not k.startswith(_PFX):
        return False
    body = k[len(_PFX):]
    parts = body.split("-")
    if len(parts) != _SEG_COUNT:
        return False
    return all(len(p) == _SEG_LEN and p.isalnum() for p in parts)


def _check_sig(k: str) -> bool:
    """Verify the cryptographic signature embedded in the key."""
    k = k.strip().upper()
    parts = k[len(_PFX):].split("-")
    if len(parts) != _SEG_COUNT:
        return False
    tag = _compute_tag(parts[:_SEG_COUNT - 1])
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(parts[-1], tag)


# ── Persistence ──────────────────────────────────────────────────

def _license_path() -> str:
    return os.path.join(appdata_dir(), _LICENSE_FILE)


def _load_data() -> dict:
    path = _license_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {
        "conversion_count": 0,
        "license_key": "",
        "activated_date": "",
        "first_use_date": "",
    }


def _save_data(data: dict) -> None:
    path = _license_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


# ── Public API ───────────────────────────────────────────────────


def get_conversion_count() -> int:
    """Return the number of conversions used."""
    return _load_data().get("conversion_count", 0)


def get_free_tier_limit() -> int:
    """Return the free tier conversion limit."""
    return _FREE_TIER_LIMIT


def get_remaining_conversions() -> int:
    """Return remaining free conversions (or -1 if licensed)."""
    if is_licensed():
        return -1  # unlimited
    count = get_conversion_count()
    return max(0, _FREE_TIER_LIMIT - count)


def is_licensed() -> bool:
    """Check if a valid license key is activated."""
    data = _load_data()
    key = data.get("license_key", "")
    if not key:
        return False
    return _check_format(key) and _check_sig(key)


def is_trial_expired() -> bool:
    """Check if the free tier has been exhausted."""
    if is_licensed():
        return False
    return get_conversion_count() >= _FREE_TIER_LIMIT


def increment_conversion_count(count: int = 1) -> int:
    """
    Increment the conversion counter by count.
    Called after each successful file conversion.
    Returns the new total.  Thread-safe via _io_lock.
    """
    with _io_lock:
        data = _load_data()
        if not data.get("first_use_date"):
            data["first_use_date"] = datetime.date.today().isoformat()
        data["conversion_count"] = data.get("conversion_count", 0) + count
        _save_data(data)
        return data["conversion_count"]


def activate_license(key: str) -> tuple[bool, str]:
    """
    Attempt to activate a license key.

    Returns (success: bool, message: str).
    """
    key = key.strip().upper()

    if not _check_format(key):
        return False, "Invalid key format. Expected: DS-XXXX-XXXX-XXXX-XXXX"

    if not _check_sig(key):
        return False, "Invalid license key. Please check and try again."

    data = _load_data()
    data["license_key"] = key
    data["activated_date"] = datetime.date.today().isoformat()
    _save_data(data)
    return True, "License activated successfully. Enjoy unlimited conversions!"


def deactivate_license() -> None:
    """Remove the license key (revert to free tier)."""
    data = _load_data()
    data["license_key"] = ""
    data["activated_date"] = ""
    _save_data(data)


def get_license_info() -> dict:
    """Return a summary of the current license state."""
    data = _load_data()
    licensed = is_licensed()
    return {
        "licensed": licensed,
        "license_key": data.get("license_key", ""),
        "activated_date": data.get("activated_date", ""),
        "first_use_date": data.get("first_use_date", ""),
        "conversion_count": data.get("conversion_count", 0),
        "remaining": get_remaining_conversions(),
        "limit": _FREE_TIER_LIMIT,
        "status": "Licensed" if licensed else (
            "Trial expired" if is_trial_expired() else "Free tier"
        ),
    }
