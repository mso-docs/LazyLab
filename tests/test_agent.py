"""Behavior-level integration tests: scripted reasoning, real registered science."""
import json
from unittest.mock import patch

from slothlab.agent.orchestrator import ResearchAgent
from slothlab.config import Config
from slothlab.memory.repository import Repository
from slothlab.models import FakeModelClient, ModelReply
from slothlab.schemas import Budget, Hypothesis, ResearchSession


class ScriptedResearchClient(FakeModelClient):
    """Test-only context-aware script so generated session/result IDs stay real."""
    def __init__(self, plans, malformed=False):
        super().__init__([])
        self.plans = iter(plans)
        self.malformed = malformed

    def generate(self, prompt, schema, max_tokens):
        self.calls.append({"prompt": prompt, "schema": schema, "max_tokens": max_tokens})
        context = json.JSONDecoder().raw_decode(prompt.split("Context: ", 1)[1])[0]
        task = prompt.split("Task: ", 1)[1].split("\nContext:", 1)[0]
        if "Generate two" in task:
            payload = {"hypotheses": [{"id": "h1", "session_id": context["session_id"], "statement": "Correction helps under shift", "falsifiable_prediction": "delta_brier < 0"}, {"id": "h2", "session_id": context["session_id"], "statement": "Correction may worsen under miscalibration", "falsifiable_prediction": "delta_brier > 0 under temperature 4"}]}
        elif "Interpret recorded" in task:
            evidence = [r["id"] for r in context["evidence"] if r["status"] == "COMPLETED"]
            payload = {"assessments": [{"hypothesis_id": context["hypotheses"][0]["id"], "status": "CONTRADICTED", "evidence_ids": evidence, "explanation": "Scripted provisional interpretation; use actual deltas in report."}], "next_direction": "Revise the claim and investigate independent replications before concluding."}
        elif self.malformed:
            return ModelReply("not JSON", 2, 3, 0.01)
        else:
            candidates = next(self.plans, [])
            candidates = [dict(c, hypothesis_id=context["hypotheses"][0]["id"]) if c["hypothesis_id"] == "h1" else c for c in candidates]
            payload = {"candidates": candidates}
        return ModelReply(json.dumps(payload), 2, 3, 0.01)


def candidate(seed, **changes):
    return {"hypothesis_id": "h1", "seed": seed, "replicate_group": "shift-condition-a", "rationale": "Measure independent prior-correction trial", "parameters": {"sample_size": 100}, **changes}


def configured(tmp_path, **budget):
    return Config(db_path=str(tmp_path / "state.sqlite"), artifact_dir=str(tmp_path / "artifacts"), budget=Budget(max_tokens=500000, wall_seconds=60, **budget))


def test_multiround_real_science_cache_replication_and_persisted_stages(tmp_path):
    config = configured(tmp_path, max_rounds=4, max_experiments=4)
    client = ScriptedResearchClient([[candidate(1)], [candidate(1)], [candidate(2)], []])
    with Repository(config.db_path) as repo:
        session = ResearchAgent(repo, client, config).create()
        assert session.state == "STOPPED"
        assert session.budget_consumed["experiments"] == 2
        assert session.budget_consumed["cache_hits"] == 1
        assert len(repo.results(session.id)) == 2
        actions = [d.decision for d in repo.decisions(session.id)]
        assert actions == ["EXECUTE", "REUSE", "REPLICATE"]
        assert {e["payload"]["to"] for e in repo.events(session.id, "state_transition")} >= {"HYPOTHESIZING", "PLANNING", "VALIDATING", "EXECUTING", "ANALYZING", "REPLANNING", "STOPPED"}
        usage = repo.events(session.id, "model_usage")
        assert session.budget_consumed["tokens"] == len(usage) * 5
        assert session.budget_consumed["model_calls"] == len(client.calls)
        assert all(r.runtime_seconds > 0 for r in repo.results(session.id))
        # Free-form model status is never promoted to an established claim.
        assert repo.hypotheses(session.id)[0].status == "INCONCLUSIVE"
        assert all(not event["payload"]["verified_claim"] for event in repo.events(session.id, "interpretation"))
    with Repository(config.db_path) as reopened:
        assert reopened.get_session(session.id).budget_consumed["experiments"] == 2
        assert len(reopened.results(session.id)) == 2


