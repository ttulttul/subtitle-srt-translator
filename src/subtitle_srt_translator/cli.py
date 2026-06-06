"""Command-line interface for subtitle translation."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from subtitle_srt_translator.env import load_openai_api_key
from subtitle_srt_translator.openai_client import OpenAISubtitleTranslator
from subtitle_srt_translator.pipeline import translate_subtitles
from subtitle_srt_translator.progress import ChunkProgressBar
from subtitle_srt_translator.srt import read_srt, render_srt, replace_cue_text

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the subtitle translator CLI."""
    args = _parse_args()
    _configure_logging(args.verbose, args.progress)
    asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> None:
    """Execute the translation workflow."""
    load_openai_api_key(Path.cwd())
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    cues = read_srt(input_path)
    translator = OpenAISubtitleTranslator(
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        cache_dir=args.cache_dir,
        cache_enabled=not args.no_cache,
    )
    progress_bar = ChunkProgressBar() if args.progress else None
    try:
        translations = await translate_subtitles(
            cues,
            translator,
            source_languages=tuple(args.source_language),
            target_language=args.target_language,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            parallelism=args.parallelism,
            progress=progress_bar,
        )
    finally:
        if progress_bar is not None:
            progress_bar.finish()
    output = render_srt(replace_cue_text(cues, translations))

    if output_path:
        logger.info("Writing translated SRT to %s", output_path)
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="subtitle-srt-translator",
        description="Translate SRT subtitles using OpenAI structured outputs.",
    )
    parser.add_argument("input", help="Input SRT file path.")
    parser.add_argument(
        "--source-language",
        action="append",
        default=[],
        help="Plain-text source language hint. Repeat for multiple languages.",
    )
    parser.add_argument(
        "--target-language",
        required=True,
        help="Plain-text target language.",
    )
    parser.add_argument("--output", help="Output SRT file path. Defaults to stdout.")
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--overlap", type=int, default=5)
    parser.add_argument("--parallelism", type=int, default=4)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument(
        "--cache-dir",
        default=".llm-cache",
        help="Directory for cached LLM responses. Enabled by default.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable local LLM response caching.",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Suppress logs and show a chunk status progress bar.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _configure_logging(verbose: bool, progress: bool = False) -> None:
    """Configure process logging."""
    logging.basicConfig(
        level=_log_level(verbose, progress),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)


def _log_level(verbose: bool, progress: bool) -> int:
    """Return the root log level for CLI mode."""
    if verbose:
        return logging.DEBUG
    if progress:
        return logging.CRITICAL
    return logging.INFO
