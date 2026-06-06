"""Tests for the OpenAI subtitle translator wrapper."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from subtitle_srt_translator.models import (
    StructuredChunkTranslation,
    StructuredCueTranslation,
    SubtitleCue,
    TranslationRequest,
)
from subtitle_srt_translator.openai_client import OpenAISubtitleTranslator


@dataclass
class FakeParsedResponse:
    """Small response object that mimics the SDK parsed response shape."""

    output_parsed: StructuredChunkTranslation


class FakeResponses:
    """Fake Responses API surface."""

    def __init__(self) -> None:
        """Initialize call tracking."""
        self.calls = 0
        self.seen_inputs: list[Any] = []

    async def parse(self, **kwargs: Any) -> FakeParsedResponse:
        """Return a deterministic parsed translation."""
        self.calls += 1
        self.seen_inputs.append(kwargs["input"])
        return FakeParsedResponse(
            output_parsed=StructuredChunkTranslation(
                translations=[
                    StructuredCueTranslation(
                        cue_index=1,
                        translated_lines=["Hello"],
                    )
                ]
            )
        )


class FakeClient:
    """Fake OpenAI client with a Responses API surface."""

    def __init__(self) -> None:
        """Initialize the fake responses resource."""
        self.responses = FakeResponses()


def test_translate_chunk_uses_cache_for_identical_prompt(tmp_path: Path) -> None:
    """The second identical chunk translation avoids another Responses API call."""
    asyncio.run(_run_cache_hit_test(tmp_path))


async def _run_cache_hit_test(tmp_path: Path) -> None:
    """Run the async cache hit assertion."""
    client = FakeClient()
    translator = OpenAISubtitleTranslator(
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        client=client,  # type: ignore[arg-type]
        cache_dir=tmp_path,
    )
    request = TranslationRequest(
        chunk_id=1,
        cues=(
            SubtitleCue(
                index=1,
                cue_id=None,
                timing="00:00:00,000 --> 00:00:01,000",
                text_lines=("שלום",),
            ),
        ),
        source_languages=("Hebrew",),
        target_language="English",
    )

    first = await translator.translate_chunk(request)
    second = await translator.translate_chunk(request)

    assert client.responses.calls == 1
    assert first == second
    assert first[0].translated_lines == ("Hello",)


def test_translate_chunk_can_disable_cache(tmp_path: Path) -> None:
    """Disabling the cache keeps every call live."""
    asyncio.run(_run_cache_disabled_test(tmp_path))


async def _run_cache_disabled_test(tmp_path: Path) -> None:
    """Run the async cache disabled assertion."""
    client = FakeClient()
    translator = OpenAISubtitleTranslator(
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        client=client,  # type: ignore[arg-type]
        cache_dir=tmp_path,
        cache_enabled=False,
    )
    request = TranslationRequest(
        chunk_id=1,
        cues=(
            SubtitleCue(
                index=1,
                cue_id=None,
                timing="00:00:00,000 --> 00:00:01,000",
                text_lines=("שלום",),
            ),
        ),
        source_languages=("Hebrew",),
        target_language="English",
    )

    await translator.translate_chunk(request)
    await translator.translate_chunk(request)

    assert client.responses.calls == 2
