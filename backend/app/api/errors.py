"""Global error-handling blueprint."""
from flask import Blueprint, jsonify

errors_bp = Blueprint("errors", __name__)


@errors_bp.app_errorhandler(404)
def not_found(_exc):
    return jsonify(ok=False, message="Resource not found.", code="NOT_FOUND"), 404


@errors_bp.app_errorhandler(405)
def method_not_allowed(_exc):
    return jsonify(ok=False, message="Method not allowed.", code="METHOD_NOT_ALLOWED"), 405

