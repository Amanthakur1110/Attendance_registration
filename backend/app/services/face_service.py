"""InsightFace wrapper — loads the model once, provides thread-safe inference."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_face_app: "insightface.app.FaceAnalysis | None" = None  # type: ignore[name-defined]


@dataclass
class FaceResult:
    """Parsed result for a single face detected in an image."""

    det_score: float
    yaw: float    # degrees; positive = face turns to the person's left (InsightFace convention)
    pitch: float  # degrees; positive = face tilts up
    roll: float   # degrees; in-plane roll
    embedding: np.ndarray  # 512-dim (buffalo_s) or 512-dim (buffalo_l)
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2


def get_face_service():
    """Return the singleton FaceAnalysis app, loading it on first call."""
    global _face_app
    if _face_app is not None:
        return _face_app
    with _lock:
        if _face_app is not None:  # double-checked locking
            return _face_app
        _face_app = _load_model()
    return _face_app


def _load_model():
    """Load InsightFace model. Imports are inside to allow the rest of the app
    to start even if InsightFace is not installed (e.g. during unit tests)."""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        from flask import current_app

        model_name = current_app.config.get("INSIGHTFACE_MODEL", "buffalo_s")
        logger.info("Loading InsightFace model: %s", model_name)
        fa = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        fa.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded: %s", model_name)
        return fa
    except Exception as exc:
        logger.error("Could not load InsightFace: %s", exc)
        raise


def analyse(image_bytes: bytes) -> list[FaceResult]:
    """
    Analyse image bytes with InsightFace.
    Returns a list of FaceResult (one per detected face).
    Filters by faces that have pose and embedding data.
    """
    import cv2
    import numpy as np

    fa = get_face_service()

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    with _lock:
        faces = fa.get(img)

        # If no face found or confidence is borderline, enhance lighting/contrast and retry
        best_score = max((float(f.det_score) for f in faces), default=0.0)
        if len(faces) == 0 or best_score < 0.35:
            # 1. CLAHE adaptive histogram equalization on luminance
            try:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                enhanced_l = clahe.apply(l)
                enhanced_lab = cv2.merge((enhanced_l, a, b))
                enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                clahe_faces = fa.get(enhanced_img)
                if len(clahe_faces) > 0 and max((float(f.det_score) for f in clahe_faces), default=0.0) > best_score:
                    faces = clahe_faces
                    best_score = max((float(f.det_score) for f in faces), default=0.0)
            except Exception as e:
                logger.debug("CLAHE enhancement skipped: %s", e)

            # 2. Gamma boost for low-light/dim room environments
            if len(faces) == 0:
                try:
                    gamma = 1.45
                    inv_gamma = 1.0 / gamma
                    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                    brightened = cv2.LUT(img, table)
                    bright_faces = fa.get(brightened)
                    if len(bright_faces) > 0:
                        faces = bright_faces
                except Exception as e:
                    logger.debug("Gamma boost skipped: %s", e)

    results: list[FaceResult] = []
    for face in faces:
        if not hasattr(face, "pose") or face.pose is None:
            continue
        if not hasattr(face, "embedding") or face.embedding is None:
            continue

        pitch, yaw, roll = float(face.pose[0]), float(face.pose[1]), float(face.pose[2])
        bbox = tuple(face.bbox.tolist())  # type: ignore[arg-type]
        results.append(
            FaceResult(
                det_score=float(face.det_score),
                yaw=yaw,
                pitch=pitch,
                roll=roll,
                embedding=face.embedding,
                bbox=bbox,  # type: ignore[arg-type]
            )
        )
    return results


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

