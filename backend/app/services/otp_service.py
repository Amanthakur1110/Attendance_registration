"""OTP generation, hashing, verification and lifecycle management."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models.otp import Otp
from ..models.user import User

logger = logging.getLogger(__name__)


def _hash_otp(otp: str, salt: str) -> str:
    """HMAC-SHA256 hash of the OTP using SECRET_KEY as key."""
    key = (current_app.config["SECRET_KEY"] + salt).encode()
    return hmac.new(key, otp.encode(), hashlib.sha256).hexdigest()


def _salt_for_roll(roll: str) -> str:
    """Deterministic but unique-per-roll salt (OTP row created_at timestamp)."""
    # We use the roll itself as additional salt since OTPs are per-roll.
    return roll


def generate_and_store_otp(roll: str) -> tuple[str, str]:
    """
    Generate a 6-digit OTP, store its hash in the DB, return (otp, email).
    Raises RuntimeError if called too soon (cooldown not elapsed).
    Deletes any existing OTP for the roll before creating a new one.
    """
    now = datetime.now(timezone.utc)
    cooldown = current_app.config["OTP_COOLDOWN_SECONDS"]
    expiry_minutes = current_app.config["OTP_EXPIRY_MINUTES"]
    email_domain = current_app.config["EMAIL_DOMAIN"]

    # Check cooldown
    existing_otp: Otp | None = db.session.get(Otp, roll)
    if existing_otp:
        elapsed = (now - existing_otp.last_sent_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            raise CooldownError(f"Please wait {remaining} seconds before requesting a new OTP.", remaining)
        db.session.delete(existing_otp)
        db.session.flush()

    # Ensure user row exists
    user: User | None = db.session.get(User, roll)
    if not user:
        email = f"{roll}@{email_domain}"
        user = User(roll=roll, email=email)
        db.session.add(user)
        db.session.flush()

    otp = secrets.token_hex(3).upper()  # 6 hex chars, e.g. "A3F9B2"
    # Use a pure-digit OTP for student familiarity
    otp = str(secrets.randbelow(900000) + 100000)  # 100000 – 999999

    otp_hash = _hash_otp(otp, roll)
    expires_at = now + timedelta(minutes=expiry_minutes)

    otp_row = Otp(
        roll=roll,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        created_at=now,
        last_sent_at=now,
    )
    db.session.add(otp_row)
    db.session.commit()
    logger.info("OTP generated for roll=%s (expires %s)", roll, expires_at.isoformat())
    return otp, user.email


def delete_otp(roll: str) -> None:
    """Remove the OTP row if its email could not be queued for delivery."""
    otp: Otp | None = db.session.get(Otp, roll)
    if otp:
        db.session.delete(otp)
        db.session.commit()


class CooldownError(Exception):
    def __init__(self, message: str, remaining: int):
        super().__init__(message)
        self.remaining = remaining


class OtpError(Exception):
    """Base for OTP verification errors."""


def verify_otp(roll: str, otp_plain: str) -> bool:
    """
    Verify an OTP.
    - Returns True on success (and deletes the OTP row — single use).
    - Raises OtpError with a clear message on failure.
    """
    now = datetime.now(timezone.utc)
    otp_row: Otp | None = db.session.get(Otp, roll)

    if not otp_row:
        raise OtpError("No OTP found. Please request a new one.")

    # Expiry check
    expires = otp_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        db.session.delete(otp_row)
        db.session.commit()
        raise OtpError("OTP has expired. Please request a new one.")

    max_attempts = current_app.config["MAX_OTP_ATTEMPTS"]

    # Attempts check
    if otp_row.attempts >= max_attempts:
        raise OtpError(
            f"Too many wrong attempts. Please request a new OTP."
        )

    # Constant-time comparison
    expected_hash = _hash_otp(otp_plain.strip(), roll)
    actual_hash = otp_row.otp_hash
    if not hmac.compare_digest(expected_hash, actual_hash):
        otp_row.attempts += 1
        db.session.commit()
        remaining = max_attempts - otp_row.attempts
        if remaining <= 0:
            raise OtpError("Too many wrong attempts. Please request a new OTP.")
        raise OtpError(
            f"Incorrect OTP. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        )

    # Success — delete (single use)
    db.session.delete(otp_row)
    db.session.commit()
    logger.info("OTP verified for roll=%s", roll)
    return True
