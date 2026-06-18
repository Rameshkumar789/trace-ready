from __future__ import annotations


try:
    from pydantic import BaseModel, Field  # type: ignore
except Exception:

    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self) -> dict:
            return {
                key: _dump(value)
                for key, value in self.__dict__.items()
                if not key.startswith("_")
            }

    def Field(*, min_length: int | None = None, default=None):
        return default


def _dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value
