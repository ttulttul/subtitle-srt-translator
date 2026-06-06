"""Terminal progress rendering for subtitle translation."""

from __future__ import annotations

import shutil
import sys
from typing import TextIO


class ChunkProgressBar:
    """Render chunk status as a single terminal-width progress bar."""

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        terminal_width: int | None = None,
    ) -> None:
        """Initialize the progress bar."""
        self.stream = stream or sys.stderr
        self.terminal_width = terminal_width
        self.statuses: list[str] = []
        self._started = False

    def initialize(self, total_chunks: int) -> None:
        """Initialize progress tracking for a translation job."""
        self.statuses = ["-"] * total_chunks
        self._started = True
        self.render()

    def chunk_started(self, chunk_id: int) -> None:
        """Mark a chunk as processing."""
        self._set_status(chunk_id, "o")

    def chunk_completed(self, chunk_id: int) -> None:
        """Mark a chunk as fully translated."""
        self._set_status(chunk_id, "+")

    def chunk_conflicted(self, chunk_id: int) -> None:
        """Mark a chunk as having an unresolved disagreement."""
        self._set_status(chunk_id, "?")

    def finish(self) -> None:
        """Finish rendering the progress bar."""
        if self._started:
            self.stream.write("\n")
            self.stream.flush()
            self._started = False

    def render(self) -> None:
        """Render the current progress state."""
        self.stream.write(f"\r[{self._display_statuses()}]")
        self.stream.flush()

    def _set_status(self, chunk_id: int, status: str) -> None:
        """Set status for a 1-based chunk id and render."""
        if not self.statuses:
            return
        self.statuses[chunk_id - 1] = status
        self.render()

    def _display_statuses(self) -> str:
        """Return status characters capped to the terminal width."""
        body_width = max(1, self._bar_width() - 2)
        if len(self.statuses) <= body_width:
            return "".join(self.statuses)
        return "".join(
            _aggregate_status(self.statuses[start:end])
            for start, end in _bucket_ranges(len(self.statuses), body_width)
        )

    def _bar_width(self) -> int:
        """Return terminal width, defaulting to 80 columns."""
        if self.terminal_width is not None:
            return self.terminal_width
        return shutil.get_terminal_size(fallback=(80, 20)).columns


def _bucket_ranges(total_items: int, total_buckets: int) -> list[tuple[int, int]]:
    """Return proportional half-open bucket ranges."""
    ranges: list[tuple[int, int]] = []
    for bucket in range(total_buckets):
        start = bucket * total_items // total_buckets
        end = (bucket + 1) * total_items // total_buckets
        ranges.append((start, end))
    return ranges


def _aggregate_status(statuses: list[str]) -> str:
    """Aggregate multiple chunk states into one display character."""
    for status in ("?", "o", "-", "+"):
        if status in statuses:
            return status
    return "-"
