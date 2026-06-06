"""Shared data models for subtitle translation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class SubtitleCue:
    """A parsed subtitle cue from an SRT file."""

    index: int
    timing: str
    text_lines: tuple[str, ...]
    cue_id: str | None = None

    @property
    def text(self) -> str:
        """Return subtitle text as a single newline-delimited string."""
        return "\n".join(self.text_lines)


@dataclass(frozen=True)
class TranslationRequest:
    """Input sent to a translation backend for one overlapping chunk."""

    chunk_id: int
    cues: tuple[SubtitleCue, ...]
    source_languages: tuple[str, ...]
    target_language: str


@dataclass(frozen=True)
class TranslationCandidate:
    """A translated candidate for a cue returned from one chunk."""

    cue_index: int
    translated_lines: tuple[str, ...]
    chunk_id: int

    @property
    def text(self) -> str:
        """Return translated subtitle text as a single newline-delimited string."""
        return "\n".join(self.translated_lines)


class StructuredCueTranslation(BaseModel):
    """Structured model output for a single cue translation."""

    cue_index: int = Field(description="The exact cue index from the input chunk.")
    translated_lines: list[str] = Field(
        description="Translated subtitle text split into SRT text lines."
    )


class StructuredChunkTranslation(BaseModel):
    """Structured model output for a translated subtitle chunk."""

    translations: list[StructuredCueTranslation] = Field(
        description="One translation for every cue in the input chunk."
    )


class StructuredConflictResolution(BaseModel):
    """Structured model output for choosing a translation during conflict resolution."""

    cue_index: int = Field(description="The cue index whose translation was resolved.")
    chosen_translation: list[str] = Field(
        description="The best translated subtitle text split into SRT text lines."
    )
    rationale: str = Field(
        description="A concise reason for the choice, useful for debug logs."
    )


class SubtitleTranslator(Protocol):
    """Protocol implemented by subtitle translation backends."""

    async def translate_chunk(
        self, request: TranslationRequest
    ) -> list[TranslationCandidate]:
        """Translate a chunk of subtitle cues."""

    async def resolve_conflict(
        self,
        cue: SubtitleCue,
        context: tuple[SubtitleCue, ...],
        candidates: tuple[TranslationCandidate, ...],
        source_languages: tuple[str, ...],
        target_language: str,
    ) -> TranslationCandidate:
        """Choose the best translation for a cue from conflicting candidates."""
