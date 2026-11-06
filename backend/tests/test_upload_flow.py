"""Tests for the photo upload flow."""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_minimal_jpeg() -> bytes:
    """Return a minimal valid JPEG byte string (>1000 bytes)."""
    header = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e\xc1"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
        b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
        b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd3\xff\xd9"
    )
    return header + b"\x00" * 1200


def _setup_logged_in(client, app, roll="524cs0019"):
    """Log in as roll via a verified session."""
    with app.app_context():
        from app.models.user import User
        from app.extensions import db
        if not db.session.get(User, roll):
            u = User(roll=roll, email=f"{roll}@iiitk.ac.in")
            db.session.add(u)
            db.session.commit()
    with client.session_transaction() as sess:
        sess["verified_roll"] = roll
        sess["_permanent"] = True


def _make_face_result(
    yaw_ratio=0.0,
    pitch_ratio=0.30,
    score=0.95,
    w=640,
    h=480,
    embedding=None,
):
    """Create a mock FaceResult that passes all checks."""
    from app.services.face_service import FaceResult
    if embedding is None:
        embedding = np.random.rand(512).astype(np.float32)
        embedding /= np.linalg.norm(embedding)
    margin = 60
    bbox = (float(margin), float(margin), float(w - margin), float(h - margin))
    eye_y = 100.0
    mouth_y = 200.0
    keypoints = np.array(
        [
            [100.0, eye_y],
            [200.0, eye_y],
            [150.0 + yaw_ratio * 100.0, eye_y + pitch_ratio * (mouth_y - eye_y)],
            [120.0, mouth_y],
            [180.0, mouth_y],
        ],
        dtype=np.float32,
    )
    return FaceResult(
        det_score=score,
        keypoints=keypoints,
        embedding=embedding,
        bbox=bbox,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_upload_requires_auth(client):
    resp = client.post("/api/photos/upload")
    assert resp.status_code == 401


def test_upload_wrong_pose_order(client, app):
    """Uploading RIGHT before FRONT is accepted must fail with 409 WRONG_POSE_ORDER."""
    _setup_logged_in(client, app, "poseorder1")
    data = {"pose": "RIGHT", "image": (io.BytesIO(make_minimal_jpeg()), "photo.jpg")}
    with patch("app.services.photo_service.analyse") as mock_analyse, \
         patch("app.services.photo_service.cv2") as mock_cv2:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 200.0
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [_make_face_result()]
        resp = client.post(
            "/api/photos/upload",
            data=data,
            content_type="multipart/form-data",
        )
    assert resp.status_code == 409
    assert resp.get_json()["code"] == "WRONG_POSE_ORDER"


def test_upload_no_face(client, app):
    """Rejection when no face is found."""
    _setup_logged_in(client, app, "noface001")
    data = {"pose": "FRONT", "image": (io.BytesIO(make_minimal_jpeg()), "photo.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse", return_value=[]):
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        resp = client.post("/api/photos/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "NO_FACE"


def test_upload_multiple_faces(client, app):
    """Rejection when multiple faces are detected."""
    _setup_logged_in(client, app, "multiface001")
    data = {"pose": "FRONT", "image": (io.BytesIO(make_minimal_jpeg()), "photo.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_analyse.return_value = [_make_face_result(), _make_face_result()]
        resp = client.post("/api/photos/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "MULTIPLE_FACES"


def test_upload_blurry_image(client, app):
    """Rejection when image is too blurry."""
    _setup_logged_in(client, app, "blurry001")
    data = {"pose": "FRONT", "image": (io.BytesIO(make_minimal_jpeg()), "photo.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 10.0  # Below the minimum blur threshold
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [_make_face_result()]
        resp = client.post("/api/photos/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "BLURRY_IMAGE"


def test_upload_wrong_pose_angles(client, app):
    """A frontal photo is rejected when keypoints show a large side turn."""
    _setup_logged_in(client, app, "wrongangle001")
    data = {"pose": "FRONT", "image": (io.BytesIO(make_minimal_jpeg()), "photo.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 150.0
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [_make_face_result(yaw_ratio=0.20)]
        resp = client.post("/api/photos/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["code"] == "WRONG_POSE"


def test_upload_requires_left_turn_for_second_photo(client, app):
    """The second photo requires the configured left-facing keypoint ratio."""
    roll = "leftpose001"
    _setup_logged_in(client, app, roll)
    shared_emb = np.zeros(512, dtype=np.float32)
    shared_emb[0] = 1.0

    def upload(pose, image_bytes):
        data = {"pose": pose, "image": (io.BytesIO(image_bytes), f"{pose}.jpg")}
        with patch("app.services.photo_service.cv2") as mock_cv2, \
             patch("app.services.photo_service.analyse") as mock_analyse:
            mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
            mock_cv2.COLOR_BGR2GRAY = 6
            mock_cv2.cvtColor.return_value = MagicMock()
            mock_cv2.Laplacian.return_value.var.return_value = 150.0
            mock_cv2.CV_64F = 6
            mock_analyse.return_value = [
                _make_face_result(embedding=shared_emb)
            ]
            return client.post(
                "/api/photos/upload",
                data=data,
                content_type="multipart/form-data",
            )

    first = upload("PHOTO_1", make_minimal_jpeg())
    assert first.status_code == 201

    second = upload("PHOTO_2", make_minimal_jpeg() + b"new-frame")
    assert second.status_code == 422
    assert second.get_json()["code"] == "WRONG_POSE"
    assert second.get_json()["message"] == "Turn a bit more to your LEFT."


def test_pose_attempts_allow_submit_anyway_and_valid_pose_stays_verified(
    client, app, tmp_path, monkeypatch
):
    roll = "poseoverride001"
    _setup_logged_in(client, app, roll)
    shared_emb = np.zeros(512, dtype=np.float32)
    shared_emb[0] = 1.0
    monkeypatch.setitem(app.config, "PHOTOS_DIR", str(tmp_path))

    def upload(pose, image_bytes, yaw_ratio=0.0, submit_anyway=False):
        data = {
            "pose": pose,
            "image": (io.BytesIO(image_bytes), f"{pose}.jpg"),
        }
        if submit_anyway:
            data["submit_anyway"] = "true"
        with patch("app.services.photo_service.cv2") as mock_cv2, \
             patch("app.services.photo_service.analyse") as mock_analyse:
            mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
            mock_cv2.COLOR_BGR2GRAY = 6
            mock_cv2.cvtColor.return_value = MagicMock()
            mock_cv2.Laplacian.return_value.var.return_value = 150.0
            mock_cv2.CV_64F = 6
            mock_analyse.return_value = [
                _make_face_result(
                    yaw_ratio=yaw_ratio,
                    embedding=shared_emb,
                )
            ]
            return client.post(
                "/api/photos/upload",
                data=data,
                content_type="multipart/form-data",
            )

    assert upload("PHOTO_1", make_minimal_jpeg()).status_code == 201
    too_early = upload(
        "PHOTO_2",
        make_minimal_jpeg() + b"early",
        yaw_ratio=0.0,
        submit_anyway=True,
    )
    assert too_early.status_code == 422
    assert too_early.get_json()["code"] == "SUBMIT_ANYWAY_NOT_AVAILABLE"

    for attempt in range(3):
        response = upload(
            "PHOTO_2",
            make_minimal_jpeg() + bytes([attempt + 1]),
            yaw_ratio=0.0,
        )
        assert response.status_code == 422
        assert response.get_json()["pose_attempts"] == attempt + 1

    unavailable = upload(
        "PHOTO_2",
        make_minimal_jpeg() + b"early",
        yaw_ratio=0.2,
        submit_anyway=True,
    )
    assert unavailable.status_code == 201
    assert unavailable.get_json()["photo"]["pose_verified"] is True


def test_submit_anyway_saves_unverified_after_three_pose_failures(
    client, app, tmp_path, monkeypatch
):
    roll = "poseoverride002"
    _setup_logged_in(client, app, roll)
    shared_emb = np.zeros(512, dtype=np.float32)
    shared_emb[0] = 1.0
    monkeypatch.setitem(app.config, "PHOTOS_DIR", str(tmp_path))

    def upload(pose, image_bytes, yaw_ratio=0.0, submit_anyway=False):
        data = {
            "pose": pose,
            "image": (io.BytesIO(image_bytes), f"{pose}.jpg"),
        }
        if submit_anyway:
            data["submit_anyway"] = "true"
        with patch("app.services.photo_service.cv2") as mock_cv2, \
             patch("app.services.photo_service.analyse") as mock_analyse:
            mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
            mock_cv2.COLOR_BGR2GRAY = 6
            mock_cv2.cvtColor.return_value = MagicMock()
            mock_cv2.Laplacian.return_value.var.return_value = 150.0
            mock_cv2.CV_64F = 6
            mock_analyse.return_value = [
                _make_face_result(yaw_ratio=yaw_ratio, embedding=shared_emb)
            ]
            return client.post(
                "/api/photos/upload",
                data=data,
                content_type="multipart/form-data",
            )

    assert upload("PHOTO_1", make_minimal_jpeg()).status_code == 201
    for attempt in range(3):
        response = upload(
            "PHOTO_2",
            make_minimal_jpeg() + bytes([attempt + 1]),
        )
        assert response.status_code == 422

    accepted = upload(
        "PHOTO_2",
        make_minimal_jpeg() + b"submit",
        submit_anyway=True,
    )
    assert accepted.status_code == 201
    assert accepted.get_json()["photo"]["pose_verified"] is False
    with app.app_context():
        from app.extensions import db
        from app.models.photo import Photo

        saved = db.session.query(Photo).filter_by(roll=roll, pose="PHOTO_2").one()
        assert saved.pose_verified is False


def test_debug_pose_ratios_are_returned_at_top_level(client, app, tmp_path, monkeypatch):
    roll = "posedebug001"
    _setup_logged_in(client, app, roll)
    monkeypatch.setitem(app.config, "PHOTOS_DIR", str(tmp_path))
    monkeypatch.setitem(app.config, "DEBUG_POSE", True)
    data = {"pose": "PHOTO_1", "image": (io.BytesIO(make_minimal_jpeg()), "debug.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 150.0
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [_make_face_result(yaw_ratio=0.04, pitch_ratio=0.3)]
        response = client.post(
            "/api/photos/upload",
            data=data,
            content_type="multipart/form-data",
        )
    body = response.get_json()
    assert response.status_code == 201
    assert body["pose_debug"]["yaw_ratio"] == pytest.approx(0.04)
    assert body["pose_debug"]["pitch_ratio"] == pytest.approx(0.30)
    assert body["pose_debug"]["thresholds"]["front_yaw_max"] == pytest.approx(0.15)

def test_upload_different_person(client, app):
    """Rejection when photo 2 does not match photo 1's embedding."""
    roll = "diffperson001"
    _setup_logged_in(client, app, roll)

    base_emb = np.zeros(512, dtype=np.float32)
    base_emb[0] = 1.0  # unit vector along axis 0

    diff_emb = np.zeros(512, dtype=np.float32)
    diff_emb[1] = 1.0  # orthogonal unit vector (cosine similarity = 0.0)

    # First photo: FRONT
    data1 = {"pose": "FRONT", "image": (io.BytesIO(make_minimal_jpeg()), "p1.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 150.0
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [_make_face_result(embedding=base_emb)]
        resp1 = client.post("/api/photos/upload", data=data1, content_type="multipart/form-data")
        assert resp1.status_code == 201

    # Second photo has a valid left turn but belongs to another person.
    data2 = {"pose": "PHOTO_2", "image": (io.BytesIO(make_minimal_jpeg() + b"photo2_bytes"), "p2.jpg")}
    with patch("app.services.photo_service.cv2") as mock_cv2, \
         patch("app.services.photo_service.analyse") as mock_analyse:
        mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
        mock_cv2.COLOR_BGR2GRAY = 6
        mock_cv2.cvtColor.return_value = MagicMock()
        mock_cv2.Laplacian.return_value.var.return_value = 150.0
        mock_cv2.CV_64F = 6
        mock_analyse.return_value = [
            _make_face_result(yaw_ratio=0.25, embedding=diff_emb)
        ]
        resp2 = client.post("/api/photos/upload", data=data2, content_type="multipart/form-data")
    assert resp2.status_code == 422
    assert resp2.get_json()["code"] == "DIFFERENT_PERSON"


def test_four_photos_completion_flow(client, app):
    """4 valid photos saved as photos/524cs0019/... and DB shows completed=1."""
    roll = "524cs0019"
    _setup_logged_in(client, app, roll)

    temp_photos_dir = tempfile.mkdtemp()
    app.config["PHOTOS_DIR"] = temp_photos_dir

    try:
        shared_emb = np.zeros(512, dtype=np.float32)
        shared_emb[0] = 1.0

        poses = [
            ("PHOTO_1", 0.0, 0.30),
            ("PHOTO_2", 0.25, 0.30),
            ("PHOTO_3", -0.25, 0.30),
            ("PHOTO_4", 0.0, 0.23),
        ]

        for idx, (pose_name, yaw_ratio, pitch_ratio) in enumerate(poses, start=1):
            # Unique bytes for each photo to avoid sha256 duplicate check
            img_bytes = make_minimal_jpeg() + idx.to_bytes(4, "big")
            data = {"pose": pose_name, "image": (io.BytesIO(img_bytes), f"{pose_name}.jpg")}

            with patch("app.services.photo_service.cv2") as mock_cv2, \
                 patch("app.services.photo_service.analyse") as mock_analyse:
                mock_cv2.imdecode.return_value = MagicMock(shape=(480, 640, 3))
                mock_cv2.COLOR_BGR2GRAY = 6
                mock_cv2.cvtColor.return_value = MagicMock()
                mock_cv2.Laplacian.return_value.var.return_value = 150.0
                mock_cv2.CV_64F = 6
                mock_analyse.return_value = [
                    _make_face_result(
                        yaw_ratio=yaw_ratio,
                        pitch_ratio=pitch_ratio,
                        score=0.95,
                        embedding=shared_emb,
                    )
                ]

                resp = client.post("/api/photos/upload", data=data, content_type="multipart/form-data")
                assert resp.status_code == 201
                body = resp.get_json()
                assert body["ok"] is True
                if idx < 4:
                    assert body["all_done"] is False
                else:
                    assert body["all_done"] is True

        # Check DB status
        with app.app_context():
            from app.models.user import User
            from app.models.photo import Photo
            from app.extensions import db

            user = db.session.get(User, roll)
            assert user is not None
            assert user.completed is True
            assert user.photo_count == 4
            assert user.completed_at is not None

            photos = db.session.query(Photo).filter(Photo.roll == roll).order_by(Photo.photo_no).all()
            assert len(photos) == 4
            assert photos[0].pitch_ratio == pytest.approx(0.30)
            assert all(p.pose_verified for p in photos)
            for i, p in enumerate(photos, start=1):
                assert p.photo_no == i
                assert os.path.exists(p.path)

    finally:
        shutil.rmtree(temp_photos_dir, ignore_errors=True)


def test_resume_at_correct_pose(client, app):
    """After 2 photos, /api/photos/status returns next_pose = 'RIGHT'."""
    roll = "resume001"
    _setup_logged_in(client, app, roll)

    with app.app_context():
        from app.models.photo import Photo
        from app.extensions import db
        import numpy as np

        embedding = np.zeros(512, dtype=np.float32).tobytes()
        for i, pose_name in enumerate(["PHOTO_1", "PHOTO_2"], start=1):
            p = Photo(
                roll=roll,
                photo_no=i,
                pose=pose_name,
                path=f"/tmp/{roll}_{i}.jpg",
                confidence=0.95,
                yaw=0.0,
                pitch=0.0,
                roll_angle=0.0,
                yaw_ratio=0.0,
                pitch_ratio=0.30 if i == 1 else 0.30,
                sha256=f"abc{i}" * 16,
                embedding=embedding,
            )
            db.session.add(p)
        from app.models.user import User
        u = db.session.get(User, roll)
        u.photo_count = 2
        db.session.commit()

    resp = client.get("/api/photos/status")
    data = resp.get_json()
    assert data["ok"] is True
    assert data["next_pose"] == "PHOTO_3"
    assert len(data["accepted_poses"]) == 2
    assert data["front_pitch_ratio"] == pytest.approx(0.30)
    assert data["pose_attempts"] == 0
    assert data["pose_thresholds"]["side_yaw_min"] == pytest.approx(0.18)
