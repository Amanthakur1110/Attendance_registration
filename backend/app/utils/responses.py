"""JSON response helpers."""
from __future__ import annotations

from flask import jsonify
from werkzeug.wrappers import Response


def json_ok(message: str = "ok", code: str = "OK", status: int = 200, **kwargs) -> tuple[Response, int]:
    payload: dict = {"ok": True, "message": message, "code": code, **kwargs}
    return jsonify(payload), status


def json_error(message: str, code: str = "ERROR", status: int = 400, **kwargs) -> tuple[Response, int]:
    payload: dict = {"ok": False, "message": message, "code": code, **kwargs}
    return jsonify(payload), status

