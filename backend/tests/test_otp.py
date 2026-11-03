"""Tests for OTP generation, verification, and lifecycle."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


def _setup_user(app, roll: str = "524cs0019"):
    """Helper: create a user row."""
    from app.models.user import User
    from app.extensions import db
    with app.app_context():
        u = User(roll=roll, email=f"{roll}@iiitk.ac.in")
        db.session.add(u)
        db.session.commit()


def test_send_otp_emails_correct_address(client, app):
    """OTP delivery is queued and does not block the HTTP response."""
    with patch("app.api.auth._otp_email_executor.submit") as mock_submit, \
         patch("app.api.auth.generate_and_store_otp", return_value=("123456", "524cs0019@iiitk.ac.in")):
        resp = client.post("/api/auth/send-otp", json={"roll": "524cs0019"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "524cs0019@iiitk.ac.in" in data["message"]
        assert "being sent" in data["message"]
        mock_submit.assert_called_once()
        worker, queued_app, email, roll, otp = mock_submit.call_args.args
        assert worker.__name__ == "_send_otp_email_in_background"
        assert queued_app is app
        assert email == "524cs0019@iiitk.ac.in"
        assert roll == "524cs0019"
        assert otp == "123456"


def test_background_otp_delivery_logs_email_failure(app):
    with patch("app.api.auth.send_otp_email", side_effect=RuntimeError("SMTP unavailable")) as mock_send, \
         patch("app.api.auth.logger.exception") as mock_log:
        from app.api.auth import _send_otp_email_in_background

        _send_otp_email_in_background(app, "524cs0019@iiitk.ac.in", "524cs0019", "123456")

        mock_send.assert_called_once_with("524cs0019@iiitk.ac.in", "524cs0019", "123456")
        mock_log.assert_called_once()


def test_send_otp_invalid_roll(client):
    """Invalid roll numbers must be rejected."""
    for bad_roll in ["../../etc", "ab", "A B", "", "a" * 20]:
        resp = client.post("/api/auth/send-otp", json={"roll": bad_roll})
        assert resp.status_code in (400, 422), f"Expected 4xx for roll={bad_roll!r}"
        data = resp.get_json()
        assert data["ok"] is False


def test_wrong_otp_rejected(client, app):
    """Wrong OTP returns 401."""
    with app.app_context():
        from app.models.user import User
        from app.extensions import db
        user = User(roll="testroll1", email="testroll1@iiitk.ac.in")
        db.session.add(user)
        db.session.commit()

    with patch("app.api.auth.send_otp_email"):
        client.post("/api/auth/send-otp", json={"roll": "testroll1"})

    resp = client.post("/api/auth/verify-otp", json={"roll": "testroll1", "otp": "000000"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["ok"] is False


def test_otp_locked_after_max_attempts(client, app):
    """After MAX_OTP_ATTEMPTS wrong attempts, OTP is locked."""
    roll = "locktest1"
    with app.app_context():
        from app.models.user import User
        from app.models.otp import Otp
        from app.extensions import db
        import hmac, hashlib
        now = datetime.now(timezone.utc)
        user = User(roll=roll, email=f"{roll}@iiitk.ac.in")
        db.session.add(user)
        db.session.flush()
        key = (app.config["SECRET_KEY"] + roll).encode()
        otp_hash = hmac.new(key, b"111111", hashlib.sha256).hexdigest()
        otp_row = Otp(
            roll=roll,
            otp_hash=otp_hash,
            expires_at=now + timedelta(minutes=5),
            attempts=0,
            created_at=now,
            last_sent_at=now,
        )
        db.session.add(otp_row)
        db.session.commit()

    max_attempts = app.config["MAX_OTP_ATTEMPTS"]
    for _ in range(max_attempts):
        client.post("/api/auth/verify-otp", json={"roll": roll, "otp": "999999"})

    resp = client.post("/api/auth/verify-otp", json={"roll": roll, "otp": "111111"})
    data = resp.get_json()
    assert data["ok"] is False
    assert "attempt" in data["message"].lower() or "new OTP" in data["message"]


def test_expired_otp_rejected(client, app):
    """An expired OTP must be rejected."""
    roll = "expiredroll"
    with app.app_context():
        from app.models.user import User
        from app.models.otp import Otp
        from app.extensions import db
        import hmac, hashlib
        now = datetime.now(timezone.utc)
        user = User(roll=roll, email=f"{roll}@iiitk.ac.in")
        db.session.add(user)
        db.session.flush()
        key = (app.config["SECRET_KEY"] + roll).encode()
        otp_hash = hmac.new(key, b"123456", hashlib.sha256).hexdigest()
        otp_row = Otp(
            roll=roll,
            otp_hash=otp_hash,
            expires_at=now - timedelta(minutes=1),  # already expired
            attempts=0,
            created_at=now - timedelta(minutes=6),
            last_sent_at=now - timedelta(minutes=6),
        )
        db.session.add(otp_row)
        db.session.commit()

    resp = client.post("/api/auth/verify-otp", json={"roll": roll, "otp": "123456"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert "expired" in data["message"].lower()


def test_otp_single_use(client, app):
    """A correct OTP can only be used once."""
    roll = "singleuse1"
    with app.app_context():
        from app.models.user import User
        from app.models.otp import Otp
        from app.extensions import db
        import hmac, hashlib
        now = datetime.now(timezone.utc)
        user = User(roll=roll, email=f"{roll}@iiitk.ac.in")
        db.session.add(user)
        db.session.flush()
        key = (app.config["SECRET_KEY"] + roll).encode()
        otp_hash = hmac.new(key, b"654321", hashlib.sha256).hexdigest()
        otp_row = Otp(
            roll=roll,
            otp_hash=otp_hash,
            expires_at=now + timedelta(minutes=5),
            attempts=0,
            created_at=now,
            last_sent_at=now,
        )
        db.session.add(otp_row)
        db.session.commit()

    resp1 = client.post("/api/auth/verify-otp", json={"roll": roll, "otp": "654321"})
    assert resp1.status_code == 200

    resp2 = client.post("/api/auth/verify-otp", json={"roll": roll, "otp": "654321"})
    assert resp2.status_code == 401


def test_completed_roll_no_otp(client, app):
    """A completed roll returns 409 and does NOT send an email."""
    roll = "completed1"
    with app.app_context():
        from app.models.user import User
        from app.extensions import db
        user = User(roll=roll, email=f"{roll}@iiitk.ac.in", completed=True, photo_count=4)
        db.session.add(user)
        db.session.commit()

    with patch("app.api.auth.send_otp_email") as mock_send:
        resp = client.post("/api/auth/send-otp", json={"roll": roll})
        assert resp.status_code == 409
        data = resp.get_json()
        assert data["ok"] is False
        mock_send.assert_not_called()
