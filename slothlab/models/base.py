"""Small interchangeable inference interface; missing telemetry stays missing."""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelReply:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    elapsed_seconds: float = 0.0

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None or self.completion_tokens is None:
            return None
        return self.prompt_tokens + self.completion_tokens


class ModelError(RuntimeError):
    """Inference failed; the application must not substitute fabricated output."""


class ModelClient(Protocol):
    @property
    def name(self) -> str: ...

    def generate(self, prompt: str, schema: dict[str, Any], max_tokens: int) -> ModelReply: ...
