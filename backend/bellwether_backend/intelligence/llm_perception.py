"""Shared harness for LLM *perception* calls (mapping, classification, extraction, narrative).

Contract used by every AI feature in the audit engine:

1. Cache hit -> re-verify (defense against stale schemas) -> return ``llm_cached``.
2. Cache miss and no ``ANTHROPIC_API_KEY`` -> deterministic ``fallback()`` (never cached).
3. Cache miss with a key -> one live call -> deterministic ``verify`` -> on failure retry
   exactly once with the verification errors appended -> still failing -> ``fallback()``.
4. Only *verified* outputs are written to the cache, so demo runs are cache-hit-only after a
   single warm pass and bit-for-bit reproducible.

Perception never decides compliance: callers turn verified perception outputs into
deterministic, cited checks.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from bellwether_backend.intelligence.anthropic_client import (
    AnthropicJSONClient,
    AnthropicJSONParseError,
    AnthropicLLMConfig,
)
from bellwether_backend.intelligence.llm_cache import LLMCache


logger = logging.getLogger("bellwether.perception")


@dataclass
class PerceptionResult:
    items: list[dict[str, Any]]
    method: str  # "llm_cached" | "llm_live" | "deterministic_fallback"
    model: str | None = None
    errors: list[str] = field(default_factory=list)


def anthropic_key_available() -> bool:
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return True
    # AnthropicLLMConfig.from_env also loads a local .env file; probe it the same way
    # without raising when nothing is configured.
    try:
        AnthropicLLMConfig.from_env()
        return True
    except RuntimeError:
        return False


def build_default_client() -> AnthropicJSONClient | None:
    try:
        return AnthropicJSONClient(AnthropicLLMConfig.from_env())
    except RuntimeError:
        return None


def run_cached_perception(
    *,
    namespace: str,
    cache_key: str,
    system: str,
    user_prompt: str,
    verify: Callable[[list[dict[str, Any]]], list[str]],
    fallback: Callable[[], list[dict[str, Any]]],
    client: AnthropicJSONClient | None = None,
    cache: LLMCache | None = None,
) -> PerceptionResult:
    cache = cache or LLMCache()

    cached = cache.get(namespace, cache_key)
    if cached is not None:
        errors = _safe_verify(verify, cached)
        if not errors:
            return PerceptionResult(items=cached, method="llm_cached")
        logger.warning("llm cache entry failed re-verification namespace=%s key=%s errors=%s", namespace, cache_key, errors)
        cache.delete(namespace, cache_key)

    resolved_client = client if client is not None else build_default_client()
    if resolved_client is None:
        items = fallback()
        return PerceptionResult(items=items, method="deterministic_fallback", errors=["no ANTHROPIC_API_KEY configured"])

    request_sha = hashlib.sha256((system + "\x1f" + user_prompt).encode("utf-8")).hexdigest()
    attempt_prompt = user_prompt
    last_errors: list[str] = []
    model_used: str | None = None
    for attempt in (1, 2):
        try:
            response = resolved_client.complete_json_array(system=system, user_prompt=attempt_prompt)
        except AnthropicJSONParseError as exc:
            last_errors = [f"attempt {attempt}: response was not a JSON array: {exc}"]
            attempt_prompt = _retry_prompt(user_prompt, last_errors)
            continue
        except Exception as exc:  # API/transport failure: degrade, never crash the audit
            logger.warning("llm call failed namespace=%s attempt=%s error=%s", namespace, attempt, exc)
            last_errors = [f"attempt {attempt}: llm call failed: {exc}"]
            break
        model_used = response.model
        errors = _safe_verify(verify, response.parsed_json)
        if not errors:
            cache.put(namespace, cache_key, response.parsed_json, model=response.model, request_sha256=request_sha)
            return PerceptionResult(items=response.parsed_json, method="llm_live", model=response.model)
        last_errors = errors
        attempt_prompt = _retry_prompt(user_prompt, errors)

    items = fallback()
    return PerceptionResult(items=items, method="deterministic_fallback", model=model_used, errors=last_errors)


def _retry_prompt(user_prompt: str, errors: list[str]) -> str:
    bullet_list = "\n- ".join(errors[:20])
    return (
        f"{user_prompt}\n\nYour previous answer failed deterministic verification:\n- {bullet_list}\n"
        "Return a corrected JSON array only, with no commentary."
    )


def _safe_verify(verify: Callable[[list[dict[str, Any]]], list[str]], items: list[dict[str, Any]]) -> list[str]:
    try:
        return list(verify(items))
    except Exception as exc:  # verifier bugs must not take down the pipeline
        return [f"verifier raised: {exc}"]
