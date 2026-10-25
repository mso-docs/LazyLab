from unittest.mock import patch
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.config import Config
from slothlab.memory.repository import Repository
from slothlab.models import ModelReply
from slothlab.schemas import Budget
from test_agent import ScriptedResearchClient, candidate


class UsageClient(ScriptedResearchClient):
    def generate(self, prompt, schema, max_tokens):
        reply = super().generate(prompt,schema,max_tokens)
        if len(self.calls) == 1:
            return ModelReply(reply.content, None, None, .01)
        return ModelReply(reply.content, 1000000, 5, .01)


def test_usage_overrun_after_unknown_usage_still_stops(tmp_path):
    config = Config(db_path=str(tmp_path/'db.sqlite'), artifact_dir=str(tmp_path), budget=Budget(max_tokens=500000))
    client = UsageClient([[candidate(1)]])
    with Repository(config.db_path) as repo, patch('slothlab.agent.orchestrator.execute') as execute:
        s = ResearchAgent(repo,client,config).create()
        assert s.budget_consumed['tokens'] is None
        assert 'usage exceeded' in s.termination_reason
        execute.assert_not_called()


def test_known_usage_releases_unused_reservation(tmp_path):
    config = Config(db_path=str(tmp_path/'db.sqlite'), artifact_dir=str(tmp_path), budget=Budget(max_tokens=20000,max_rounds=1))
    client = ScriptedResearchClient([[]])
    with Repository(config.db_path) as repo:
        s = ResearchAgent(repo,client,config).create()
        assert s.budget_consumed['tokens'] == 10
        assert s.budget_consumed['token_reservations'] == 10


def test_failed_inference_keeps_usage_unknown_and_charged(tmp_path):
    import pytest
    from slothlab.models import ModelError
    config = Config(db_path=str(tmp_path/'db.sqlite'), budget=Budget(max_tokens=20000))
    client = ScriptedResearchClient([])
    with Repository(config.db_path) as repo, patch.object(client,'generate',side_effect=ModelError('unavailable')):
        with pytest.raises(ModelError):
            ResearchAgent(repo,client,config).create()
        s = repo.list_sessions()[0]
        assert s.state == 'FAILED'
        assert s.budget_consumed['tokens'] is None
        assert s.budget_consumed['token_reservations'] > 0
        assert repo.events(s.id,'model_call_failed')[0]['payload']['token_usage'] is None
