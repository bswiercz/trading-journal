"""
JWT authentication.

The journal has a single fixed password (no user accounts). Logging in
exchanges that password for a short-lived JWT, which the frontend then
sends as `Authorization: Bearer <token>` on every API call. Tokens are
signed with HS256 using the random secret from config.ini.
"""

import datetime
from functools import wraps

import jwt
from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash

ALGORITHM = "HS256"


def verify_password(password: str) -> bool:
    password_hash = current_app.config["PASSWORD_HASH"]
    if not password:
        return False
    return check_password_hash(password_hash, password)


def issue_token() -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expiry_hours = current_app.config["JWT_EXPIRY_HOURS"]
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(hours=expiry_hours)
    payload = {
        "sub": "journal-user",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm=ALGORITHM)
    return token, int(expiry_hours * 3600)


def _extract_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None


def jwt_required(fn):
    """Route decorator: rejects the request with 401 unless a valid,
    unexpired bearer token is present."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify(error="Missing bearer token"), 401
        try:
            jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify(error="Token expired"), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid token"), 401
        return fn(*args, **kwargs)

    return wrapper
