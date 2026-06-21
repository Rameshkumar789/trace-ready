from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_ANTHROPIC_CONFLICT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 12000


@dataclass(frozen=True)
class AnthropicLLMConfig:
    api_key: str
    model: str = DEFAULT_ANTHROPIC_MODEL
    conflict_model: str = DEFAULT_ANTHROPIC_CONFLICT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 0.0
    prompt_cache_enabled: bool = True
    prompt_cache_ttl: str | None = None

    @classmethod
    def from_env(cls) -> "AnthropicLLMConfig":
        _load_local_env_file()
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your shell or bellwether/backend/.env.")
        return cls(
            api_key=api_key,
            model=os.getenv("BELLWETHER_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL).strip() or DEFAULT_ANTHROPIC_MODEL,
            conflict_model=os.getenv("BELLWETHER_ANTHROPIC_CONFLICT_MODEL", DEFAULT_ANTHROPIC_CONFLICT_MODEL).strip()
            or DEFAULT_ANTHROPIC_CONFLICT_MODEL,
            max_tokens=int(os.getenv("BELLWETHER_ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            temperature=float(os.getenv("BELLWETHER_ANTHROPIC_TEMPERATURE", "0")),
            prompt_cache_enabled=os.getenv("BELLWETHER_ANTHROPIC_PROMPT_CACHE", "1").strip().lower()
            not in {"0", "false", "no", "off"},
            prompt_cache_ttl=_normalized_cache_ttl(_env_optional("BELLWETHER_ANTHROPIC_PROMPT_CACHE_TTL")),
        )

    def cache_control(self) -> dict[str, str] | None:
        if not self.prompt_cache_enabled:
            return None
        value = {"type": "ephemeral"}
        ttl = _normalized_cache_ttl(self.prompt_cache_ttl)
        if ttl:
            value["ttl"] = ttl
        return value


@dataclass(frozen=True)
class AnthropicLLMResponse:
    model: str
    response_text: str
    parsed_json: list[dict[str, Any]]
    usage: dict[str, Any]
    stop_reason: str | None
    cache_control: dict[str, Any] | None


class AnthropicJSONParseError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        response_text: str,
        model: str,
        usage: dict[str, Any],
        stop_reason: str | None,
        cache_control: dict[str, Any] | None,
    ):
        super().__init__(message)
        self.response_text = response_text
        self.model = model
        self.usage = usage
        self.stop_reason = stop_reason
        self.cache_control = cache_control


class AnthropicJSONClient:
    def __init__(self, config: AnthropicLLMConfig):
        self.config = config
        try:
            from anthropic import Anthropic
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The anthropic Python SDK is not installed. Run `python -m pip install -e .` "
                "or `python -m pip install anthropic` inside bellwether/ingestion."
            ) from exc
        self._client = Anthropic(api_key=config.api_key)

    def complete_json_array(self, *, system: str, user_prompt: str) -> AnthropicLLMResponse:
        cache_control = self.config.cache_control()
        system_content: str | list[dict[str, Any]] = system
        user_content: str | list[dict[str, Any]] = user_prompt
        if cache_control:
            system_content = [{"type": "text", "text": system, "cache_control": cache_control}]
            user_content = [{"type": "text", "text": user_prompt, "cache_control": cache_control}]
        request: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system_content,
            "messages": [{"role": "user", "content": user_content}],
        }
        message = self._client.messages.create(**request)
        response_text = _message_text(message)
        model = getattr(message, "model", self.config.model)
        usage = _usage_dict(getattr(message, "usage", None))
        stop_reason = getattr(message, "stop_reason", None)
        try:
            parsed_json = extract_json_array(response_text)
        except ValueError as exc:
            raise AnthropicJSONParseError(
                str(exc),
                response_text=response_text,
                model=model,
                usage=usage,
                stop_reason=stop_reason,
                cache_control=cache_control,
            ) from exc
        return AnthropicLLMResponse(
            model=model,
            response_text=response_text,
            parsed_json=parsed_json,
            usage=usage,
            stop_reason=stop_reason,
            cache_control=cache_control,
        )

    def cache_control(self) -> dict[str, str] | None:
        return self.config.cache_control()


def _env_optional(key: str) -> str | None:
    value = os.getenv(key, "").strip()
    return value or None


def _normalized_cache_ttl(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in {"1h"}:
        raise ValueError("BELLWETHER_ANTHROPIC_PROMPT_CACHE_TTL currently supports only blank/default or '1h'.")
    return value


def extract_json_array(response_text: str) -> list[dict[str, Any]]:
    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("Model response did not contain a JSON array.")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, list):
        raise ValueError("Model response JSON must be an array of records.")
    if not all(isinstance(item, dict) for item in parsed):
        raise ValueError("Model response JSON array must contain only objects.")
    return parsed


def _message_text(message: Any) -> str:
    blocks = getattr(message, "content", [])
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _usage_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump(mode="json")
    return {
        key: getattr(usage, key)
        for key in ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
        if hasattr(usage, key)
    }


def _load_local_env_file() -> None:
    candidate_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for path in candidate_paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
