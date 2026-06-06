"""Tests for CLI behavior."""

import logging

from subtitle_srt_translator.cli import _configure_logging


def test_default_logging_suppresses_http_library_info() -> None:
    """Default logging suppresses noisy httpx/OpenAI request INFO logs."""
    _configure_logging(verbose=False)

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("openai").getEffectiveLevel() >= logging.WARNING
