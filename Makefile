# Face Registration — Project Makefile
# Usage: make <target>
# Requires: Python 3.10+, Node 18+, pip, npm

.PHONY: install dev-backend dev-frontend test build serve clean

## Install all dependencies (Python + Node)
install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

## Install and pre-download InsightFace models
install-models:
	python backend/scripts/download_models.py --model buffalo_s

## Run Flask backend in development mode
dev-backend:
	python backend/run.py

## Run Vite dev server (proxies /api -> Flask)
dev-frontend:
	cd frontend && npm run dev

## Run pytest
test:
	cd backend && python -m pytest tests/ -v

## Build frontend for production
build:
	cd frontend && npm run build

## Production: build frontend + serve everything with waitress
serve: build
	cd backend && python -c "\
import os; os.chdir('..'); \
from dotenv import load_dotenv; load_dotenv('.env'); \
from waitress import serve as waitress_serve; \
from backend.wsgi import application; \
host = os.getenv('HOST', '127.0.0.1'); \
port = int(os.getenv('PORT', 5000)); \
print(f'Serving on http://{host}:{port}'); \
waitress_serve(application, host=host, port=port, threads=4)"

## Clean build artifacts
clean:
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	find backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
	find backend -name '*.pyc' -delete 2>/dev/null; true

