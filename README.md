# Subtitle SRT Translator

Translate SRT subtitle files with the OpenAI Responses API and structured outputs.

The CLI reads an SRT file, translates subtitle cues in overlapping chunks, and resolves disagreements in the overlap with a follow-up model call. It preserves cue timings, speakers, cue numbering when present, and blank-line SRT formatting.

## Install

This project supports Python 3.11 through 3.15.

```bash
uv sync
```

## Authentication

Set `OPENAI_API_KEY` in the environment, in `.env` at the project root, or in `~/.env`.

```bash
OPENAI_API_KEY=<your-openai-api-key> uv run subtitle-srt-translator input.srt --target-language English
```

## Usage

```bash
uv run subtitle-srt-translator "/path/to/input.srt" \
  --source-language Hebrew \
  --source-language Arabic \
  --target-language English \
  --output "/path/to/output.en.srt"
```

Useful options:

- `--chunk-size 10`: number of subtitle cues per model translation request.
- `--overlap 5`: number of cues shared between adjacent chunks.
- `--parallelism 4`: maximum concurrent OpenAI requests.
- `--model gpt-5.4-mini`: model used for translation and conflict resolution.
- `--reasoning-effort medium`: Responses API reasoning effort.
- `--cache-dir .llm-cache`: local `joblib.Memory` cache for LLM responses.
- `--no-cache`: disable local LLM response caching.
- `--verbose`: enable debug logging.

When `--output` is omitted, the translated SRT is written to stdout.

## Development

```bash
uv run pytest
```

To validate the supported Python range locally for the interpreters available
to uv:

```bash
uv run python scripts/test_python_versions.py 3.11 3.12 3.13 3.14 --skip-missing
```

For live smoke tests, use a tiny SRT sample first. Full subtitle files can produce many parallel model requests depending on `--chunk-size`, `--overlap`, and `--parallelism`.
