"""Environment helpers for OpenAI API credentials."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_openai_api_key(project_root: Path | None = None) -> str:
    """Load OPENAI_API_KEY from the environment, `.env`, or `~/.env`."""
    existing = os.environ.get("OPENAI_API_KEY")
    if existing:
        logger.debug("Using OPENAI_API_KEY from process environment")
        return existing

    root = project_root or Path.cwd()
    for env_path in (root / ".env", Path.home() / ".env"):
        value = _read_key_from_env_file(env_path)
        if value:
            os.environ["OPENAI_API_KEY"] = value
            logger.debug("Loaded OPENAI_API_KEY from %s", env_path)
            return value

    message = "OPENAI_API_KEY was not found in the environment, .env, or ~/.env"
    logger.error(message)
    raise RuntimeError(message)


def _read_key_from_env_file(path: Path) -> str | None:
    """Read OPENAI_API_KEY from an env file without logging the secret."""
    if not path.exists():
        return None

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("Could not read env file %s: %s", path, exc)
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() != "OPENAI_API_KEY":
            continue
        cleaned = value.strip().strip('"').strip("'")
        if cleaned:
            return cleaned
    return None
