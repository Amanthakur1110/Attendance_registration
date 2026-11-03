"""Tests for face photo pose checks."""
import pytest
from app.services.pose_service import POSES, POSE_NAMES, check_pose, get_pose, normalize_pose_name


def test_four_photo_steps():
    """Ensure exactly 4 steps exist."""
    assert len(POSES) == 4
    for i, name in enumerate(["PHOTO_1", "PHOTO_2", "PHOTO_3", "PHOTO_4"]):
        assert POSES[i].name == name
        assert get_pose(name) is not None


def test_legacy_aliases():
    """Ensure legacy aliases map to the 4 photo steps."""
    assert normalize_pose_name("FRONT") == "PHOTO_1"
    assert normalize_pose_name("LEFT") == "PHOTO_2"
    assert normalize_pose_name("RIGHT") == "PHOTO_3"
    assert normalize_pose_name("UP") == "PHOTO_4"
    assert get_pose("FRONT") is not None


def test_natural_poses_accepted():
    """Natural angles (center, turned slightly, tilted slightly) must be accepted."""
    p1 = get_pose("PHOTO_1")
    assert check_pose(p1, yaw=0, pitch=0, roll=0).ok
    assert check_pose(p1, yaw=25, pitch=5, roll=0).ok
    assert check_pose(p1, yaw=-25, pitch=-5, roll=0).ok
    assert check_pose(p1, yaw=5, pitch=20, roll=0).ok


def test_excessive_roll():
    """Excessive sideways in-plane tilt is rejected with upright reminder."""
    p1 = get_pose("PHOTO_1")
    result = check_pose(p1, yaw=0, pitch=0, roll=45)
    assert not result.ok
    assert "upright" in result.message.lower()
