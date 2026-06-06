"""Tests for translation orchestration."""

from __future__ import annotations

import asyncio

from subtitle_srt_translator.models import (
    SubtitleCue,
    TranslationCandidate,
    TranslationRequest,
)
from subtitle_srt_translator.pipeline import translate_subtitles


class FakeTranslator:
    """Fake translator used to test chunk merging behavior."""

    def __init__(self) -> None:
        """Initialize recorded calls."""
        self.resolved: list[int] = []

    async def translate_chunk(
        self, request: TranslationRequest
    ) -> list[TranslationCandidate]:
        """Return deterministic translations with one deliberate overlap conflict."""
        candidates: list[TranslationCandidate] = []
        for cue in request.cues:
            text = f"translated {cue.index}"
            if cue.index == 6 and request.chunk_id == 2:
                text = "better translated 6"
            candidates.append(
                TranslationCandidate(
                    cue_index=cue.index,
                    translated_lines=(text,),
                    chunk_id=request.chunk_id,
                )
            )
        return candidates

    async def resolve_conflict(
        self,
        cue: SubtitleCue,
        context: tuple[SubtitleCue, ...],
        candidates: tuple[TranslationCandidate, ...],
        source_languages: tuple[str, ...],
        target_language: str,
    ) -> TranslationCandidate:
        """Choose the second candidate for the deliberate conflict."""
        self.resolved.append(cue.index)
        assert [item.index for item in context] == [4, 5, 6, 7, 8]
        return candidates[1]


def test_translate_subtitles_resolves_only_disagreements() -> None:
    """Overlapping exact matches are accepted and disagreements are resolved."""
    asyncio.run(_run_translation_test())


async def _run_translation_test() -> None:
    """Run the async pipeline assertion."""
    cues = tuple(
        SubtitleCue(
            index=index,
            cue_id=None,
            timing="00:00:00,000 --> 00:00:01,000",
            text_lines=(str(index),),
        )
        for index in range(1, 12)
    )
    translator = FakeTranslator()

    translations = await translate_subtitles(
        cues,
        translator,
        source_languages=("Hebrew", "Arabic"),
        target_language="English",
        chunk_size=10,
        overlap=5,
        parallelism=2,
    )

    assert translator.resolved == [6]
    assert translations[6] == ("better translated 6",)
    assert translations[1] == ("translated 1",)
