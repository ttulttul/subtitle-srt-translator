"""Parse and render SRT subtitle files."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from subtitle_srt_translator.models import SubtitleCue

logger = logging.getLogger(__name__)

TIMING_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}(?:\s+.*)?$"
)


def read_srt(path: Path) -> tuple[SubtitleCue, ...]:
    """Read and parse an SRT file from disk."""
    logger.info("Reading SRT file from %s", path)
    text = path.read_text(encoding="utf-8-sig")
    return parse_srt(text)


def parse_srt(text: str) -> tuple[SubtitleCue, ...]:
    """Parse SRT text into subtitle cues.

    Standard SRT cue IDs are preserved when present. Files that omit numeric cue
    IDs and start each block with a timing line are also supported.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        logger.warning("Received empty SRT content")
        return ()

    cues: list[SubtitleCue] = []
    blocks = re.split(r"\n{2,}", normalized)
    for fallback_index, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        cue = _parse_block(lines, fallback_index)
        cues.append(cue)

    logger.info("Parsed %d subtitle cues", len(cues))
    return tuple(cues)


def render_srt(cues: tuple[SubtitleCue, ...]) -> str:
    """Render subtitle cues back to SRT text."""
    blocks: list[str] = []
    for cue in cues:
        block_lines: list[str] = []
        if cue.cue_id is not None:
            block_lines.append(cue.cue_id)
        block_lines.append(cue.timing)
        block_lines.extend(cue.text_lines)
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks) + "\n"


def replace_cue_text(
    cues: tuple[SubtitleCue, ...], translations: dict[int, tuple[str, ...]]
) -> tuple[SubtitleCue, ...]:
    """Return cues with translated text substituted by cue index."""
    rendered: list[SubtitleCue] = []
    for cue in cues:
        rendered.append(
            SubtitleCue(
                index=cue.index,
                cue_id=cue.cue_id,
                timing=cue.timing,
                text_lines=translations[cue.index],
            )
        )
    return tuple(rendered)


def _parse_block(lines: list[str], fallback_index: int) -> SubtitleCue:
    """Parse a single SRT block into a cue."""
    if not lines:
        raise ValueError("SRT block cannot be empty")

    cue_id: str | None = None
    timing_line_index = 0
    if not TIMING_RE.match(lines[0]):
        cue_id = lines[0]
        timing_line_index = 1

    if timing_line_index >= len(lines) or not TIMING_RE.match(lines[timing_line_index]):
        message = f"Invalid SRT block near cue {fallback_index}: missing timing line"
        logger.error(message)
        raise ValueError(message)

    text_lines = tuple(lines[timing_line_index + 1 :])
    if not text_lines:
        logger.warning("Cue %d has no subtitle text", fallback_index)

    parsed_index = fallback_index
    if cue_id is not None and cue_id.isdigit():
        parsed_index = int(cue_id)

    return SubtitleCue(
        index=parsed_index,
        cue_id=cue_id,
        timing=lines[timing_line_index],
        text_lines=text_lines,
    )
