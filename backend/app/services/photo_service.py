"""Photo upload pipeline: validation, saving, DB recording."""
from __future__ import annotations

import csv
import hashlib
import logging
import os
import tempfile
from datetime import datetime, timezone

import cv2
import numpy as np

from flask import current_app

from ..extensions import db
from ..models.photo import Photo
from ..models.user import User
from ..services.face_service import analyse, cosine_similarity, FaceResult
from ..services.pose_service import POSES, POSE_NAMES, get_pose, check_pose, normalize_pose_name
from ..utils.validators import validate_image_bytes

logger = logging.getLogger(__name__)

MIN_FACE_FRACTION = 0.08   # face width / image width
MIN_RESOLUTION = (320, 240)  # (width, height)
BLUR_THRESHOLD = 18.0       # variance of Laplacian (generous threshold for normal webcams)


class PhotoError(Exception):
    """Raised when a photo fails validation; carries an error code."""
    def __init__(self, message: str, code: str = "PHOTO_REJECTED"):
        super().__init__(message)
        self.code = code


def get_accepted_poses(roll: str) -> list[str]:
    """Return list of pose names already accepted for this roll, in order."""
    rows = (
        db.session.query(Photo)
        .filter(Photo.roll == roll)
        .order_by(Photo.photo_no)
        .all()
    )
    return [normalize_pose_name(r.pose) for r in rows]


def get_next_pose_name(roll: str) -> str | None:
    """Return the name of the next expected pose, or None if all done."""
    accepted = get_accepted_poses(roll)
    for pose in POSE_NAMES:
        if pose not in accepted:
            return pose
    return None


def process_upload(roll: str, image_bytes: bytes, claimed_pose: str) -> dict:
    """
    Full validation pipeline for a photo upload.
    Returns a dict with photo info on success.
    Raises PhotoError on any validation failure.
    """
    claimed_pose = normalize_pose_name(claimed_pose)

    # ── 1. User / completion guard ─────────────────────────────────────────
    user: User | None = db.session.get(User, roll)
    if user and user.completed:
        raise PhotoError("You have already submitted all photos.", "ALREADY_COMPLETED")

    # ── 2. Pose sequence check ─────────────────────────────────────────────
    next_pose_name = get_next_pose_name(roll)
    if next_pose_name is None:
        raise PhotoError("All photos have already been submitted.", "ALREADY_COMPLETED")

    accepted = get_accepted_poses(roll)
    if claimed_pose in accepted:
        raise PhotoError(
            f"The '{claimed_pose}' pose has already been accepted.",
            "POSE_ALREADY_ACCEPTED",
        )
    if claimed_pose != next_pose_name:
        raise PhotoError(
            f"Expected pose '{next_pose_name}' next, but received '{claimed_pose}'. "
            f"Please follow the guided sequence.",
            "WRONG_POSE_ORDER",
        )

    expected_pose_cfg = get_pose(next_pose_name)
    assert expected_pose_cfg is not None  # always exists

    # ── 3. File validation ─────────────────────────────────────────────────
    valid, err = validate_image_bytes(image_bytes)
    if not valid:
        raise PhotoError(err, "INVALID_FILE")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise PhotoError("Could not decode image. Please try again.", "DECODE_ERROR")

    h, w = img.shape[:2]
    if w < MIN_RESOLUTION[0] or h < MIN_RESOLUTION[1]:
        raise PhotoError(
            f"Image resolution too low ({w}×{h}). Minimum is {MIN_RESOLUTION[0]}×{MIN_RESOLUTION[1]}.",
            "LOW_RESOLUTION",
        )

    # ── 4. Brightness check ────────────────────────────────────────────────
    if isinstance(img, np.ndarray):
        gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if isinstance(gray_full, np.ndarray):
            mean_lum = float(np.mean(gray_full))
            if mean_lum < 16.0:
                raise PhotoError(
                    "The photo is too dark. Please face towards a light source or turn on a room light.",
                    "TOO_DARK",
                )

    # ── 5. Face detection ──────────────────────────────────────────────────
    threshold = current_app.config.get("FACE_CONFIDENCE_THRESHOLD", 0.25)
    try:
        all_faces = analyse(image_bytes)
    except Exception as exc:
        logger.error("Face analysis failed: %s", exc)
        raise PhotoError("Face analysis failed. Please try again.", "FACE_ANALYSIS_ERROR")

    good_faces = [f for f in all_faces if f.det_score >= threshold]

    # If single face found with score slightly below threshold, accept it
    if len(good_faces) == 0 and len(all_faces) == 1 and all_faces[0].det_score >= 0.20:
        good_faces = all_faces

    if len(good_faces) == 0:
        raise PhotoError(
            "No clear face detected. Please ensure your face is well lit, centered, and looking towards the camera.",
            "NO_FACE",
        )
    if len(good_faces) > 1:
        raise PhotoError(
            "Multiple people detected. Only you should be in the frame.",
            "MULTIPLE_FACES",
        )

    face: FaceResult = good_faces[0]

    # ── 5. Face size and bounds check ──────────────────────────────────────
    x1, y1, x2, y2 = face.bbox
    face_w = x2 - x1
    face_h = y2 - y1

    if face_w / w < MIN_FACE_FRACTION:
        raise PhotoError("Move closer to the camera.", "FACE_TOO_SMALL")

    # Face must be fully inside the frame (with a small margin)
    margin = 5
    if x1 < margin or y1 < margin or x2 > w - margin or y2 > h - margin:
        raise PhotoError(
            "Your face is partly outside the camera frame. Move back and keep your whole face visible.",
            "FACE_OUT_OF_BOUNDS",
        )

    # ── 6. Blur check ──────────────────────────────────────────────────────
    x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
    face_crop = img[y1i:y2i, x1i:x2i]
    gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())
    blur_threshold = BLUR_THRESHOLD
    if blur_score < blur_threshold:
        raise PhotoError(
            "Image is too blurry. Hold the camera steady and try again.",
            "BLURRY_IMAGE",
        )

    previous_photos: list[Photo] = (
        db.session.query(Photo)
        .filter(Photo.roll == roll)
        .order_by(Photo.photo_no)
        .all()
    )

    # ── 7. Requested front/side-view pose check ─────────────────────────────
    pose_result = check_pose(
        expected_pose_cfg,
        face.yaw,
        face.pitch,
        face.roll,
        [photo.yaw for photo in previous_photos],
    )
    if not pose_result.ok:
        raise PhotoError(pose_result.message, "WRONG_POSE")

    # ── 8. Duplicate check (SHA-256) ───────────────────────────────────────
    sha = hashlib.sha256(image_bytes).hexdigest()
    existing_sha = (
        db.session.query(Photo).filter(Photo.roll == roll, Photo.sha256 == sha).first()
    )
    if existing_sha:
        raise PhotoError(
            "This exact image has already been uploaded. Please take a new photo.",
            "DUPLICATE_IMAGE",
        )

    # ── 9. Same-person check (embedding cosine similarity) ─────────────────
    photo_no = len(accepted) + 1
    if photo_no > 1:
        threshold_sim = current_app.config["SAME_PERSON_THRESHOLD"]
        for previous_photo in previous_photos:
            if previous_photo.embedding:
                ref_embedding = np.frombuffer(previous_photo.embedding, dtype=np.float32)
                sim = cosine_similarity(face.embedding, ref_embedding)
                if sim < threshold_sim:
                    raise PhotoError(
                        "This does not appear to be the same person as your earlier photos. "
                        "Please ensure only you are in the frame.",
                        "DIFFERENT_PERSON",
                    )

    # ── 10. Save atomically + DB insert ────────────────────────────────────
    _save_photo_atomic(
        roll=roll,
        photo_no=photo_no,
        pose=next_pose_name,
        image_bytes=image_bytes,
        face=face,
        sha=sha,
    )

    return {
        "photo_no": photo_no,
        "pose": next_pose_name,
        "confidence": face.det_score,
        "yaw": face.yaw,
        "pitch": face.pitch,
        "roll_angle": face.roll,
    }


