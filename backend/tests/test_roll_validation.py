"""Tests for roll number validation."""
import pytest
from app.utils.validators import validate_roll, normalise_roll


@pytest.mark.parametrize("roll, expected_valid", [
    ("524cs0019", True),
    ("abc123", True),
    ("a1b2c3d4e5", True),
    # Invalid cases
    ("../../etc", False),     # path traversal
    ("ab", False),             # too short
    ("A B", False),            # spaces
    ("ABCDEF", False),         # uppercase (before normalise)
    ("a" * 16, False),         # too long
    ("abc_def", False),        # underscore not allowed
    ("", False),               # empty
    ("abc!@#", False),         # special chars
])
def test_validate_roll(roll, expected_valid):
    valid, _ = validate_roll(roll)
    assert valid == expected_valid


def test_normalise_roll():
    assert normalise_roll("  524CS0019  ") == "524cs0019"
    assert normalise_roll("ABC123") == "abc123"


def test_normalise_then_validate():
    roll = normalise_roll("  524CS0019  ")
    valid, err = validate_roll(roll)
    assert valid is True
    assert err == ""

