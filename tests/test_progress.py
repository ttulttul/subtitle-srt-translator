"""Tests for terminal progress rendering."""

from __future__ import annotations

from io import StringIO

from subtitle_srt_translator.progress import ChunkProgressBar


def test_progress_bar_renders_chunk_statuses() -> None:
    """Progress output reflects chunk lifecycle status characters."""
    stream = StringIO()
    progress = ChunkProgressBar(stream=stream, terminal_width=80)

    progress.initialize(4)
    progress.chunk_started(2)
    progress.chunk_conflicted(3)
    progress.chunk_completed(1)
    progress.finish()

    assert "\r[----]" in stream.getvalue()
    assert "\r[-o--]" in stream.getvalue()
    assert "\r[-o?-]" in stream.getvalue()
    assert "\r[+o?-]" in stream.getvalue()
    assert stream.getvalue().endswith("\n")


def test_progress_bar_compacts_to_terminal_width() -> None:
    """Progress output aggregates many chunks into the available bar width."""
    stream = StringIO()
    progress = ChunkProgressBar(stream=stream, terminal_width=6)

    progress.initialize(8)
    progress.chunk_completed(1)
    progress.chunk_started(3)
    progress.chunk_conflicted(5)

    last_render = stream.getvalue().split("\r")[-1]
    assert last_render == "[-o?-]"
    assert len(last_render) == 6
