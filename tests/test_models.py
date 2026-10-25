import io
import json
import os
from urllib.error import URLError
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from slothlab.models import FakeModelClient, ModelError, ModelReply, OllamaModelClient
from slothlab.schemas import Plan


def test_fake_is_scripted_and_preserves_missing_usage():
    client = FakeModelClient([{"candidates": []}, "bad-json"])
    reply = client.generate("plan", Plan.model_json_schema(), 100)
    assert Plan.model_validate_json(reply.content).candidates == []
    assert reply.total_tokens is None
    with pytest.raises(ValidationError):
        Plan.model_validate_json(client.generate("retry", {}, 100).content)
    with pytest.raises(ModelError, match="exhausted"):
        client.generate("third", {}, 100)
    assert len(client.calls) == 3


def test_ollama_real_request_contract_and_telemetry():
    body = {"done": True, "message": {"content": '{"candidates": []}'}, "prompt_eval_count": 12, "eval_count": 7}
    with patch("slothlab.models.ollama_client.urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as http:
        client = OllamaModelClient("http://localhost:11434/", "test-model")
        reply = client.generate("plan", Plan.model_json_schema(), 80)
    request = http.call_args.args[0]
    payload = json.loads(request.data)
    assert request.full_url == "http://localhost:11434/api/chat"
    assert payload["stream"] is False
    assert payload["format"] == Plan.model_json_schema()
    assert payload["options"] == {"temperature": 0, "num_predict": 80}
    assert reply.total_tokens == 19
    assert reply.elapsed_seconds >= 0


def test_ollama_missing_usage_stays_none():
    body = {"done": True, "message": {"content": "{}"}}
    with patch("slothlab.models.ollama_client.urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
        reply = OllamaModelClient("http://localhost:11434", "test").generate("hi", {}, 64)
    assert reply.prompt_tokens is None
    assert reply.completion_tokens is None
    assert reply.total_tokens is None


@pytest.mark.parametrize("body", [{}, [], {"done": False, "message": {"content": "{}"}}, {"done": True, "message": {"content": "{}"}, "eval_count": -1}])
def test_ollama_invalid_protocol_rejected(body):
    with patch("slothlab.models.ollama_client.urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
        with pytest.raises(ModelError):
            OllamaModelClient("http://localhost:11434", "test").generate("hi", {}, 64)


def test_ollama_unavailable_is_actionable_and_no_fake():
    with patch("slothlab.models.ollama_client.urlopen", side_effect=URLError("refused")):
        with pytest.raises(ModelError, match="ollama serve"):
            OllamaModelClient("http://localhost:11434", "test").generate("hi", {}, 64)


def test_spec_rejects_extra_fields_and_invalid_seed():
    with pytest.raises(ValidationError):
        Plan.model_validate({"candidates": [{"hypothesis_id": "h", "seed": "1", "rationale": "test"}]})
    with pytest.raises(ValidationError):
        Plan.model_validate({"candidates": [], "execute_shell": "bad"})


@pytest.mark.ollama
@pytest.mark.skipif(os.environ.get("SLOTHLAB_TEST_OLLAMA") != "1", reason="opt-in real local inference")
def test_local_ollama_integration():
    model = os.environ.get("OLLAMA_MODEL")
    if not model:
        pytest.fail("Set OLLAMA_MODEL to an installed local model")
    client = OllamaModelClient(os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"), model)
    reply = client.generate("Return an object with candidates equal to an empty array.", Plan.model_json_schema(), 128)
    assert Plan.model_validate_json(reply.content).candidates == []


def test_model_weight_provenance_is_captured_without_generation():
    body={'models':[{'name':'local:latest','digest':'sha256:verified-test-digest','details':{'quantization_level':'Q4_K_M'}}]}
    with patch('slothlab.models.ollama_client.urlopen',return_value=io.BytesIO(json.dumps(body).encode())) as http:
        provenance=OllamaModelClient('http://localhost:11434','local').provenance()
    assert provenance['digest']=='sha256:verified-test-digest'
    assert http.call_args.args[0].endswith('/api/tags')
    with patch('slothlab.models.ollama_client.urlopen',side_effect=URLError('unavailable')):
        assert OllamaModelClient('http://localhost:11434','local').provenance()['digest'] is None
