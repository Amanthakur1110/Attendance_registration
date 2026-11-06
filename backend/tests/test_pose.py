"""Tests for face photo pose checks."""
import pytest

from app.services.pose_service import (
    POSES,
    POSE_NAMES,
    check_pose,
    compute_pose_ratios,
    get_pose,
    normalize_pose_name,
)


def test_four_photo_steps():
    """Ensure exactly 4 steps exist."""
    assert len(POSES) == 4
    for i, name in enumerate(["PHOTO_1", "PHOTO_2", "PHOTO_3", "PHOTO_4"]):
        assert POSES[i].name == name
        assert get_pose(name) is not None


def test_legacy_aliases():
    """Ensure pose aliases map to the corresponding capture steps."""
    assert normalize_pose_name("FRONT") == "PHOTO_1"
    assert normalize_pose_name("FRONT_SLIGHT_RIGHT") == "PHOTO_1"
    assert normalize_pose_name("LEFT") == "PHOTO_2"
    assert normalize_pose_name("RIGHT") == "PHOTO_3"
    assert normalize_pose_name("UP") == "PHOTO_4"
    assert get_pose("FRONT") is not None


def make_keypoints(yaw_ratio, pitch_ratio):
    eye_y = 100.0
    mouth_y = 200.0
    eye_mid_x = 150.0
    return [
        (100.0, eye_y),
        (200.0, eye_y),
        (eye_mid_x + yaw_ratio * 100.0, eye_y + pitch_ratio * (mouth_y - eye_y)),
        (120.0, mouth_y),
        (180.0, mouth_y),
    ]


def test_keypoint_ratios_use_eye_and_mouth_normalization():
    yaw_ratio, pitch_ratio = compute_pose_ratios(make_keypoints(0.20, 0.24))
    assert yaw_ratio == pytest.approx(0.20)
    assert pitch_ratio == pytest.approx(0.24)


def test_front_left_right_and_up_pose_rules():
    front = check_pose(get_pose("PHOTO_1"), 0.15, 0.30, None, 0.95)
    left = check_pose(get_pose("PHOTO_2"), 0.18, 0.30, 0.30, 0.95)
    right = check_pose(get_pose("PHOTO_3"), -0.18, 0.30, 0.30, 0.95)
    up = check_pose(get_pose("PHOTO_4"), 0.20, 0.24, 0.30, 0.95)
    assert front.ok
    assert left.ok
    assert right.ok
    assert up.ok


def test_wrong_pose_direction_has_actionable_feedback():
    front = check_pose(get_pose("PHOTO_1"), 0.2, 0.3, None, 0.95)
    left = check_pose(get_pose("PHOTO_2"), -0.2, 0.3, 0.3, 0.95)
    right = check_pose(get_pose("PHOTO_3"), 0.2, 0.3, 0.3, 0.95)
    up = check_pose(get_pose("PHOTO_4"), 0, 0.30, 0.30, 0.95)
    assert front.message == "Look straight at the camera."
    assert left.message == "Turn a bit more to your LEFT."
    assert right.message == "Turn a bit more to your RIGHT."
    assert up.message == "Tilt your chin up slightly."


def test_yaw_sign_flips_left_and_right_once():
    thresholds = {"POSE_YAW_SIGN": -1}
    left = check_pose(get_pose("PHOTO_2"), -0.2, 0.3, 0.3, 0.95, thresholds)
    right = check_pose(get_pose("PHOTO_3"), 0.2, 0.3, 0.3, 0.95, thresholds)
    assert left.ok
    assert right.ok


def test_mirrored_keypoints_flip_yaw_ratio_sign():
    points = make_keypoints(0.22, 0.30)
    mirrored = [(400.0 - x, y) for x, y in points]
    original_yaw, original_pitch = compute_pose_ratios(points)
    mirrored_yaw, mirrored_pitch = compute_pose_ratios(mirrored)
    assert mirrored_yaw == pytest.approx(-original_yaw)
    assert mirrored_pitch == pytest.approx(original_pitch)


def test_side_confidence_and_up_yaw_limits():
    low_confidence = check_pose(get_pose("PHOTO_2"), 0.3, 0.3, 0.3, 0.69)
    wide_up_yaw = check_pose(get_pose("PHOTO_4"), 0.26, 0.20, 0.30, 0.95)
    assert not low_confidence.ok
    assert "well lit" in low_confidence.message.lower()
    assert not wide_up_yaw.ok
    assert "more directly" in wide_up_yaw.message.lower()


def test_invalid_keypoint_geometry_is_rejected():
    with pytest.raises(ValueError):
        compute_pose_ratios([(0, 0)] * 4)
    points = make_keypoints(0.0, 0.3)
    points[2] = (float("nan"), 100.0)
    with pytest.raises(ValueError):
        compute_pose_ratios(points)
