"""
Configuration loader.

All secrets (database location, the journal's login password hash, and the
JWT signing key) live in a single INI file that is kept OUTSIDE the Python
package and OUTSIDE version control:

    config/config.ini

This file is never baked into the Docker image — it is generated once with
scripts/generate_config.py and then mounted into the container at runtime
(see docker-compose.yml / README.md). Keeping it out of the image means the
secrets never end up in an image layer that could be pushed to a registry.

The password itself is never stored in plaintext — only its PBKDF2 hash
(see scripts/generate_config.py, which uses werkzeug.security). The JWT
secret is a random 64-byte value used to sign/verify tokens.

The config file path can be overridden with the APP_CONFIG_PATH environment
variable, which is useful for tests or alternate deployments.
"""

import configparser
import os
import stat
from pathlib import Path

# backend/ -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.ini"


class ConfigError(RuntimeError):
    """Raised when the config file is missing or malformed."""


class Config:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path(
            os.environ.get("APP_CONFIG_PATH", DEFAULT_CONFIG_PATH)
        )

        #if not self.path.exists():
        #    raise ConfigError(
        #        f"Config file not found at '{self.path}'.\n"
        #        "Generate one with:  python scripts/generate_config.py\n"
        #        "See README.md for details."
        #    )

        #self._warn_if_permissive()

        #parser = configparser.ConfigParser()
        #parser.read(self.path)
        #print(parser.sections())
        #try:
        #    db_section = parser["database"]
        #    auth_section = parser["auth"]
        #except KeyError as e:
        #    raise ConfigError(
        #        f"Config file '{self.path}' is missing required section {e}. "
        #        "Regenerate it with scripts/generate_config.py."
        #    ) from e

        # --- database ---
        self.db_path = "/app/data/journal.db" #b_section.get("path", fallback=str(_PROJECT_ROOT / "data" / "journal.db"))

        # --- auth ---
        self.password_hash = "pbkdf2:sha256:1000000$Xumq4KA0Wfe3Xl8D$d24fe49c03a8fe12c2cbde35fd75a406c96581eaac01f9985cb1abe28b642ef9" #auth_section.get("password_hash", fallback=None)
        self.jwt_secret = "d663e23b4640cdf9eeef20b71cccb100422d2c4a5c72dec9ccabb7a435d410180c60994efb17f4b8b4d26010553f476596e8b09199b9a46f68d5660e3d485138" #auth_section.get("jwt_secret", fallback=None)
        self.jwt_expiry_hours = 12 #auth_section.getint("jwt_expiry_hours", fallback=12)

        #if not self.password_hash or not self.jwt_secret:
        #    raise ConfigError(
        #        f"Config file '{self.path}' is missing 'password_hash' or 'jwt_secret' "
        #       # "under [auth]. Regenerate it with scripts/generate_config.py."
        #    )

    def _warn_if_permissive(self):
        """Best-effort check that the secrets file isn't world/group readable."""
        try:
            mode = stat.S_IMODE(os.stat(self.path).st_mode)
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                import warnings

                warnings.warn(
                    f"'{self.path}' is readable by group/other (mode {oct(mode)}). "
                    "Consider `chmod 600` on this file.",
                    stacklevel=2,
                )
        except OSError:
            pass


# Singleton, lazily created so importing this module doesn't explode at
# import time (e.g. during Sphinx/pytest collection with a patched path).
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
