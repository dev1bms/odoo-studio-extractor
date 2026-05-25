"""Configuration loading for odoo-studio-extractor.

Configuration is read from environment variables only. Optionally, if
``python-dotenv`` is installed, a ``.env`` file in the current working
directory is loaded automatically.

No secret value is ever printed by this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable


REQUIRED_VARS: tuple[str, ...] = (
    "ODOO_URL",
    "ODOO_DB",
    "ODOO_USERNAME",
    "ODOO_PASSWORD",
)


class ConfigError(RuntimeError):
    """Raised when the configuration is missing or invalid."""


@dataclass(frozen=True)
class OdooConfig:
    """Connection settings for an Odoo instance.

    All fields are required. ``password`` is intentionally not included in
    ``__repr__`` to avoid accidental logging.
    """

    url: str
    db: str
    username: str
    password: str = field(repr=False)

    def safe_summary(self) -> dict[str, str]:
        """Return a representation suitable for logging (no secrets)."""
        return {
            "url": self.url,
            "db": self.db,
            "username": self.username,
            "password": "***",
        }


def _try_load_dotenv() -> None:
    """Best-effort load of a local ``.env`` file if python-dotenv is present."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except Exception:
        return
    try:
        load_dotenv()
    except Exception:
        # Never fail config loading because of dotenv issues.
        return


def load_config(
    env: dict[str, str] | None = None,
    *,
    required: Iterable[str] = REQUIRED_VARS,
    use_dotenv: bool = True,
) -> OdooConfig:
    """Load and validate Odoo configuration from environment variables.

    Parameters
    ----------
    env:
        Optional mapping to read from instead of ``os.environ``. Useful for
        testing.
    required:
        Iterable of required variable names.
    use_dotenv:
        If ``True``, attempt to load a local ``.env`` file via
        ``python-dotenv`` (only when ``env`` is ``None``).
    """
    if env is None:
        if use_dotenv:
            _try_load_dotenv()
        env = dict(os.environ)

    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(sorted(missing))
            + ". See .env.example for the expected variables."
        )

    url = env["ODOO_URL"].strip().rstrip("/")
    db = env["ODOO_DB"].strip()
    username = env["ODOO_USERNAME"].strip()
    password = env["ODOO_PASSWORD"]

    if not url.startswith(("http://", "https://")):
        raise ConfigError(
            "ODOO_URL must start with 'http://' or 'https://'."
        )

    return OdooConfig(url=url, db=db, username=username, password=password)
