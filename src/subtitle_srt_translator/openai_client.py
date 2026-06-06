"""OpenAI Responses API client for subtitle translation."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from subtitle_srt_translator.models import (
    StructuredChunkTranslation,
    StructuredConflictResolution,
    SubtitleCue,
    TranslationCandidate,
    TranslationRequest,
)

logger = logging.getLogger(__name__)


class OpenAISubtitleTranslator:
    """Translate subtitle chunks with the OpenAI Responses API."""

    def __init__(
        self,
        *,
        model: str,
        reasoning_effort: str,
        client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize the translator."""
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.client = client or AsyncOpenAI()

    async def translate_chunk(
        self, request: TranslationRequest
    ) -> list[TranslationCandidate]:
        """Translate a chunk of subtitle cues."""
        logger.info(
            "Translating chunk %d with %d cues", request.chunk_id, len(request.cues)
        )
        response = await self.client.responses.parse(
            model=self.model,
            reasoning={"effort": self.reasoning_effort},
            input=[
                {"role": "system", "content": _translation_system_prompt()},
                {
                    "role": "user",
                    "content": _translation_user_prompt(
                        request.cues,
                        request.source_languages,
                        request.target_language,
                    ),
                },
            ],
            text_format=StructuredChunkTranslation,
        )

        parsed = response.output_parsed
        if parsed is None:
            message = f"Model returned no parsed translation for chunk {request.chunk_id}"
            logger.error(message)
            raise RuntimeError(message)

        return [
            TranslationCandidate(
                cue_index=item.cue_index,
                translated_lines=tuple(item.translated_lines),
                chunk_id=request.chunk_id,
            )
            for item in parsed.translations
        ]

    async def resolve_conflict(
        self,
        cue: SubtitleCue,
        context: tuple[SubtitleCue, ...],
        candidates: tuple[TranslationCandidate, ...],
        source_languages: tuple[str, ...],
        target_language: str,
    ) -> TranslationCandidate:
        """Choose the best translation for a cue from conflicting candidates."""
        logger.info(
            "Resolving translation conflict for cue %d across %d candidates",
            cue.index,
            len(candidates),
        )
        response = await self.client.responses.parse(
            model=self.model,
            reasoning={"effort": self.reasoning_effort},
            input=[
                {"role": "system", "content": _resolution_system_prompt()},
                {
                    "role": "user",
                    "content": _resolution_user_prompt(
                        cue,
                        context,
                        candidates,
                        source_languages,
                        target_language,
                    ),
                },
            ],
            text_format=StructuredConflictResolution,
        )

        parsed = response.output_parsed
        if parsed is None:
            message = f"Model returned no parsed conflict resolution for cue {cue.index}"
            logger.error(message)
            raise RuntimeError(message)

        logger.debug(
            "Resolved cue %d using model rationale: %s", cue.index, parsed.rationale
        )
        return TranslationCandidate(
            cue_index=parsed.cue_index,
            translated_lines=tuple(parsed.chosen_translation),
            chunk_id=-1,
        )


def _translation_system_prompt() -> str:
    """Build the system prompt for chunk translation."""
    return (
        "You are a professional subtitle translator. Translate subtitle cues "
        "faithfully while preserving speaker labels, sound-effect brackets, names, "
        "tone, and subtitle line breaks when practical. Return one translation for "
        "every cue_index in the input. Do not merge, drop, or renumber cues."
    )


def _translation_user_prompt(
    cues: tuple[SubtitleCue, ...],
    source_languages: tuple[str, ...],
    target_language: str,
) -> str:
    """Build the user prompt for chunk translation."""
    return "\n".join(
        [
            f"Source language hints: {_format_languages(source_languages)}",
            f"Target language: {target_language}",
            "",
            "Translate these SRT cues:",
            _format_cues(cues),
        ]
    )


def _resolution_system_prompt() -> str:
    """Build the system prompt for conflict resolution."""
    return (
        "You are a senior subtitle translation editor. Choose the best translated "
        "version for the target cue, considering local context, idiom, continuity, "
        "speaker intent, subtitle readability, and preservation of bracketed sound "
        "effects. Return only the selected cue translation."
    )


def _resolution_user_prompt(
    cue: SubtitleCue,
    context: tuple[SubtitleCue, ...],
    candidates: tuple[TranslationCandidate, ...],
    source_languages: tuple[str, ...],
    target_language: str,
) -> str:
    """Build the user prompt for resolving a cue conflict."""
    return "\n".join(
        [
            f"Source language hints: {_format_languages(source_languages)}",
            f"Target language: {target_language}",
            f"Target cue index: {cue.index}",
            "",
            "Original context:",
            _format_cues(context),
            "",
            "Candidate translations:",
            _format_candidates(candidates),
        ]
    )


def _format_languages(source_languages: tuple[str, ...]) -> str:
    """Format source languages for prompts."""
    if not source_languages:
        return "unknown or mixed languages"
    return ", ".join(source_languages)


def _format_cues(cues: tuple[SubtitleCue, ...]) -> str:
    """Format cues for prompts."""
    blocks: list[str] = []
    for cue in cues:
        blocks.append(
            "\n".join(
                [
                    f"cue_index: {cue.index}",
                    f"timing: {cue.timing}",
                    "text:",
                    cue.text,
                ]
            )
        )
    return "\n\n".join(blocks)


def _format_candidates(candidates: tuple[TranslationCandidate, ...]) -> str:
    """Format translation candidates for prompts."""
    blocks: list[str] = []
    for candidate in candidates:
        blocks.append(
            "\n".join(
                [
                    f"from_chunk_id: {candidate.chunk_id}",
                    f"cue_index: {candidate.cue_index}",
                    "translated_text:",
                    candidate.text,
                ]
            )
        )
    return "\n\n".join(blocks)