def _save_photo_atomic(
    roll: str,
    photo_no: int,
    pose: str,
    image_bytes: bytes,
    face: FaceResult,
    sha: str,
) -> None:
    """
    Write the photo to disk (temp → os.replace) then insert the DB row.
    On DB failure, remove the file.  On file failure, do not touch the DB.
    """
    photos_dir = current_app.config["PHOTOS_DIR"]
    roll_dir = os.path.join(photos_dir, roll)
    os.makedirs(roll_dir, exist_ok=True)

    filename = f"{roll}_{photo_no}_{pose}.jpg"
    final_path = os.path.join(roll_dir, filename)

    # Write to temp file then atomically rename
    fd, tmp_path = tempfile.mkstemp(dir=roll_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image_bytes)
        os.replace(tmp_path, final_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # DB insert
    try:
        user: User | None = db.session.get(User, roll)
        if not user:
            raise RuntimeError(f"User {roll} not found in DB during photo save.")

        embedding_bytes = face.embedding.astype(np.float32).tobytes()

        photo_row = Photo(
            roll=roll,
            photo_no=photo_no,
            pose=pose,
            path=final_path,
            confidence=face.det_score,
            yaw=face.yaw,
            pitch=face.pitch,
            roll_angle=face.roll,
            sha256=sha,
            embedding=embedding_bytes,
        )
        db.session.add(photo_row)

        user.photo_count = photo_no
        if photo_no == len(POSES):
            user.completed = True
            user.completed_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info(
            "Photo saved: roll=%s, no=%d, pose=%s, path=%s", roll, photo_no, pose, final_path
        )

        # Write / update CSV for this student's folder
        _write_student_csv(user, roll_dir)

    except Exception:
        # Roll back and remove the file so disk and DB stay consistent
        db.session.rollback()
        try:
            os.unlink(final_path)
        except OSError:
            pass
        raise


def _write_student_csv(user: User, roll_dir: str) -> None:
    """Write (or overwrite) <roll_dir>/student_info.csv with name, branch, roll."""
    csv_path = os.path.join(roll_dir, "student_info.csv")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["roll", "name", "branch", "email", "completed_at"])
            writer.writeheader()
            writer.writerow({
                "roll": user.roll,
                "name": user.name or "",
                "branch": user.branch or "",
                "email": user.email,
                "completed_at": user.completed_at.isoformat() if user.completed_at else "",
            })
    except Exception as exc:
        logger.warning("Could not write student CSV for %s: %s", user.roll, exc)
