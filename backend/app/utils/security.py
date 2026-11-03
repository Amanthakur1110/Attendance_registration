"""Session / authentication helpers."""
from __future__ import annotations

import functools
from typing import Callable

from flask import session, current_app
from ..utils.responses import json_error


SESSION_ROLL_KEY = "verified_roll"
SESSION_CREATED_KEY = "session_created"


def get_session_roll() -> str | None:
    return session.get(SESSION_ROLL_KEY)


def set_session_roll(roll: str) -> None:
    session.permanent = True
    session[SESSION_ROLL_KEY] = roll


def clear_session() -> None:
    session.clear()


def login_required(fn: Callable) -> Callable:
    """Decorator: return 401 if there is no valid session."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not get_session_roll():
            return json_error("Authentication required. Please log in.", "UNAUTHORIZED", 401)
        return fn(*args, **kwargs)
    return wrapper

