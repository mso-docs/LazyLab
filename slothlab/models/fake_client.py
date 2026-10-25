"""Explicit deterministic test double. Never selected by the production CLI."""
import json
from collections.abc import Iterable
from typing import Any
from slothlab.models.base import ModelError, ModelReply


class FakeModelClient:
    name = "fake-scripted-test-only"

    def __init__(self, responses: Iterable[str | dict | ModelReply]):
        self.responses = iter(responses)
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, schema: dict[str, Any], max_tokens: int) -> ModelReply:
        self.calls.append({"prompt": prompt, "schema": schema, "max_tokens": max_tokens})
        try:
            response = next(self.responses)
        except StopIteration as exc:
            raise ModelError("FakeModelClient script exhausted; no response was fabricated") from exc
        if isinstance(response, ModelReply):
            return response
        return ModelReply(content=response if isinstance(response, str) else json.dumps(response))
