"""
Pose calibration helper script.

Run this script to inspect InsightFace's yaw, pitch, and roll angles for an image or
live camera test:
    python backend/scripts/calibrate_pose.py --image path/to/sample.jpg
    python backend/scripts/calibrate_pose.py --webcam

InsightFace (buffalo_s / buffalo_l) Angle Conventions:
- Yaw:
    positive (+) -> person turned their head to their LEFT (viewer's right in mirrored preview)
    negative (-) -> person turned their head to their RIGHT (viewer's left in mirrored preview)
- Pitch:
    positive (+) -> person tilted their head UPWARD (chin up)
    negative (-) -> person tilted their head DOWNWARD (chin down)
- Roll:
    in-plane rotation around line of sight.

This script verifies how angles are reported for your setup.
"""
from __future__ import annotations

import argparse
import sys
import numpy as np


def calibrate_image(image_path: str):
    import cv2
    import insightface
    from insightface.app import FaceAnalysis

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return

    fa = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
    fa.prepare(ctx_id=0, det_size=(640, 640))
    faces = fa.get(img)

    if not faces:
        print("No faces detected in image.")
        return

    for idx, face in enumerate(faces):
        pitch, yaw, roll = face.pose
        print(f"\nFace #{idx + 1}:")
        print(f"  Detection Score: {face.det_score:.3f}")
        print(f"  Yaw:             {yaw:+.2f}° (InsightFace: positive = person's left)")
        print(f"  Pitch:           {pitch:+.2f}° (InsightFace: positive = chin up)")
        print(f"  Roll:            {roll:+.2f}° (in-plane tilt)")


def calibrate_webcam():
    import cv2
    import insightface
    from insightface.app import FaceAnalysis

    print("Opening webcam... Press 'q' to quit, 's' to snapshot & analyze.")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    fa = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
    fa.prepare(ctx_id=0, det_size=(640, 640))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Webcam Calibration (Press 's' to analyze, 'q' to quit)", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            faces = fa.get(frame)
            if not faces:
                print("No face detected.")
            else:
                for idx, face in enumerate(faces):
                    pitch, yaw, roll = face.pose
                    print(f"Detected: Score={face.det_score:.2f} | Yaw={yaw:+.1f}° | Pitch={pitch:+.1f}° | Roll={roll:+.1f}°")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate InsightFace pose angles.")
    parser.add_argument("--image", type=str, help="Path to image file to analyze")
    parser.add_argument("--webcam", action="store_true", help="Launch interactive webcam test")
    args = parser.parse_args()

    if args.image:
        calibrate_image(args.image)
    elif args.webcam:
        calibrate_webcam()
    else:
        parser.print_help()

