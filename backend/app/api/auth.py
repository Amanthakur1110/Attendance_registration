"""Auth blueprint: OTP send, verify, logout, me, profile."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, Flask, current_app, request

from ..extensions import limiter
from ..models.user import User, VALID_BRANCHES
from ..extensions import db
from ..services.otp_service import (
    CooldownError,
    OtpError,
    delete_otp,
    generate_and_store_otp,
    verify_otp,
)
from ..services.mail_service import send_otp_email
from ..utils.responses import json_error, json_ok
from ..utils.validators import normalise_roll, validate_roll
from ..utils.security import (
    clear_session,
    get_session_roll,
    login_required,
    set_session_roll,
)

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)
_otp_email_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="otp-email")


def _send_otp_email_in_background(app: Flask, email: str, roll: str, otp: str) -> None:
    """Deliver the OTP outside the request while keeping Flask app context."""
    with app.app_context():
        try:
            send_otp_email(email, roll, otp)
        except Exception:
            logger.exception("Background OTP email delivery failed for %s", roll)


@auth_bp.post("/send-otp")
@limiter.limit("5 per hour", key_func=lambda: request.json.get("roll", "") if request.json else "")
@limiter.limit("1 per 60 seconds", key_func=lambda: request.json.get("roll", "") if request.json else "")
def send_otp():
    data = request.get_json(silent=True) or {}
    raw_roll = data.get("roll", "")
    roll = normalise_roll(raw_roll)

    valid, err = validate_roll(roll)
    if not valid:
        return json_error(err, "INVALID_ROLL", 400)

    # Check if already completed
    user: User | None = db.session.get(User, roll)
    if user and user.completed:
        return json_error(
            "Photos already submitted for this roll number.",
            "ALREADY_COMPLETED",
            409,
        )

    try:
        otp, email = generate_and_store_otp(roll)
    except CooldownError as exc:
        return json_error(str(exc), "COOLDOWN", 429, remaining=exc.remaining)
    except Exception as exc:
        logger.exception("Error generating OTP for %s: %s", roll, exc)
        return json_error("Could not generate OTP. Please try again.", "OTP_ERROR", 500)

    app = current_app._get_current_object()
    try:
        _otp_email_executor.submit(_send_otp_email_in_background, app, email, roll, otp)
    except Exception as exc:
        delete_otp(roll)
        logger.exception("Could not queue OTP email for %s: %s", roll, exc)
        return json_error("Could not queue the OTP email. Please try again.", "EMAIL_ERROR", 503)

    domain = current_app.config["EMAIL_DOMAIN"]
    return json_ok(
        f"OTP email is being sent to {roll}@{domain}. Please also check your SPAM/Junk folder.",
        "OTP_SENT",
        email=email,
        cooldown=current_app.config["OTP_COOLDOWN_SECONDS"],
    )


@auth_bp.post("/verify-otp")
@limiter.limit("10 per minute")
def verify_otp_endpoint():
    data = request.get_json(silent=True) or {}
    raw_roll = data.get("roll", "")
    otp_plain = str(data.get("otp", "")).strip()
    roll = normalise_roll(raw_roll)

    valid, err = validate_roll(roll)
    if not valid:
        return json_error(err, "INVALID_ROLL", 400)

    if not otp_plain or len(otp_plain) != 6 or not otp_plain.isdigit():
        return json_error("OTP must be a 6-digit number.", "INVALID_OTP", 400)

    try:
        verify_otp(roll, otp_plain)
    except OtpError as exc:
        return json_error(str(exc), "OTP_INVALID", 401)
    except Exception as exc:
        logger.exception("Unexpected OTP verify error for %s: %s", roll, exc)
        return json_error("Verification failed. Please try again.", "OTP_ERROR", 500)

    set_session_roll(roll)
    return json_ok("OTP verified. You are now logged in.", "OTP_VERIFIED", roll=roll)


@auth_bp.post("/logout")
def logout():
    clear_session()
    return json_ok("Logged out.")


@auth_bp.get("/me")
def me():
    roll = get_session_roll()
    if not roll:
        return json_error("Not authenticated.", "UNAUTHORIZED", 401)
    user: User | None = db.session.get(User, roll)
    if not user:
        clear_session()
        return json_error("User not found.", "NOT_FOUND", 404)
    return json_ok("ok", "OK", user=user.to_dict())


@auth_bp.post("/profile")
@login_required
@limiter.limit("20 per hour")
def save_profile():
    """Save student name and branch after OTP verification, before capture."""
    roll = get_session_roll()
    assert roll is not None

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    branch = (data.get("branch") or "").strip().upper()

    if not name or len(name) < 2 or len(name) > 100:
        return json_error("Please enter your full name (2–100 characters).", "INVALID_NAME", 400)
    if branch not in VALID_BRANCHES:
        return json_error(
            f"Branch must be one of: {', '.join(VALID_BRANCHES)}.",
            "INVALID_BRANCH",
            400,
        )

    user: User | None = db.session.get(User, roll)
    if not user:
        return json_error("User not found.", "NOT_FOUND", 404)

    user.name = name
    user.branch = branch
    db.session.commit()

    return json_ok("Profile saved.", "PROFILE_SAVED", user=user.to_dict())
