"""Shared pytest fixtures and app setup."""
from __future__ import annotations

import os
import sys
import pytest

# Make the backend package importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile

# Set required env vars before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-long-enough")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("GMAIL_USER", "test@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "testpassword")
os.environ.setdefault("EMAIL_DOMAIN", "iiitk.ac.in")
os.environ.setdefault("OTP_EXPIRY_MINUTES", "5")
os.environ.setdefault("MAX_OTP_ATTEMPTS", "5")
os.environ.setdefault("OTP_COOLDOWN_SECONDS", "60")
os.environ.setdefault("FACE_CONFIDENCE_THRESHOLD", "0.70")
os.environ.setdefault("SAME_PERSON_THRESHOLD", "0.35")
os.environ.setdefault("INSIGHTFACE_MODEL", "buffalo_s")
os.environ.setdefault("PHOTOS_DIR", os.path.join(tempfile.gettempdir(), "test_photos"))


@pytest.fixture(scope="session")
def app():
    """Create a Flask app configured for testing."""
    # Patch face service to avoid loading insightface during tests
    from unittest.mock import MagicMock, patch

    mock_fa = MagicMock()
    mock_fa.get.return_value = []

    with patch("app.services.face_service._load_model", return_value=mock_fa):
        from app import create_app
        from app.config import Config
        from sqlalchemy.pool import StaticPool

        Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
        Config.SECRET_KEY = "test-secret-key-long-enough"
        Config.PHOTOS_DIR = os.path.join(tempfile.gettempdir(), "test_photos")
        Config.TESTING = True

        application = create_app(Config)
        application.config["TESTING"] = True
        application.config["WTF_CSRF_ENABLED"] = False

    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    from app.extensions import db as _db
    with app.app_context():
        _db.create_all()
        yield _db.session
        _db.session.remove()
        _db.drop_all()

