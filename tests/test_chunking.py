"""Tests for overlapping chunk planning."""

import pytest

from subtitle_srt_translator.chunking import build_overlapping_chunks
from subtitle_srt_translator.models import SubtitleCue


def test_build_overlapping_chunks_uses_expected_windows() -> None:
    """Chunks advance by chunk_size minus overlap."""
    cues = tuple(
        SubtitleCue(
            index=index,
            cue_id=None,
            timing="00:00:00,000 --> 00:00:01,000",
            text_lines=(str(index),),
        )
        for index in range(1, 17)
    )

    chunks = build_overlapping_chunks(cues, chunk_size=10, overlap=5)

    assert [[cue.index for cue in chunk] for chunk in chunks] == [
        list(range(1, 11)),
        list(range(6, 16)),
        list(range(11, 17)),
    ]


def test_build_overlapping_chunks_rejects_full_overlap() -> None:
    """Overlap must be smaller than chunk size."""
    with pytest.raises(ValueError, match="overlap must be smaller"):
        build_overlapping_chunks((), chunk_size=10, overlap=10)
