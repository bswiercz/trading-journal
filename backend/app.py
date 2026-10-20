from pathlib import Path

from flask import Flask, send_from_directory

from backend.config import get_config
from backend.db import init_db

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def create_app(config_path=None) -> Flask:
    app = Flask(__name__, static_folder=None)

    cfg = get_config() if config_path is None else __import__(
        "backend.config", fromlist=["Config"]
    ).Config(config_path)

    app.config["DB_PATH"] = cfg.db_path
    app.config["PASSWORD_HASH"] = cfg.password_hash
    app.config["JWT_SECRET"] = cfg.jwt_secret
    app.config["JWT_EXPIRY_HOURS"] = cfg.jwt_expiry_hours
    # Flask's own secret key (session/flash cookies aren't used here, but
    # Flask expects one to be set; reuse the JWT secret rather than adding
    # a second value to manage).
    app.config["SECRET_KEY"] = cfg.jwt_secret

    init_db(app)

    from backend.routes.auth_routes import bp as auth_bp
    from backend.routes.trades_routes import bp as trades_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(trades_bp)

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def frontend_assets(filename):
        # Serves any additional static assets placed in frontend/dist
        # (the journal itself ships as a single self-contained index.html).
        full_path = FRONTEND_DIR / filename
        if full_path.is_file():
            return send_from_directory(FRONTEND_DIR, filename)
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.after_request
    def set_security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    return app
