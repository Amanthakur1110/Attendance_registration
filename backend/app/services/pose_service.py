"""Keypoint-ratio pose validation shared with the camera capture flow."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PoseConfig:
    name: str                 # internal key, e.g. "PHOTO_1"
    label: str                # human label, e.g. "Photo 1"
    instruction: str          # shown to the student


POSES: list[PoseConfig] = [
    PoseConfig(
        name="PHOTO_1",
        label="Front",
        instruction="Look straight at the camera",
    ),
    PoseConfig(
        name="PHOTO_2",
        label="Turn left",
        instruction="Turn a bit more to your LEFT",
    ),
    PoseConfig(
        name="PHOTO_3",
        label="Turn right",
        instruction="Turn a bit more to your RIGHT",
    ),
    PoseConfig(
        name="PHOTO_4",
        label="Look up",
        instruction="Tilt your chin up slightly",
    ),
]

POSE_NAMES: list[str] = [p.name for p in POSES]

# Aliases mapping legacy names to standard steps
POSE_ALIASES: dict[str, str] = {
    "FRONT": "PHOTO_1",
    "FRONT_SLIGHT_RIGHT": "PHOTO_1",
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


def compute_pose_ratios(
    keypoints: Sequence[Sequence[float]],
) -> tuple[float, float]:
    """Compute yaw/pitch ratios from InsightFace's five ordered keypoints."""
    if len(keypoints) < 5:
        raise ValueError("Five facial keypoints are required.")

    left_eye, right_eye, nose, left_mouth, right_mouth = keypoints[:5]
    coordinates = [
        float(point[axis])
        for point in (left_eye, right_eye, nose, left_mouth, right_mouth)
        for axis in (0, 1)
    ]
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("Facial keypoints must contain finite coordinates.")

    eye_mid_x = (float(left_eye[0]) + float(right_eye[0])) / 2
    eye_mid_y = (float(left_eye[1]) + float(right_eye[1])) / 2
    inter_eye_distance = math.hypot(
        float(right_eye[0]) - float(left_eye[0]),
        float(right_eye[1]) - float(left_eye[1]),
    )
    mouth_mid_y = (float(left_mouth[1]) + float(right_mouth[1])) / 2
    vertical_eye_mouth_distance = mouth_mid_y - eye_mid_y

    if inter_eye_distance <= 0 or abs(vertical_eye_mouth_distance) < 1e-6:
        raise ValueError("Facial keypoints do not define usable eye and mouth distances.")

    yaw_ratio = (float(nose[0]) - eye_mid_x) / inter_eye_distance
    pitch_ratio = (float(nose[1]) - eye_mid_y) / vertical_eye_mouth_distance
    return yaw_ratio, pitch_ratio


def signed_yaw_ratio(yaw_ratio: float, yaw_sign: int) -> float:
    """Apply the configured left/right convention in one place."""
    if yaw_sign not in (-1, 1):
        raise ValueError("YAW_SIGN must be either 1 or -1.")
    return yaw_ratio * yaw_sign


def get_pose_thresholds(config: Mapping | None = None) -> dict[str, float | int]:
    from ..config import Config

    defaults = {
        "POSE_FRONT_YAW_MAX": Config.POSE_FRONT_YAW_MAX,
        "POSE_SIDE_YAW_MIN": Config.POSE_SIDE_YAW_MIN,
        "POSE_UP_PITCH_DELTA": Config.POSE_UP_PITCH_DELTA,
        "POSE_UP_YAW_MAX": Config.POSE_UP_YAW_MAX,
        "POSE_YAW_SIGN": Config.POSE_YAW_SIGN,
        "POSE_SIDE_FACE_CONFIDENCE": Config.POSE_SIDE_FACE_CONFIDENCE,
    }
    if config is not None:
        defaults.update(
            {key: config[key] for key in defaults if key in config}
        )
    return {
        "front_yaw_max": float(defaults["POSE_FRONT_YAW_MAX"]),
        "side_yaw_min": float(defaults["POSE_SIDE_YAW_MIN"]),
        "up_pitch_delta": float(defaults["POSE_UP_PITCH_DELTA"]),
        "up_yaw_max": float(defaults["POSE_UP_YAW_MAX"]),
        "yaw_sign": int(defaults["POSE_YAW_SIGN"]),
        "side_face_confidence": float(defaults["POSE_SIDE_FACE_CONFIDENCE"]),
    }


def check_pose(
    expected: PoseConfig,
    yaw_ratio: float,
    pitch_ratio: float,
    front_pitch_ratio: float | None,
    det_score: float,
    thresholds: Mapping | None = None,
) -> PoseCheckResult:
    values = get_pose_thresholds(thresholds)
    directed_yaw = signed_yaw_ratio(yaw_ratio, int(values["yaw_sign"]))

    if expected.name == "PHOTO_1":
        if abs(directed_yaw) > float(values["front_yaw_max"]):
            return PoseCheckResult(False, "Look straight at the camera.")
    elif expected.name == "PHOTO_2":
        if det_score < float(values["side_face_confidence"]):
            return PoseCheckResult(False, "Move closer and keep your face well lit.")
        if directed_yaw < float(values["side_yaw_min"]):
            return PoseCheckResult(False, "Turn a bit more to your LEFT.")
    elif expected.name == "PHOTO_3":
        if det_score < float(values["side_face_confidence"]):
            return PoseCheckResult(False, "Move closer and keep your face well lit.")
        if directed_yaw > -float(values["side_yaw_min"]):
            return PoseCheckResult(False, "Turn a bit more to your RIGHT.")
    elif expected.name == "PHOTO_4":
        if front_pitch_ratio is None:
            return PoseCheckResult(False, "Front photo reference is missing; please contact the supervisor.")
        if abs(directed_yaw) > float(values["up_yaw_max"]):
            return PoseCheckResult(False, "Face the camera more directly, then tilt your chin up.")
        if pitch_ratio > front_pitch_ratio - float(values["up_pitch_delta"]):
            return PoseCheckResult(False, "Tilt your chin up slightly.")

    return PoseCheckResult(True, "")
