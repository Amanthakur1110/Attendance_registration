"""Pose / Face photo sequence configuration and classification.

Supports 4 progressive face photo captures (PHOTO_1, PHOTO_2, PHOTO_3, PHOTO_4)
along with legacy aliases (FRONT, LEFT, RIGHT, UP) for backward compatibility.
Focuses on valid face presence, proper framing, and user-friendly capture.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PoseConfig:
    name: str                 # internal key, e.g. "PHOTO_1"
    label: str                # human label, e.g. "Photo 1"
    instruction: str          # shown to the student
    yaw_min: float = -90.0
    yaw_max: float = 90.0
    pitch_min: float = -90.0
    pitch_max: float = 90.0
    roll_max: float = 35.0    # maximum absolute in-plane roll (symmetric)


# ── Canonical 4-step photo capture sequence ────────────────────────────────
POSES: list[PoseConfig] = [
    PoseConfig(
        name="PHOTO_1",
        label="Photo 1",
        instruction="Center your face inside the circle",
    ),
    PoseConfig(
        name="PHOTO_2",
        label="Photo 2",
        instruction="Move your head slowly to complete the circle",
    ),
    PoseConfig(
        name="PHOTO_3",
        label="Photo 3",
        instruction="Move your head slowly to complete the circle",
    ),
    PoseConfig(
        name="PHOTO_4",
        label="Photo 4",
        instruction="Move your head slowly to complete the circle",
    ),
]

POSE_NAMES: list[str] = [p.name for p in POSES]

# Aliases mapping legacy names to standard steps
POSE_ALIASES: dict[str, str] = {
    "FRONT": "PHOTO_1",
    "LEFT": "PHOTO_2",
    "RIGHT": "PHOTO_3",
    "UP": "PHOTO_4",
    "PHOTO_1": "PHOTO_1",
    "PHOTO_2": "PHOTO_2",
    "PHOTO_3": "PHOTO_3",
    "PHOTO_4": "PHOTO_4",
}


def normalize_pose_name(name: str) -> str:
    cleaned = (name or "").strip().upper()
    return POSE_ALIASES.get(cleaned, cleaned)


def get_pose(name: str) -> PoseConfig | None:
    norm = normalize_pose_name(name)
    for p in POSES:
        if p.name == norm:
            return p
    return None


@dataclass
class PoseCheckResult:
    ok: bool
    message: str   # empty when ok


def check_pose(expected: PoseConfig, yaw: float, pitch: float, roll: float) -> PoseCheckResult:
    """
    Validate that head is kept reasonably upright (roll within +/-35 deg).
    Does not restrict yaw/pitch so students can naturally complete the Face ID circle.
    """
    if abs(roll) > expected.roll_max:
        direction = "right" if roll > 0 else "left"
        return PoseCheckResult(False, f"Please keep your head upright (it's leaning to the {direction}).")

    return PoseCheckResult(True, "")
