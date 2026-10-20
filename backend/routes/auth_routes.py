from flask import Blueprint, current_app, jsonify, request

from backend.auth import issue_token, jwt_required, verify_password

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Very small in-memory brute-force throttle. Fine for a single-password,
# single-instance app; swap for Flask-Limiter/Redis if you scale this out.
_failed_attempts = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def _throttled(key: str) -> bool:
    import time

    now = time.time()
    attempts = [t for t in _failed_attempts.get(key, []) if now - t < WINDOW_SECONDS]
    _failed_attempts[key] = attempts
    return len(attempts) >= MAX_ATTEMPTS


def _record_failure(key: str):
    import time

    _failed_attempts.setdefault(key, []).append(time.time())


@bp.post("/login")
def login():
    ip = request.remote_addr or "unknown"
    if _throttled(ip):
        return jsonify(error="Too many attempts. Try again in a minute."), 429

    body = request.get_json(silent=True) or {}
    password = body.get("password", "")

    if not verify_password(password):
        _record_failure(ip)
        return jsonify(error="Incorrect password"), 401

    token, expires_in = issue_token()
    return jsonify(access_token=token, expires_in=expires_in)


@bp.get("/verify")
@jwt_required
def verify():
    """Lets the frontend check on load whether a stored token is still valid."""
    return jsonify(valid=True)
