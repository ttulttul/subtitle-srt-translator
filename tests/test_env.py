"""Tests for environment credential loading."""

import os
from pathlib import Path

from subtitle_srt_translator.env import load_openai_api_key


def test_load_openai_api_key_from_project_env(
    tmp_path: Path, monkeypatch
) -> None:
    """Project .env is used when the process environment has no key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY='test-key'\n", encoding="utf-8")

    value = load_openai_api_key(tmp_path)

    assert value == "test-key"
    assert os.environ["OPENAI_API_KEY"] == "test-key"