def test_invalid_planning_repairs_and_replans_are_bounded(tmp_path):
    config = configured(tmp_path, max_rounds=20, max_experiments=4, repair_attempts=1, no_progress_rounds=2)
    client = ScriptedResearchClient([], malformed=True)
    with Repository(config.db_path) as repo, patch("slothlab.agent.orchestrator.execute") as execution:
        session = ResearchAgent(repo, client, config).create()
        assert session.state == "STOPPED"
        assert "Repeated unproductive planning" in session.termination_reason
        assert session.iteration_count == 2
        assert len(repo.events(session.id, "invalid_model_output")) == 4
        assert session.budget_consumed["experiments"] == 0
        assert len(client.calls) == 5  # one hypothesis call and two rounds * two repairs
        execution.assert_not_called()


def test_token_budget_checked_before_any_model_call(tmp_path):
    config = Config(db_path=str(tmp_path / "state.sqlite"), artifact_dir=str(tmp_path), budget=Budget(max_tokens=64, call_token_reserve=64))
    client = ScriptedResearchClient([])
    with Repository(config.db_path) as repo:
        session = ResearchAgent(repo, client, config).create()
        assert "next model call cannot fit" in session.termination_reason
        assert client.calls == []
        assert session.budget_consumed["token_reservations"] == 0


def test_unauthorized_parameter_and_seed_never_execute(tmp_path):
    config = configured(tmp_path, max_rounds=1)
    config.objective.permitted_parameters = {"sample_size": [200]}
    client = ScriptedResearchClient([[candidate(1), candidate(10001)]])
    with Repository(config.db_path) as repo, patch("slothlab.agent.orchestrator.execute") as execution:
        session = ResearchAgent(repo, client, config).create()
        assert [d.decision for d in repo.decisions(session.id)] == ["REJECT", "REJECT"]
        assert session.budget_consumed["experiments"] == 0
        execution.assert_not_called()


def test_experiment_budget_rechecked_between_candidates(tmp_path):
    config = configured(tmp_path, max_rounds=1, max_experiments=1)
    client = ScriptedResearchClient([[candidate(1), candidate(2)]])
    with Repository(config.db_path) as repo:
        session = ResearchAgent(repo, client, config).create()
        assert session.budget_consumed["experiments"] == 1
        assert len(repo.results(session.id)) == 1
        assert repo.decisions(session.id)[-1].decision == "STOP"


def test_resume_preserves_reservations_without_regenerating_hypotheses(tmp_path):
    config = configured(tmp_path, max_rounds=1)
    client = ScriptedResearchClient([[]])
    with Repository(config.db_path) as repo:
        repo.save_objective(config.objective)
        session = ResearchSession(objective_id=config.objective.id, model_name=client.name, state="REPLANNING", budget_configuration=config.budget)
        session.budget_consumed["token_reservations"] = 100
        session.budget_consumed["wall_seconds"] = 1.5
        repo.save_session(session)
        repo.save_hypothesis(Hypothesis(id="h1", session_id=session.id, statement="Correction helps", falsifiable_prediction="delta_brier < 0"))
        resumed = ResearchAgent(repo, client, config).run(session.id)
        assert len(client.calls) == 1
        assert "Propose at most" in client.calls[0]["prompt"]
        assert resumed.budget_consumed["token_reservations"] > 100
        assert resumed.budget_consumed["wall_seconds"] >= 1.5
        # Terminal resumes are idempotent and do not call inference.
        ResearchAgent(repo, client, config).run(session.id)
        assert len(client.calls) == 1


def test_cross_session_reuse_gets_interpreted_with_correct_local_hypothesis(tmp_path):
    config = configured(tmp_path,max_rounds=1)
    with Repository(config.db_path) as repo:
        first = ResearchAgent(repo,ScriptedResearchClient([[candidate(1)]]),config).create()
        original = repo.results(first.id)[0]
        second = ResearchAgent(repo,ScriptedResearchClient([[candidate(1)]]),config).create()
        assert second.budget_consumed['experiments'] == 0
        assert second.budget_consumed['cache_hits'] == 1
        assert repo.results(second.id)[0].id == original.id
        assert len(repo.events(second.id,'interpretation')) == 1
        assert repo.events(second.id,'interpretation')[0]['payload']['references_valid'] is True
