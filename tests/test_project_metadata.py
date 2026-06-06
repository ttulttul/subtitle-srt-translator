"""Tests for packaging and compatibility metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_supported_python_range() -> None:
    """Project metadata advertises Python 3.11 through 3.15 support."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["requires-python"] == ">=3.11,<3.16"


def test_uv_build_backend_avoids_hidden_editable_pth() -> None:
    """The uv build backend emits module-named editable pth files."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["build-system"]["build-backend"] == "uv_build"
    assert pyproject["tool"]["uv"]["build-backend"]["module-name"] == (
        "subtitle_srt_translator"
    )
