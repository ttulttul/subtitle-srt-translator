"""Subtitle translation orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Protocol

from subtitle_srt_translator.chunking import build_overlapping_chunks
from subtitle_srt_translator.models import (
    SubtitleCue,
    SubtitleTranslator,
    TranslationCandidate,
    TranslationRequest,
)

logger = logging.getLogger(__name__)


class TranslationProgress(Protocol):
    """Progress sink for translation chunk lifecycle events."""

    def initialize(self, total_chunks: int) -> None:
        """Initialize progress tracking for a translation job."""

    def chunk_started(self, chunk_id: int) -> None:
        """Mark a chunk as processing."""

    def chunk_completed(self, chunk_id: int) -> None:
        """Mark a chunk as fully translated."""

    def chunk_conflicted(self, chunk_id: int) -> None:
        """Mark a chunk as having an unresolved disagreement."""


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
    progress: TranslationProgress | None = None,
) -> dict[int, tuple[str, ...]]:
    """Translate subtitle cues in overlapping chunks and resolve conflicts."""
    if parallelism < 1:
        raise ValueError("parallelism must be at least 1")

    chunks = build_overlapping_chunks(cues, chunk_size, overlap)
    if progress is not None:
        progress.initialize(len(chunks))
    semaphore = asyncio.Semaphore(parallelism)
    cue_to_chunk_ids = _map_cues_to_chunks(chunks)
    candidates_so_far: dict[int, list[TranslationCandidate]] = defaultdict(list)
    conflicted_cues: set[int] = set()

    async def run_chunk(
        chunk_id: int, chunk: tuple[SubtitleCue, ...]
    ) -> tuple[int, list[TranslationCandidate]]:
        async with semaphore:
            if progress is not None:
                progress.chunk_started(chunk_id)
            request = TranslationRequest(
                chunk_id=chunk_id,
                cues=chunk,
                source_languages=source_languages,
                target_language=target_language,
            )
            candidates = await translator.translate_chunk(request)
            return chunk_id, candidates

    tasks = [
        asyncio.create_task(run_chunk(chunk_id, chunk))
        for chunk_id, chunk in enumerate(chunks, start=1)
    ]
    chunk_results_by_id: dict[int, list[TranslationCandidate]] = {}
    for completed_task in asyncio.as_completed(tasks):
        chunk_id, candidates = await completed_task
        chunk_results_by_id[chunk_id] = candidates
        if progress is not None:
            progress.chunk_completed(chunk_id)
        new_conflicts = _record_candidates(candidates, candidates_so_far)
        conflicted_cues.update(new_conflicts)
        if progress is not None:
            for cue_index in new_conflicts:
                for conflict_chunk_id in cue_to_chunk_ids[cue_index]:
                    progress.chunk_conflicted(conflict_chunk_id)

    chunk_results = [
        chunk_results_by_id[chunk_id] for chunk_id in range(1, len(chunks) + 1)
    ]
    candidates = _group_candidates(chunk_results)
    _validate_translation_coverage(cues, candidates)
    translations = await _choose_translations(
        cues,
        candidates,
        translator,
        source_languages=source_languages,
        target_language=target_language,
        context_radius=context_radius,
        parallelism=parallelism,
    )
    if progress is not None and conflicted_cues:
        for chunk_id in range(1, len(chunks) + 1):
            progress.chunk_completed(chunk_id)
    return translations


def _map_cues_to_chunks(
    chunks: tuple[tuple[SubtitleCue, ...], ...],
) -> dict[int, set[int]]:
    """Map cue indexes to the chunks that contain them."""
    cue_to_chunk_ids: dict[int, set[int]] = defaultdict(set)
    for chunk_id, chunk in enumerate(chunks, start=1):
        for cue in chunk:
            cue_to_chunk_ids[cue.index].add(chunk_id)
    return cue_to_chunk_ids


def _record_candidates(
    candidates: list[TranslationCandidate],
    candidates_so_far: dict[int, list[TranslationCandidate]],
) -> set[int]:
    """Record candidates and return cue indexes with new disagreements."""
    conflicts: set[int] = set()
    for candidate in candidates:
        existing = candidates_so_far[candidate.cue_index]
        if any(
            item.translated_lines != candidate.translated_lines for item in existing
        ):
            conflicts.add(candidate.cue_index)
        existing.append(candidate)
    return conflicts


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
