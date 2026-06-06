"""Tests for explicit LLM response caching."""

from pathlib import Path

from subtitle_srt_translator.cache import LLMResponseCache


def test_cache_key_depends_on_model_and_prompt_text() -> None:
    """Cache keys are stable and distinguish model or prompt changes."""
    first = LLMResponseCache.build_key(model="gpt-5.4-mini", prompt_text="hello")
    second = LLMResponseCache.build_key(model="gpt-5.4-mini", prompt_text="hello")
    other_model = LLMResponseCache.build_key(model="gpt-5.4", prompt_text="hello")
    other_prompt = LLMResponseCache.build_key(model="gpt-5.4-mini", prompt_text="hi")

    assert first == second
    assert first != other_model
    assert first != other_prompt


def test_cache_round_trip(tmp_path: Path) -> None:
    """Payloads can be stored and loaded by explicit model and prompt key."""
    cache = LLMResponseCache(tmp_path)
    payload = {"translations": [{"cue_index": 1, "translated_lines": ["Hello"]}]}

    assert cache.get(model="gpt-5.4-mini", prompt_text="prompt") is None

    cache.set(model="gpt-5.4-mini", prompt_text="prompt", payload=payload)

    assert cache.get(model="gpt-5.4-mini", prompt_text="prompt") == payload
    assert cache.get(model="gpt-5.4", prompt_text="prompt") is None
