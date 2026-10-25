from slothlab.models.base import ModelClient, ModelError, ModelReply
from slothlab.models.ollama_client import OllamaModelClient
from slothlab.models.fake_client import FakeModelClient

__all__ = ["ModelClient", "ModelError", "ModelReply", "OllamaModelClient", "FakeModelClient", "client_from_config"]


def client_from_config(config):
    return OllamaModelClient(config.base_url, config.model,
                             timeout=config.inference_timeout_seconds,
                             context_tokens=config.inference_context_tokens,
                             threads=config.inference_threads,
                             thinking=config.inference_thinking)
