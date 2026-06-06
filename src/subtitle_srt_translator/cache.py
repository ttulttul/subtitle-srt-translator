"""Explicit local cache for LLM responses."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from joblib import Memory

logger = logging.getLogger(__name__)

CachePayload = dict[str, Any]


class LLMResponseCache:
    """Joblib-backed cache keyed by model and exact prompt text."""

    def __init__(self, cache_dir: Path | str) -> None:
        """Initialize the response cache."""
        self.memory = Memory(location=cache_dir, verbose=0)

    def get(self, *, model: str, prompt_text: str) -> CachePayload | None:
        """Return a cached payload for the model and prompt text, if present."""
        call_id = self._call_id(model=model, prompt_text=prompt_text)
        display_key = _short_key(call_id[1])
        if not self.memory.store_backend.contains_item(call_id):
            logger.debug("LLM cache miss for key %s", display_key)
            return None

        logger.info("Using cached LLM response for key %s", display_key)
        payload = self.memory.store_backend.load_item(call_id, verbose=0)
        if not isinstance(payload, dict):
            logger.warning("Ignoring invalid cached LLM payload for key %s", display_key)
            return None
        return payload

    def set(self, *, model: str, prompt_text: str, payload: CachePayload) -> None:
        """Store a payload for the model and prompt text."""
        call_id = self._call_id(model=model, prompt_text=prompt_text)
        self.memory.store_backend.dump_item(call_id, payload, verbose=0)
        logger.debug("Stored LLM response in cache for key %s", _short_key(call_id[1]))

    @staticmethod
    def build_key(*, model: str, prompt_text: str) -> str:
        """Build a deterministic cache key from model and exact prompt text."""
        cache_input = json.dumps(
            {"model": model, "prompt_text": prompt_text},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(cache_input.encode("utf-8")).hexdigest()

    @classmethod
    def _call_id(cls, *, model: str, prompt_text: str) -> tuple[str, str]:
        """Build the joblib call id for a model and prompt."""
        return (
            "subtitle_srt_translator.llm_response",
            cls.build_key(model=model, prompt_text=prompt_text),
        )


def _short_key(cache_key: str) -> str:
    """Return a short display form for a cache key."""
    return f"{cache_key[:5]}..."
