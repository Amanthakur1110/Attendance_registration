"""Tests for face photo pose checks."""
from app.services.pose_service import POSES, POSE_NAMES, check_pose, get_pose, normalize_pose_name


def test_four_photo_steps():
    """Ensure exactly 4 steps exist."""
    assert len(POSES) == 4
    for i, name in enumerate(["PHOTO_1", "PHOTO_2", "PHOTO_3", "PHOTO_4"]):
        assert POSES[i].name == name
        assert get_pose(name) is not None


def test_legacy_aliases():
    """Ensure pose aliases map to the corresponding capture steps."""
    assert normalize_pose_name("FRONT") == "PHOTO_1"
    assert normalize_pose_name("FRONT_SLIGHT_RIGHT") == "PHOTO_2"
    assert normalize_pose_name("LEFT") == "PHOTO_3"
    assert normalize_pose_name("RIGHT") == "PHOTO_4"
    assert normalize_pose_name("UP") == "PHOTO_4"
    assert get_pose("FRONT") is not None


def test_front_and_either_side_view_are_accepted():
    """Accept two front poses and side views regardless of yaw sign."""
    assert check_pose(get_pose("PHOTO_1"), yaw=0, pitch=0, roll=0).ok
    assert check_pose(get_pose("PHOTO_2"), yaw=0, pitch=0, roll=0).ok
    assert check_pose(get_pose("PHOTO_3"), yaw=15, pitch=5, roll=0).ok
    assert check_pose(get_pose("PHOTO_3"), yaw=-15, pitch=5, roll=0).ok
    assert check_pose(get_pose("PHOTO_3"), yaw=80, pitch=5, roll=0).ok
    assert check_pose(get_pose("PHOTO_4"), yaw=25, pitch=-5, roll=0, previous_yaws=[0, 0, 15]).ok
    assert check_pose(get_pose("PHOTO_4"), yaw=-25, pitch=-5, roll=0, previous_yaws=[0, 0, -15]).ok


def test_side_photos_require_only_a_slight_change_of_view():
    side_without_turn = check_pose(get_pose("PHOTO_3"), yaw=4, pitch=0, roll=0)
    repeated_side = check_pose(get_pose("PHOTO_4"), yaw=17, pitch=0, roll=0, previous_yaws=[0, 0, 15])
    assert not side_without_turn.ok
    assert "either side" in side_without_turn.message.lower()
    assert not repeated_side.ok
    assert "slightly" in repeated_side.message.lower()


def test_front_step_rejects_extreme_angle():
    result = check_pose(get_pose("PHOTO_1"), yaw=80, pitch=0, roll=0)
    assert not result.ok
    assert "face visible" in result.message.lower()


def test_excessive_roll():
    """Excessive sideways in-plane tilt is rejected with upright reminder."""
    p1 = get_pose("PHOTO_1")
    result = check_pose(p1, yaw=0, pitch=0, roll=55)
    assert not result.ok
    assert "upright" in result.message.lower()
