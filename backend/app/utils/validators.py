"""Input validation utilities."""
from __future__ import annotations

import re

ROLL_PATTERN = re.compile(r"^[a-z0-9]{6,15}$")


def validate_roll(roll: str) -> tuple[bool, str]:
    """Validate a normalised roll number.

    Returns (is_valid, error_message).
    """
    if not roll:
        return False, "Roll number is required."
    if not ROLL_PATTERN.match(roll):
        return False, (
            "Invalid roll number. Must be 6–15 alphanumeric lowercase characters "
            "(e.g. 524cs0019)."
        )
    return True, ""


def normalise_roll(roll: str) -> str:
    """Strip whitespace and lowercase a roll number."""
    return roll.strip().lower()


# ── Image file validation ────────────────────────────────────────────────────

ALLOWED_MAGIC: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}
MAX_MAGIC_LEN = 8
MIN_FILE_BYTES = 1_000   # 1 KB — any real photo is bigger
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB


def validate_image_bytes(data: bytes) -> tuple[bool, str]:
    """Check magic bytes, minimum and maximum size."""
    if len(data) < MIN_FILE_BYTES:
        return False, "File is too small or empty."
    if len(data) > MAX_FILE_BYTES:
        return False, "File too large. Maximum size is 2 MB."

    header = data[:MAX_MAGIC_LEN]
    for magic in ALLOWED_MAGIC:
        if header[: len(magic)] == magic:
            return True, ""

    return False, "Only JPEG and PNG images are accepted."

