"""Application configuration."""
from __future__ import annotations

import os
import secrets
from dotenv import load_dotenv

# Automatically load .env from project root if present
_this_dir = os.path.dirname(os.path.abspath(__file__))
for _candidate in [
    os.path.abspath(os.path.join(_this_dir, "..", "..", ".env")),
    os.path.abspath(os.path.join(_this_dir, "..", ".env")),
    os.path.abspath(".env"),
]:
    if os.path.isfile(_candidate):
        load_dotenv(_candidate)
        break


class Config:
    """Load and validate application configuration from environment variables."""

    # ── Required secrets ──────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    # ── Application environment ───────────────────────────────────────────
    APP_ENV: str = os.getenv("APP_ENV", "development")
    IS_PRODUCTION: bool = APP_ENV == "production"

    # ── Server ────────────────────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "5000"))
    PUBLIC_URL: str = os.getenv("PUBLIC_URL", "http://localhost:5000")

    # ── Database ──────────────────────────────────────────────────────────
    _base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    _instance_dir = os.path.join(_base_dir, "instance")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(_instance_dir, 'app.db')}",
    )
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "connect_args": {"check_same_thread": False},
    }
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── Email ─────────────────────────────────────────────────────────────
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    EMAIL_DOMAIN: str = os.getenv("EMAIL_DOMAIN", "iiitk.ac.in")

    # ── OTP ───────────────────────────────────────────────────────────────
    OTP_EXPIRY_MINUTES: int = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
    MAX_OTP_ATTEMPTS: int = int(os.getenv("MAX_OTP_ATTEMPTS", "8"))
    OTP_COOLDOWN_SECONDS: int = int(os.getenv("OTP_COOLDOWN_SECONDS", "60"))

    # ── Face analysis ─────────────────────────────────────────────────────
    INSIGHTFACE_MODEL: str = os.getenv("INSIGHTFACE_MODEL", "buffalo_s")
    FACE_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.30")
    )
    SAME_PERSON_THRESHOLD: float = float(os.getenv("SAME_PERSON_THRESHOLD", "0.35"))
    POSE_FRONT_YAW_MAX: float = float(os.getenv("POSE_FRONT_YAW_MAX", "0.15"))
    POSE_SIDE_YAW_MIN: float = float(os.getenv("POSE_SIDE_YAW_MIN", "0.18"))
    POSE_UP_PITCH_DELTA: float = float(os.getenv("POSE_UP_PITCH_DELTA", "0.06"))
    POSE_UP_YAW_MAX: float = float(os.getenv("POSE_UP_YAW_MAX", "0.25"))
    POSE_YAW_SIGN: int = int(os.getenv("YAW_SIGN", "1"))
    POSE_SIDE_FACE_CONFIDENCE: float = float(
        os.getenv("POSE_SIDE_FACE_CONFIDENCE", "0.70")
    )
    DEBUG_POSE: bool = os.getenv("DEBUG_POSE", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }

    # ── Storage ───────────────────────────────────────────────────────────
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    PHOTOS_DIR: str = os.path.abspath(
        os.path.join(_project_root, os.getenv("PHOTOS_DIR", "backend/photos"))
    )

    # ── File upload ───────────────────────────────────────────────────────
    MAX_CONTENT_LENGTH: int = 4 * 1024 * 1024  # 4 MB hard Flask limit

    # ── Session / Cookie ──────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME: int = 1800  # 30 min

    # ── Rate limiter storage ──────────────────────────────────────────────
    RATELIMIT_STORAGE_URI: str = "memory://"
    RATELIMIT_HEADERS_ENABLED: bool = True

    @classmethod
    def validate(cls) -> None:
        """Fail fast with clear errors if required configuration is missing."""
        errors: list[str] = []

        if not cls.SECRET_KEY:
            errors.append("SECRET_KEY is not set. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")
        elif len(cls.SECRET_KEY) < 16:
            errors.append("SECRET_KEY is too short (< 16 chars). Use a longer random value.")

        if cls.IS_PRODUCTION:
            if not cls.GMAIL_USER:
                errors.append("GMAIL_USER is required in production.")
            if not cls.GMAIL_APP_PASSWORD:
                errors.append("GMAIL_APP_PASSWORD is required in production.")
            if not cls.PUBLIC_URL:
                errors.append("PUBLIC_URL is required in production.")

        if cls.POSE_YAW_SIGN not in (-1, 1):
            errors.append("YAW_SIGN must be either 1 or -1.")
        if cls.POSE_FRONT_YAW_MAX <= 0 or cls.POSE_SIDE_YAW_MIN <= 0:
            errors.append("POSE_FRONT_YAW_MAX and POSE_SIDE_YAW_MIN must be positive.")
        if cls.POSE_UP_PITCH_DELTA <= 0 or cls.POSE_UP_YAW_MAX <= 0:
            errors.append("POSE_UP_PITCH_DELTA and POSE_UP_YAW_MAX must be positive.")
        if not 0 <= cls.POSE_SIDE_FACE_CONFIDENCE <= 1:
            errors.append("POSE_SIDE_FACE_CONFIDENCE must be between 0 and 1.")

        if errors:
            lines = "\n  ".join(errors)
            raise RuntimeError(
                f"Configuration errors — fix your .env file:\n  {lines}"
            )
