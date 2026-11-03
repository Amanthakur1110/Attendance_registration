"""
Download InsightFace models before first run.

Usage:
    python backend/scripts/download_models.py [--model buffalo_s]

The model is stored in ~/.insightface/models/<model_name>/ by default.
InsightFace also auto-downloads on first inference if the model is missing,
but running this script first avoids delay during the web request.
"""
from __future__ import annotations

import argparse
import sys


def download(model_name: str) -> None:
    print(f"Downloading InsightFace model: {model_name} ...")
    try:
        import insightface
        from insightface.app import FaceAnalysis

        fa = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        fa.prepare(ctx_id=0, det_size=(640, 640))
        print(f"Model '{model_name}' is ready.")
    except ImportError:
        print(
            "ERROR: insightface is not installed.\n"
            "Run: pip install -r backend/requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-download InsightFace models.")
    parser.add_argument("--model", default="buffalo_s", help="Model name (buffalo_s or buffalo_l)")
    args = parser.parse_args()
    download(args.model)

