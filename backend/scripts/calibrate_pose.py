"""Print keypoint pose ratios for one image or a folder of calibration photos.

Examples:
    python backend/scripts/calibrate_pose.py --folder path/to/photos
    python backend/scripts/calibrate_pose.py --image path/to/photo.jpg
    python backend/scripts/calibrate_pose.py --webcam
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.pose_service import compute_pose_ratios  # noqa: E402


def build_face_analyser():
    from insightface.app import FaceAnalysis

    face_app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
    face_app.prepare(ctx_id=0, det_size=(640, 640))
    return face_app


def report_faces(path: Path, image, face_app) -> None:
    faces = face_app.get(image)
    if not faces:
        print(f"{path}: no face detected")
        return

    for index, face in enumerate(faces, start=1):
        try:
            yaw_ratio, pitch_ratio = compute_pose_ratios(np.asarray(face.kps))
            print(
                f"{path} face {index}: det_score={float(face.det_score):.3f} "
                f"yaw_ratio={yaw_ratio:+.4f} pitch_ratio={pitch_ratio:+.4f}"
            )
        except (AttributeError, TypeError, ValueError, IndexError) as exc:
            print(f"{path} face {index}: keypoint ratios unavailable ({exc})")


def calibrate_image(image_path: Path, face_app) -> None:
    import cv2

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"{image_path}: could not read image")
        return
    report_faces(image_path, image, face_app)


def calibrate_folder(folder: Path, face_app) -> None:
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_paths = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in image_extensions
    )
    if not image_paths:
        raise ValueError(f"No supported photos found in folder: {folder}")
    for image_path in image_paths:
        calibrate_image(image_path, face_app)


def calibrate_webcam(face_app) -> None:
    import cv2

    print("Opening webcam... Press 's' to analyze a frame, 'q' to quit.")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Could not open webcam.")
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            cv2.imshow("Pose Ratio Calibration", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                report_faces(Path("webcam"), frame, face_app)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate facial keypoint pose ratios.")
    parser.add_argument("--image", type=Path, help="Analyze one image")
    parser.add_argument("--folder", type=Path, help="Analyze all supported images recursively")
    parser.add_argument("--webcam", action="store_true", help="Run interactive webcam calibration")
    args = parser.parse_args()

    if sum(bool(value) for value in (args.image, args.folder, args.webcam)) != 1:
        parser.error("Choose exactly one of --image, --folder, or --webcam.")

    face_analyser = build_face_analyser()
    if args.image:
        calibrate_image(args.image, face_analyser)
    elif args.folder:
        if not args.folder.is_dir():
            parser.error(f"Not a folder: {args.folder}")
        calibrate_folder(args.folder, face_analyser)
    else:
        calibrate_webcam(face_analyser)
