"""Photos blueprint: upload + status."""
from __future__ import annotations

import logging

from flask import Blueprint, request
from flask import current_app

from ..extensions import limiter
from ..models.photo import Photo
from ..models.user import User
from ..extensions import db
from ..services.photo_service import (
    PhotoError,
    get_accepted_poses,
    get_next_pose_name,
    get_pose_attempt_count,
    process_upload,
)
from ..services.pose_service import (
    POSES,
    POSE_NAMES,
    POSE_ALIASES,
    get_pose_thresholds,
    normalize_pose_name,
)
from ..utils.responses import json_error, json_ok
from ..utils.security import get_session_roll, login_required
from ..utils.validators import validate_image_bytes

photos_bp = Blueprint("photos", __name__)
logger = logging.getLogger(__name__)

ALLOWED_POSES = set(POSE_NAMES) | set(POSE_ALIASES.keys())


@photos_bp.post("/upload")
@login_required
@limiter.limit("120 per hour")
def upload_photo():
    roll = get_session_roll()
    assert roll is not None  # guaranteed by @login_required

    # ── Multipart form data ────────────────────────────────────────────────
    if "image" not in request.files:
        return json_error("No image file provided.", "MISSING_FILE", 400)

    file = request.files["image"]
    raw_pose = (request.form.get("pose") or "").strip().upper()
    claimed_pose = normalize_pose_name(raw_pose)

    if not claimed_pose or (raw_pose not in ALLOWED_POSES and claimed_pose not in ALLOWED_POSES):
        return json_error(
            f"Invalid photo step. Must be one of: {', '.join(POSE_NAMES)}.",
            "INVALID_POSE",
            400,
        )

    image_bytes = file.read()
    submit_anyway = request.form.get("submit_anyway", "").strip().lower() in {
        "1", "true", "yes", "on"
    }

    # Quick file validation before expensive face analysis
    valid, err = validate_image_bytes(image_bytes)
    if not valid:
        return json_error(err, "INVALID_FILE", 422)

    try:
        result = process_upload(roll, image_bytes, claimed_pose, submit_anyway)
    except PhotoError as exc:
        status = 409 if exc.code in ("WRONG_POSE_ORDER", "POSE_ALREADY_ACCEPTED", "ALREADY_COMPLETED") else 422
        return json_error(str(exc), exc.code, status, **exc.details)
    except Exception as exc:
        logger.exception("Unexpected upload error for roll=%s: %s", roll, exc)
        return json_error("An error occurred while processing your photo. Please try again.", "SERVER_ERROR", 500)

    # Determine whether all done
    next_pose = get_next_pose_name(roll)
    all_done = next_pose is None

    response_fields = {
        "photo": result,
        "next_pose": next_pose,
        "all_done": all_done,
    }
    if "pose_debug" in result:
        response_fields["pose_debug"] = result["pose_debug"]

    return json_ok(
        "Photo accepted.",
        "PHOTO_ACCEPTED",
        status=201,
        **response_fields,
    )


@photos_bp.get("/status")
@login_required
def photo_status():
    roll = get_session_roll()
    assert roll is not None

    user: User | None = db.session.get(User, roll)
    accepted = get_accepted_poses(roll)
    next_pose = get_next_pose_name(roll)
    front_photo = (
        db.session.query(Photo)
        .filter_by(roll=roll, pose="PHOTO_1")
        .first()
    )

    poses_info = []
    for pose_cfg in POSES:
        poses_info.append({
            "name": pose_cfg.name,
            "label": pose_cfg.label,
            "instruction": pose_cfg.instruction,
            "accepted": pose_cfg.name in accepted,
        })

    return json_ok(
        "ok",
        "OK",
        accepted_poses=accepted,
        next_pose=next_pose,
        photo_count=user.photo_count if user else 0,
        completed=user.completed if user else False,
        poses=poses_info,
        front_pitch_ratio=front_photo.pitch_ratio if front_photo else None,
        pose_attempts=(
            get_pose_attempt_count(roll, next_pose) if next_pose else 0
        ),
        pose_thresholds=get_pose_thresholds(current_app.config),
        debug_pose=bool(current_app.config.get("DEBUG_POSE", False)),
    )
