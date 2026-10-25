"""Real local Ollama inference over the documented /api/chat API.

Reference: https://docs.ollama.com/api/chat and
https://docs.ollama.com/capabilities/structured-outputs
No generated tools or code are executed by this client.
"""
import json
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from slothlab.models.base import ModelError, ModelReply


class OllamaModelClient:
    def __init__(self, base_url: str, model: str, timeout: float = 300.0,
                 context_tokens: int | None = None, threads: int | None = None, thinking: bool | None = None):
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("OLLAMA_BASE_URL must be an HTTP(S) URL")
        if not model.strip():
            raise ValueError("Set OLLAMA_MODEL to a locally installed model name")
        if timeout <= 0:
            raise ValueError("Ollama timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.context_tokens = context_tokens
        self.threads = threads
        self.thinking = thinking

    @property
    def name(self) -> str:
        return self.model

    def provenance(self, timeout=5.0):
        """Best-effort weight identity; changing a mutable model tag is observable."""
        try:
            with urlopen(self.base_url+'/api/tags',timeout=min(self.timeout,max(.01,timeout))) as response:
                body=json.loads(response.read(1024*1024))
            aliases={self.model,self.model+':latest'} if ':' not in self.model.rsplit('/',1)[-1] else {self.model}
            entries=body.get('models',[]) if isinstance(body,dict) else []
            entry=next((row for row in entries if row.get('name') in aliases or row.get('model') in aliases),None)
            return {'model':self.model,'digest':entry.get('digest') if entry else None,
                    'details':entry.get('details',{}) if entry else {},
                    'endpoint':self.base_url,'temperature':0,'context_tokens':self.context_tokens,
                    'threads':self.threads,'thinking':self.thinking}
        except (OSError,ValueError,TypeError,AttributeError) as exc:
            return {'model':self.model,'digest':None,'endpoint':self.base_url,'error':str(exc)}

    def generate(self, prompt: str, schema: dict[str, Any], max_tokens: int) -> ModelReply:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt + "\nReturn JSON matching this schema:\n" + json.dumps(schema)}],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
        if self.context_tokens is not None:
            payload["options"]["num_ctx"] = self.context_tokens
        if self.threads is not None:
            payload["options"]["num_thread"] = self.threads
        if self.thinking is not None:
            payload['think'] = self.thinking
        request = Request(
            self.base_url + "/api/chat",
            data=json.dumps(payload, allow_nan=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ModelError("Ollama response exceeded the 8 MiB response limit")
            body = json.loads(raw)
        except HTTPError as exc:
            raise ModelError(
                f"Ollama returned HTTP {exc.code} for model {self.model!r}. "
                "Check OLLAMA_BASE_URL and run `ollama list`; pull the configured model if missing."
            ) from exc
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ModelError(
                "Cannot reach Ollama or inference timed out. Start `ollama serve`, "
                "check OLLAMA_BASE_URL, and ensure OLLAMA_MODEL is installed. "
                f"Connection detail: {exc}"
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelError("Ollama returned invalid JSON; check the endpoint and server logs") from exc
        if not isinstance(body, dict):
            raise ModelError("Ollama response must be a JSON object")
        if body.get("error"):
            raise ModelError(f"Ollama inference failed: {body['error']}")
        message = body.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ModelError("Ollama response has no text message.content")
        if body.get("done") is not True:
            raise ModelError("Ollama returned an incomplete non-streaming response")
        if body.get("done_reason") == "length":
            raise ModelError("Ollama output was truncated by the generation limit; no proposal was accepted")

        def count(key: str) -> int | None:
            value = body.get(key)
            if value is None:
                return None
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ModelError(f"Ollama returned invalid token telemetry: {key}")
            return value

        return ModelReply(
            content=message["content"],
            prompt_tokens=count("prompt_eval_count"),
            completion_tokens=count("eval_count"),
            elapsed_seconds=time.perf_counter() - started,
        )
