"""Application factory."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request, send_from_directory
from urllib.parse import urlparse
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db, limiter


def create_app(config: type[Config] | None = None) -> Flask:
    cfg = config or Config
    cfg.validate()

    # ── Ensure instance dir exists ─────────────────────────────────────────
    instance_dir = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_dir, exist_ok=True)

    # ── Determine frontend dist path ───────────────────────────────────────
    frontend_dist = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    )
    has_dist = os.path.isfile(os.path.join(frontend_dist, "index.html"))

    app = Flask(
        __name__,
        instance_path=os.path.abspath(instance_dir),
        static_folder=None,
    )

    # ── Load config ────────────────────────────────────────────────────────
    app.config.from_object(cfg)

    # ── Proxy fix (ngrok / reverse proxy) ─────────────────────────────────
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    # ── Extensions ────────────────────────────────────────────────────────
    db.init_app(app)
    limiter.init_app(app)

    # ── CORS (dev only) ────────────────────────────────────────────────────
    if not cfg.IS_PRODUCTION:
        from flask_cors import CORS
        CORS(
            app,
            origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            supports_credentials=True,
        )

    # ── Database + tables ──────────────────────────────────────────────────
    with app.app_context():
        _configure_sqlite(app)
        from .models import user, otp, photo, pose_attempt  # noqa: F401  (register models)
        db.create_all()
        _migrate_photo_pose_columns(app)

    # ── Face service warm-up (loads model once) ────────────────────────────
    with app.app_context():
        from .services.face_service import get_face_service
        try:
            get_face_service()
            app.logger.info("InsightFace model loaded successfully.")
        except Exception as exc:  # pragma: no cover
            app.logger.warning("InsightFace model could not be loaded: %s", exc)

    # ── Blueprints ─────────────────────────────────────────────────────────
    from .api.auth import auth_bp
    from .api.photos import photos_bp
    from .api.errors import errors_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(photos_bp, url_prefix="/api/photos")
    app.register_blueprint(errors_bp)

    # ── CSRF / Origin check ────────────────────────────────────────────────
    @app.before_request
    def check_csrf_origin():
        if app.config.get("TESTING"):
            return None
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin") or request.headers.get("Referer")
            if not origin:
                if not cfg.IS_PRODUCTION:
                    return None
                return jsonify(ok=False, message="CSRF check failed: Missing Origin/Referer header.", code="CSRF_ERROR"), 403

            parsed = urlparse(origin)
            origin_base = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            parsed_pub = urlparse(cfg.PUBLIC_URL)
            pub_base = f"{parsed_pub.scheme}://{parsed_pub.netloc}".rstrip("/")

            if origin_base == pub_base:
                return None
            if not cfg.IS_PRODUCTION and parsed.hostname in ("localhost", "127.0.0.1"):
                return None

            return jsonify(
                ok=False,
                message=f"CSRF check failed: Origin '{origin_base}' does not match allowed origin.",
                code="CSRF_ERROR"
            ), 403

    # ── Security headers ───────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        app.logger.info("HTTP %s: %s", exc.code, exc.description)
        return jsonify(ok=False, message=exc.description, code=str(exc.code)), exc.code

    @app.errorhandler(413)
    def handle_too_large(_exc):
        return jsonify(ok=False, message="File too large (max 4 MB).", code="FILE_TOO_LARGE"), 413

    @app.errorhandler(429)
    def handle_rate_limit(exc):
        return jsonify(ok=False, message="Too many requests. Please slow down.", code="RATE_LIMITED"), 429

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        app.logger.exception("Unhandled exception: %s", exc)
        return jsonify(ok=False, message="An internal error occurred.", code="INTERNAL_ERROR"), 500

    # ── Health endpoint ────────────────────────────────────────────────────
    @app.get("/api/health")
    def health():
        return jsonify(ok=True, message="ok", env=cfg.APP_ENV)

    # ── Serve React SPA fallback or static assets ──────────────────────────
    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def serve_spa(path: str):
        if path.startswith("api/") or path == "api":
            return jsonify(ok=False, message="Resource not found.", code="NOT_FOUND"), 404

        full = os.path.join(frontend_dist, path)
        if path and os.path.isfile(full):
            return send_from_directory(frontend_dist, path)
        if os.path.isfile(os.path.join(frontend_dist, "index.html")):
            return send_from_directory(frontend_dist, "index.html")
        return jsonify(
            ok=False,
            message="Frontend dist not built. Run 'npm run build' or visit http://localhost:5173 in development.",
            code="DIST_NOT_BUILT"
        ), 404

    # ── Logging ────────────────────────────────────────────────────────────
    _configure_logging(app)

    return app


def _migrate_photo_pose_columns(app) -> None:
    """Add pose-ratio fields to databases created before ratio-based validation."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "photos" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("photos")}
    additions = {
        "yaw_ratio": "FLOAT",
        "pitch_ratio": "FLOAT",
        "pose_verified": "BOOLEAN NOT NULL DEFAULT 1",
    }
    with db.engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(
                    text(f"ALTER TABLE photos ADD COLUMN {column_name} {column_type}")
                )


def _configure_sqlite(app: Flask) -> None:
    """Enable WAL mode and foreign keys for every SQLite connection."""
    from sqlalchemy import event, text
    engine = db.engine

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )
    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.DEBUG if not app.config.get("IS_PRODUCTION") else logging.INFO)

    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.propagate = False
