"""Pose sequence and tolerant server-side head-angle validation."""
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
    roll_max: float = 50.0    # maximum absolute in-plane roll (symmetric)


# InsightFace yaw can be noisy across camera orientation and preview mirroring.
# Later photos therefore validate side-view magnitude, not left/right sign.
POSES: list[PoseConfig] = [
    PoseConfig(
        name="PHOTO_1",
        label="Front",
        instruction="Look straight at the camera",
        yaw_min=-45.0,
        yaw_max=45.0,
        pitch_min=-45.0,
        pitch_max=45.0,
    ),
    PoseConfig(
        name="PHOTO_2",
        label="Front again",
        instruction="Look at the camera for one more front photo",
        yaw_min=-45.0,
        yaw_max=45.0,
        pitch_min=-45.0,
        pitch_max=45.0,
    ),
    PoseConfig(
        name="PHOTO_3",
        label="Different angle",
        instruction="Turn your face slightly to either side",
        yaw_min=-90.0,
        yaw_max=90.0,
        pitch_min=-60.0,
        pitch_max=60.0,
    ),
    PoseConfig(
        name="PHOTO_4",
        label="Another angle",
        instruction="Change to a slightly different side view",
        yaw_min=-90.0,
        yaw_max=90.0,
        pitch_min=-60.0,
        pitch_max=60.0,
    ),
]

POSE_NAMES: list[str] = [p.name for p in POSES]

# Aliases mapping legacy names to standard steps
POSE_ALIASES: dict[str, str] = {
    "FRONT": "PHOTO_1",
    "FRONT_SLIGHT_RIGHT": "PHOTO_2",
    "LEFT": "PHOTO_3",
    "RIGHT": "PHOTO_4",
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


def check_pose(
    expected: PoseConfig,
    yaw: float,
    pitch: float,
    roll: float,
    previous_yaws: list[float] | None = None,
) -> PoseCheckResult:
    """
    Accept either turn direction for side views; require only a small yaw change
    for the final view so camera mirror/sign conventions cannot block capture.
    """
    if yaw < expected.yaw_min or yaw > expected.yaw_max:
        return PoseCheckResult(False, "Keep your face visible to the camera.")

    if not expected.pitch_min <= pitch <= expected.pitch_max:
        return PoseCheckResult(False, "Keep your whole face visible to the camera.")

    if abs(roll) > expected.roll_max:
        return PoseCheckResult(False, "Keep your face upright and visible.")

    if expected.name in {"PHOTO_3", "PHOTO_4"} and abs(yaw) < 8.0:
        return PoseCheckResult(False, "Turn your face slightly to either side.")

    if expected.name == "PHOTO_4" and previous_yaws:
        previous_side_yaw = previous_yaws[-1]
        if abs(yaw - previous_side_yaw) < 5.0:
            return PoseCheckResult(
                False,
                "Change your face angle slightly, in either direction.",
            )

    return PoseCheckResult(True, "")
