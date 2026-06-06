"""Tests for CLI behavior."""

import logging

from subtitle_srt_translator.cli import _configure_logging, _log_level


def test_default_logging_suppresses_http_library_info() -> None:
    """Default logging suppresses noisy httpx/OpenAI request INFO logs."""
    _configure_logging(verbose=False)

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("openai").getEffectiveLevel() >= logging.WARNING


def test_progress_logging_suppresses_noncritical_output() -> None:
    """Progress mode suppresses normal logging unless verbose is also enabled."""
    assert _log_level(verbose=False, progress=True) == logging.CRITICAL
    assert _log_level(verbose=True, progress=True) == logging.DEBUG
