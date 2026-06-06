"""Subtitle translation orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from subtitle_srt_translator.chunking import build_overlapping_chunks
from subtitle_srt_translator.models import (
    SubtitleCue,
    SubtitleTranslator,
    TranslationCandidate,
    TranslationRequest,
)

logger = logging.getLogger(__name__)


async def translate_subtitles(
    cues: tuple[SubtitleCue, ...],
    translator: SubtitleTranslator,
    *,
    source_languages: tuple[str, ...],
    target_language: str,
    chunk_size: int = 10,
    overlap: int = 5,
    parallelism: int = 4,
    context_radius: int = 2,
) -> dict[int, tuple[str, ...]]:
    """Translate subtitle cues in overlapping chunks and resolve conflicts."""
    if parallelism < 1:
        raise ValueError("parallelism must be at least 1")

    chunks = build_overlapping_chunks(cues, chunk_size, overlap)
    semaphore = asyncio.Semaphore(parallelism)

    async def run_chunk(
        chunk_id: int, chunk: tuple[SubtitleCue, ...]
    ) -> list[TranslationCandidate]:
        async with semaphore:
            request = TranslationRequest(
                chunk_id=chunk_id,
                cues=chunk,
                source_languages=source_languages,
                target_language=target_language,
            )
            return await translator.translate_chunk(request)

    chunk_results = await asyncio.gather(
        *(run_chunk(chunk_id, chunk) for chunk_id, chunk in enumerate(chunks, start=1))
    )
    candidates = _group_candidates(chunk_results)
    _validate_translation_coverage(cues, candidates)
    return await _choose_translations(
        cues,
        candidates,
        translator,
        source_languages=source_languages,
        target_language=target_language,
        context_radius=context_radius,
        parallelism=parallelism,
    )


def _group_candidates(
    chunk_results: list[list[TranslationCandidate]],
) -> dict[int, tuple[TranslationCandidate, ...]]:
    """Group chunk translation candidates by cue index."""
    grouped: dict[int, list[TranslationCandidate]] = defaultdict(list)
    for chunk_result in chunk_results:
        for candidate in chunk_result:
            grouped[candidate.cue_index].append(candidate)
    return {cue_index: tuple(items) for cue_index, items in grouped.items()}


def _validate_translation_coverage(
    cues: tuple[SubtitleCue, ...],
    candidates: dict[int, tuple[TranslationCandidate, ...]],
) -> None:
    """Ensure every cue received at least one translation candidate."""
    missing = [cue.index for cue in cues if cue.index not in candidates]
    if missing:
        message = f"Missing translations for cue indexes: {missing}"
        logger.error(message)
        raise RuntimeError(message)


async def _choose_translations(
    cues: tuple[SubtitleCue, ...],
    candidates: dict[int, tuple[TranslationCandidate, ...]],
    translator: SubtitleTranslator,
    *,
    source_languages: tuple[str, ...],
    target_language: str,
    context_radius: int,
    parallelism: int,
) -> dict[int, tuple[str, ...]]:
    """Choose final translations, resolving disagreements with the model."""
    cue_by_index = {cue.index: cue for cue in cues}
    exact: dict[int, tuple[str, ...]] = {}
    conflicts: list[int] = []

    for cue in cues:
        cue_candidates = candidates[cue.index]
        unique = {candidate.translated_lines for candidate in cue_candidates}
        if len(unique) == 1:
            exact[cue.index] = cue_candidates[0].translated_lines
        else:
            conflicts.append(cue.index)

    if not conflicts:
        logger.info("No overlapping translation conflicts found")
        return exact

    logger.info("Resolving %d overlapping translation conflicts", len(conflicts))
    semaphore = asyncio.Semaphore(parallelism)

    async def resolve(cue_index: int) -> TranslationCandidate:
        async with semaphore:
            cue = cue_by_index[cue_index]
            context = _context_for(cues, cue_index, context_radius)
            return await translator.resolve_conflict(
                cue,
                context,
                candidates[cue_index],
                source_languages,
                target_language,
            )

    resolved = await asyncio.gather(*(resolve(cue_index) for cue_index in conflicts))
    for candidate in resolved:
        exact[candidate.cue_index] = candidate.translated_lines

    return exact


def _context_for(
    cues: tuple[SubtitleCue, ...], cue_index: int, context_radius: int
) -> tuple[SubtitleCue, ...]:
    """Return nearby cues around a target cue index."""
    position = next(index for index, cue in enumerate(cues) if cue.index == cue_index)
    start = max(0, position - context_radius)
    end = min(len(cues), position + context_radius + 1)
    return cues[start:end]
