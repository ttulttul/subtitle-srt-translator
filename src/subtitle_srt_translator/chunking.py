"""Build overlapping subtitle chunks."""

from __future__ import annotations

import logging

from subtitle_srt_translator.models import SubtitleCue

logger = logging.getLogger(__name__)


def build_overlapping_chunks(
    cues: tuple[SubtitleCue, ...], chunk_size: int, overlap: int
) -> tuple[tuple[SubtitleCue, ...], ...]:
    """Split cues into overlapping chunks."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if not cues:
        return ()

    chunks: list[tuple[SubtitleCue, ...]] = []
    step = chunk_size - overlap
    start = 0
    while start < len(cues):
        chunks.append(cues[start : start + chunk_size])
        if start + chunk_size >= len(cues):
            break
        start += step

    logger.info(
        "Built %d chunks from %d cues with chunk_size=%d overlap=%d",
        len(chunks),
        len(cues),
        chunk_size,
        overlap,
    )
    return tuple(chunks)
