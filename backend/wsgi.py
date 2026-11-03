"""WSGI entry point for production (waitress / gunicorn)."""
import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Load .env relative to the project root (one level above backend/)
_root = os.path.abspath(os.path.join(_backend_dir, ".."))
load_dotenv(os.path.join(_root, ".env"))

from app import create_app  # noqa: E402

application = create_app()
app = application  # gunicorn expects 'application' or a named export

if __name__ == "__main__":
    from waitress import serve
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    print(f"Serving production app with Waitress on http://{host}:{port}")
    serve(application, host=host, port=port, threads=4)


