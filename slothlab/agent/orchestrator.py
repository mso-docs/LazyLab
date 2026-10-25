"""Bounded research state machine. Model text cannot directly execute actions."""
import json
import logging
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from pydantic import ValidationError
from slothlab.config import Config
from slothlab.schemas import ResearchSession, Hypothesis, HypothesisBatch, Plan, Analysis, ExperimentSpec, now, uid
from slothlab.lazyloop.controller import validate_proposal, decide, observed_specs
from slothlab.lazyloop.fingerprint import fingerprint
from slothlab.experiments.executor import execute, recover
from slothlab.agent.critic import assess_hypothesis
from slothlab.agent.planner import hypotheses_schema, decode_hypotheses, planning_schema, decode_plan, _compact, NoViablePlan, validate_confirmation_batch
from slothlab.lazyloop.progress import repeated_actions, action_signature
from slothlab.lazyloop.stopping import objective_completion
from slothlab.lazyloop.audit import termination_audit

TERMINAL = {"COMPLETED", "STOPPED", "FAILED"}
TRANSITIONS = {
    "INITIALIZED": {"HYPOTHESIZING", "PLANNING"},
    "HYPOTHESIZING": {"PLANNING"},
    "PLANNING": {"VALIDATING"},
    "VALIDATING": {"EXECUTING", "ANALYZING", "REPLANNING"},
    "EXECUTING": {"EXECUTING", "ANALYZING", "REPLANNING"},
    "ANALYZING": {"REPLANNING"},
    "REPLANNING": {"PLANNING"},
}


class BudgetExhausted(RuntimeError):
    pass


class ResearchAgent:
    def __init__(self, repo, client, config: Config):
        self.repo, self.client = repo, client
        self.config=config.model_copy(update={
            'db_path':str(Path(repo.path).resolve()) if str(repo.path)!=':memory:' else ':memory:',
            'artifact_dir':str(Path(config.artifact_dir).resolve())})
        self.session = None
        self._clock = time.monotonic()
        self._base_wall = 0.0

    def checkpoint(self):
        s = self.session
        s.budget_consumed["wall_seconds"] = self._base_wall + time.monotonic() - self._clock
        s.last_checkpoint = now()
        self.repo.save_session(s)

    def transition(self, state, recovery=False):
        old = self.session.state
        if not recovery and state not in TERMINAL and state not in TRANSITIONS.get(old, set()):
            raise RuntimeError(f"Invalid research state transition: {old} -> {state}")
        self.session.state = state
        logging.getLogger(__name__).info("Session %s: %s -> %s", self.session.id, old, state)
        self.repo.event(self.session.id, "state_transition", {"from": old, "to": state, "recovery": recovery})
        self.checkpoint()
        if state in TERMINAL:
            self.repo.event(self.session.id, "termination_audit", termination_audit(self.repo,self.session,self.config))

    def stop(self, reason, failed=False):
        self.session.termination_reason = reason
        self.transition("FAILED" if failed else "STOPPED")
        return self.session

    def budget_check(self):
        self.checkpoint()
        s, b = self.session, self.session.budget_configuration
        if s.budget_consumed["wall_seconds"] >= b.wall_seconds:
            raise BudgetExhausted("Budget exhausted: wall clock")
        if s.budget_consumed["token_reservations"] >= b.max_tokens:
            raise BudgetExhausted("Budget exhausted: model tokens (conservative reservations)")

    def ask(self, schema, task, context, output_schema=None, transform=None):
        b = self.session.budget_configuration
        output_schema = output_schema or schema.model_json_schema()
        error = ""
        for attempt in range(b.repair_attempts + 1):
            self.budget_check()
            prompt = ("You are a scientific research planner. Return only JSON matching the schema. "
                      "Never invent measurements. Preserve uncertainty; oracle test prevalence is a synthetic assumption. "
                      "Do not request code, shell commands, network access or tools.\n"
                      f"Task: {task}\nContext: {json.dumps(context, separators=(',', ':'))}\n{error}")
            # UTF-8 byte count is a deliberately conservative tokenizer-independent input bound.
            # Reserve input plus output BEFORE contacting the model, including failures.
            input_bound = len((prompt + json.dumps(output_schema)).encode()) + 256
            reservation = input_bound + b.call_token_reserve
            used = self.session.budget_consumed
            if used["token_reservations"] + reservation > b.max_tokens:
                raise BudgetExhausted("Budget exhausted: next model call cannot fit token reservation")
            used["token_reservations"] += reservation
            used["model_calls"] += 1
            previous_tokens = used["tokens"]
            used["tokens"] = None  # A crash during inference leaves usage unknown.
            self.repo.event(self.session.id, "model_call_reserved", {"tokens": reservation, "attempt": attempt})
            self.checkpoint()
            remaining = b.wall_seconds - used["wall_seconds"]
            if hasattr(self.client, "timeout"):
                self.client.timeout = min(self.client.timeout, max(0.01, remaining))
            call_started = time.monotonic()
            try:
                reply = self.client.generate(prompt, output_schema, b.call_token_reserve)
            except BaseException as exc:
                elapsed = time.monotonic()-call_started
                used["inference_seconds"] += elapsed
                self.repo.event(self.session.id, "model_call_failed", {"error": type(exc).__name__, "elapsed_seconds": elapsed, "token_usage": None})
                self.checkpoint()
                raise
            used["inference_seconds"] += reply.elapsed_seconds
            total = reply.total_tokens
            self.repo.event(self.session.id, "model_usage", {"prompt_tokens": reply.prompt_tokens, "completion_tokens": reply.completion_tokens, "elapsed_seconds": reply.elapsed_seconds})
            if total is not None and total > reservation:
                used["token_reservations"] += total-reservation
                used["tokens"] = None if previous_tokens is None else previous_tokens+total
                self.checkpoint()
                raise BudgetExhausted("Integrity failure: model usage exceeded conservative reservation")
            if total is not None:
                used["token_reservations"] -= reservation - total
            if total is None or previous_tokens is None:
                used["tokens"] = None
            else:
                used["tokens"] = previous_tokens + total
            self.checkpoint()
            try:
                payload = json.loads(reply.content)
                if transform:
                    payload = transform(payload)
                return schema.model_validate(payload)
            except (ValidationError, ValueError, TypeError, AttributeError) as exc:
                error = "Previous output failed validation; repair it: " + str(exc)[:800]
                self.repo.event(self.session.id, "invalid_model_output", {"error": error})
        raise ValueError("Model output remained invalid after bounded repair attempts")

    def initialize(self):
        objective = self.config.objective
        try:
            if self.repo.get_objective(objective.id) != objective:
                objective=objective.model_copy(update={'id':uid()})
                self.config=self.config.model_copy(update={'objective':objective})
        except KeyError:
            pass
        self.repo.save_objective(objective)
        session = ResearchSession(objective_id=objective.id, model_name=self.client.name,
                                  budget_configuration=self.config.budget, mode=self.config.mode)
        self.repo.save_session(session)
        self.repo.event(session.id, "configuration", self.config.model_dump(mode="json"))
        provenance=getattr(self.client,'provenance',None)
        if provenance:
            self.repo.event(session.id,'model_provenance',provenance(timeout=min(5.,session.budget_configuration.wall_seconds)))
        return session

    def create(self):
        return self.run(self.initialize().id)

    def context(self):
        results = self.repo.results(self.session.id)
        hypotheses = self.repo.hypotheses(self.session.id)
        specs = self.repo.specs(self.session.id)
        directions = self.repo.events(self.session.id, "research_direction")
        rejections = [d for d in self.repo.decisions(self.session.id) if d.decision in {"REJECT", "DEFER"}]
        # Compact measurements and the latest actual analysis guide subsequent
        # scientific choices; no unbounded conversational transcript is appended.
        return {"session_id": self.session.id,
                "objective": {"question": self.config.objective.question,
                              "permitted_parameters": self.config.objective.permitted_parameters,
                              "constraints": self.config.objective.constraints,
                              "success_criteria": self.config.objective.success_criteria},
                "hypotheses": [{"id": h.id, "statement": h.statement,
                                "falsifiable_prediction": h.falsifiable_prediction,
                                "expected_delta_direction": h.expected_delta_direction,
                                "status": h.status} for h in hypotheses[-8:]],
                "evidence": [{"id": r.id, "experiment_id": r.experiment_id,
                              "status": r.status, "metrics": r.metrics} for r in results[-12:]],
                "prior_specs": [{"hypothesis_id": s.hypothesis_id, "parameters": s.parameters.model_dump(),
                                 "seed": s.seed, "phase": s.phase, "replicate_group": s.replicate_group}
                                for s in specs[-8:]],
                "latest_research_direction": directions[-1]["payload"]["text"] if directions else None,
                "recent_rejections": [{"reason": d.reason, "action": d.decision} for d in rejections[-3:]],
                "allowed_exploratory_seeds": self.config.exploratory_seeds[:100],
                "reserved_confirmatory_seeds": self.config.confirmatory_seeds[:20],
                "remaining_experiments": self.config.budget.max_experiments-self.session.budget_consumed["experiments"]}

    def apply_analysis(self, analysis):
        hypotheses = {h.id: h for h in self.repo.hypotheses(self.session.id)}
        results = {r.id: r for r in self.repo.results(self.session.id) if r.status == "COMPLETED"}
        specs = {s.id: s for s in self.repo.specs(self.session.id)}
        for a in analysis.assessments:
            evidence_specs = dict(specs)
            for decision in self.repo.decisions(self.session.id):
                proposal = specs.get(decision.experiment_id)
                if decision.decision == "REUSE" and proposal and proposal.hypothesis_id == a.hypothesis_id:
                    for reference in decision.evidence_references:
                        if reference in results:
                            original_id = results[reference].experiment_id
                            evidence_specs[original_id] = proposal.model_copy(update={"id": original_id})
            valid = (a.hypothesis_id in hypotheses and bool(a.evidence_ids)
                     and all(i in results and results[i].experiment_id in evidence_specs
                             and evidence_specs[results[i].experiment_id].hypothesis_id == a.hypothesis_id
                             for i in a.evidence_ids))
            # A free-form prediction cannot be mechanically certified. Model assessments
            # remain proposed interpretation, never an established scientific claim.
            payload = a.model_dump(mode="json")
            payload["references_valid"] = valid
            payload["verified_claim"] = False
            self.repo.event(self.session.id, "interpretation", payload)
            if a.hypothesis_id in hypotheses:
                h = hypotheses[a.hypothesis_id]
                verdict = assess_hypothesis(h, list(evidence_specs.values()), list(results.values()),
                                            self.session.budget_configuration.minimum_replications)
                h.status = verdict["status"]
                self.repo.save_hypothesis(h)
                self.repo.event(self.session.id, "verified_assessment", {"hypothesis_id": h.id, **verdict})
                statement, prediction = getattr(a, "revised_statement", None), getattr(a, "revised_prediction", None)
                if statement is not None or prediction is not None:
                    if not valid or not statement or not statement.strip() or not prediction or not prediction.strip():
                        self.repo.event(self.session.id, "hypothesis_revision_rejected", {"hypothesis_id": h.id,
                                        "reason": "A revision needs valid measured references and a complete falsifiable prediction"})
                        continue
                    direction = getattr(a, "revised_direction", None)
                    already = any(other.statement == statement and other.falsifiable_prediction == prediction
                                  and other.expected_delta_direction == direction
                                  for other in self.repo.hypotheses(self.session.id))
                    if not already:
                        revised = Hypothesis(session_id=self.session.id,statement=statement,
                                             falsifiable_prediction=prediction,expected_delta_direction=direction,
                                             assumptions=list(h.assumptions),status="PROPOSED")
                        self.repo.save_hypothesis(revised)
                        self.repo.event(self.session.id,"hypothesis_revision",{"old_hypothesis_id":h.id,
                                        "new_hypothesis_id":revised.id,"old":h.model_dump(mode="json"),
                                        "new":revised.model_dump(mode="json"),"evidence_ids":a.evidence_ids,
                                        "reason":"Model revised a prediction using recorded observations; new claim is untested"})
        self.repo.event(self.session.id, "research_direction", {"text": analysis.next_direction})

    def complete_if_satisfied(self):
        specs = {s.id: s for s in self.repo.specs(self.session.id)}
        results = self.repo.results(self.session.id)
        for result in results:
            if result.experiment_id not in specs:
                try:
                    specs[result.experiment_id] = self.repo.get_spec(result.experiment_id)
                except KeyError:
                    pass
        verdict = objective_completion(self.config, list(specs.values()), results, self.repo.verified)
        self.repo.event(self.session.id, "completion_check", verdict)
        if verdict["satisfied"]:
            self.session.termination_reason = verdict["reason"]
            self.transition("COMPLETED")
            return True
        return False

    def reconcile_interrupted(self):
        s = self.session
        decisions = self.repo.decisions(s.id)
        done = {r.experiment_id for r in self.repo.results(s.id)}
        reserved = {d.experiment_id for d in decisions if d.decision in {"EXECUTE", "REPLICATE"}}
        pending = reserved-done
        for experiment_id in pending:
            spec = self.repo.get_spec(experiment_id)
            restored = recover(spec, Path(self.config.artifact_dir)/s.id/"experiments")
            if restored is not None:
                self.repo.save_result(s.id, restored)
                self.repo.event(s.id, "execution_reconciled", {"experiment_id": experiment_id,
                                "result_id": restored.id, "policy": "verified atomic receipt; no execution repeated"})
            else:
                self.repo.event(s.id, "interrupted_work", {"experiment_id": experiment_id,
                                "policy": "no verified receipt; charged reservation retained; not treated as success"})
        self.checkpoint()

    def continue_confirmation(self, expected):
        """Complete the already-authorized batch before exposing further held-out data.

        Any uncommitted retry incurs another reservation; completed receipts are
        reconciled first, so successful scientific work is never silently rerun.
        """
        s, b = self.session, self.session.budget_configuration
        successful = {r.experiment_id for r in self.repo.results(s.id) if r.status == "COMPLETED"}
        hypotheses = {h.id for h in self.repo.hypotheses(s.id)}
        for experiment_id in expected:
            if experiment_id in successful:
                continue
            self.budget_check()
            if s.budget_consumed["experiments"] >= b.max_experiments:
                return self.stop("Budget exhausted during interrupted final confirmation; evidence insufficient")
            spec = self.repo.get_spec(experiment_id)
            validate_proposal(spec, self.config, hypotheses)
            decision, cached = decide(spec, s, self.config, self.repo)
            self.repo.save_decision(decision)
            if cached is not None:
                self.repo.save_result(s.id, cached)
                s.budget_consumed["cache_hits"] += 1
                continue
            if decision.decision not in {"EXECUTE", "REPLICATE"}:
                return self.stop("Final confirmation cannot fit remaining budget; evidence insufficient")
            self.transition("EXECUTING", recovery=True)
            s.budget_consumed["experiments"] += 1
            self.repo.event(s.id, "execution_reserved", {"experiment_id": spec.id, "fingerprint": fingerprint(spec), "recovery": True})
            self.checkpoint()
            result = execute(spec, Path(self.config.artifact_dir)/s.id/"experiments",
                             timeout=min(b.experiment_timeout,b.wall_seconds-s.budget_consumed["wall_seconds"]),
                             memory_mb=b.memory_mb, isolation=self.config.execution_isolation)
            if result.status == "COMPLETED" and not self.repo.verified(result):
                result = result.model_copy(update={"status":"FAILED","metrics":{},"error_details":"Critical numerical or artifact integrity failure"})
            self.repo.save_result(s.id,result)
            self.repo.event(s.id,"experiment_completed",{"result_id":result.id,"status":result.status,"recovery":True})
            if result.status != "COMPLETED":
                return self.stop("Execution failure during resumed final confirmation",failed=True)
        if self.complete_if_satisfied():
            return s
        return self.stop("Final confirmatory batch completed; evidence insufficient for declared success criteria")

    def run(self, session_id):
        lock = getattr(self.repo, "session_lock", None)
        with lock(session_id) if lock else nullcontext():
            return self._run(session_id)

    def _run(self, session_id):
        self.session = self.repo.get_session(session_id)
        if self.session.state in TERMINAL:
            return self.session
        elapsed_since_start = (datetime.now(timezone.utc)-datetime.fromisoformat(self.session.started_at)).total_seconds()
        self._base_wall = max(float(self.session.budget_consumed["wall_seconds"]), elapsed_since_start)
        self._clock = time.monotonic()
        s, b = self.session, self.session.budget_configuration
        s.termination_reason = None
        try:
            if self.repo.hypotheses(s.id) and s.state not in {"INITIALIZED", "REPLANNING"}:
                self.transition("REPLANNING", recovery=True)
            if not self.repo.hypotheses(s.id):
                if "exploratory" not in self.config.objective.constraints.get("allowed_phases", ["exploratory", "confirmatory"]):
                    return self.stop("No viable experiments: the objective disallows the initial exploratory phase")
                self.transition("HYPOTHESIZING", recovery=s.state != "INITIALIZED")
                batch = self.ask(HypothesisBatch, "Generate two competing falsifiable hypotheses. One should predict when correction helps, another when it may fail. Set expected_delta_direction only for a clear negative or positive prediction for delta_brier. Do not claim support before experiments.", self.context(), hypotheses_schema(), lambda payload: decode_hypotheses(payload, s.id))
                for h in batch.hypotheses:
                    # Identity, ownership and timestamps are application metadata,
                    # never facts delegated to model generation.
                    h.id = uid()
                    h.session_id = s.id
                    h.status = "PROPOSED"
                    h.created_at = now()
                    self.repo.save_hypothesis(h)
            self.reconcile_interrupted()
            for stored in self.repo.results(s.id):
                if stored.status == "COMPLETED" and not self.repo.verified(stored):
                    return self.stop(f"Critical evidence integrity failure: result {stored.id} cannot be verified", failed=True)
                if stored.status == "FAILED":
                    return self.stop(f"Execution failure already recorded for experiment {stored.experiment_id}", failed=True)
            confirmations = self.repo.events(s.id, "confirmation_batch")
            if confirmations:
                expected = set(confirmations[-1]["payload"]["experiment_ids"])
                return self.continue_confirmation(expected)
            if self.complete_if_satisfied():
                return s
            while s.iteration_count < b.max_rounds:
                self.budget_check()
                if s.budget_consumed["experiments"] >= b.max_experiments:
                    return self.stop("Budget exhausted: maximum experiments")
                s.iteration_count += 1
                self.transition("PLANNING")
                task = f"Propose at most {b.max_candidates} registered prior_correction experiments that best test or challenge the active hypotheses. Use the exact hypothesis IDs and permitted parameter values. Choose a new seed or a changed authorized condition rather than repeating a measured condition+seed. To establish reproducibility, deliberately replicate conditions using different seeds. Negative delta_brier means improvement; do not assume correction always helps. Follow latest_research_direction unless the evidence gives a specific reason to revise it. Confirmation is one final held-out batch. Each selected condition requires at least {b.minimum_replications} independent reserved seeds with identical parameters within that condition; the entire batch ends planning."
                observations = observed_specs(self.repo, s.id)
                exploratory = {(p.parameters.model_dump_json(), p.seed) for p, _ in observations if p.phase == "exploratory"}
                observed_conditions = {parameters for parameters, _ in exploratory}
                criteria = self.config.objective.success_criteria
                exploration_met = (len(exploratory) >= criteria.get("minimum_exploratory_experiments", 1)
                                   and len(observed_conditions) >= criteria.get("minimum_conditions", 1))
                explicit_criteria = bool(set(criteria)-{"minimum_replications"})
                confirmation_requested = explicit_criteria and criteria.get("require_confirmation", True)
                require_final = confirmation_requested and exploration_met
                final_groups = criteria.get("minimum_confirmatory_groups", 1)
                required_final_size = final_groups*b.minimum_replications
                confirmation_stage_allowed = not explicit_criteria or confirmation_requested and exploration_met
                can_confirm = confirmation_stage_allowed and bool(observations) and b.max_candidates >= required_final_size and b.max_experiments-s.budget_consumed["experiments"] >= required_final_size
                if require_final and (not can_confirm or "confirmatory" not in self.config.objective.constraints.get("allowed_phases", ["exploratory", "confirmatory"])):
                    return self.stop("No viable final confirmation fits the remaining authorized experiment and candidate budgets; evidence insufficient")
                try:
                    output_schema = planning_schema(self.config, self.repo.hypotheses(s.id), can_confirm,
                                                    bool(observations), self.repo.specs(s.id), require_final)
                except NoViablePlan as exc:
                    return self.stop("No viable experiments: " + str(exc) + "; evidence insufficient")
                if require_final:
                    task += f" PROTOCOL PHASE: FINAL CONFIRMATION. The predefined exploration target is met. Return one final held-out batch covering {final_groups} distinct parameter conditions, each with {b.minimum_replications} distinct reserved confirmation seeds. All records must have phase confirmatory. Parameters must be identical WITHIN each condition's independent replications. Seeds can be paired across different conditions. Do not propose exploratory seeds or further exploration. Choose the authorized conditions to confirm from measured exploratory evidence."
                    self.repo.event(s.id,"confirmation_strategy",{"reason":"Predeclared exploratory target met", "minimum_replications":b.minimum_replications,"minimum_confirmatory_groups":final_groups})
                elif not can_confirm:
                    task += " Only exploratory phase is currently permitted."
                if s.no_progress_count:
                    task += " LOOP WARNING: prior planning added no measurements. Change the seed or conditions materially; a repeated rejected plan without changed constraints is not new evidence."
                try:
                    def decode_and_check(payload):
                        decoded = decode_plan(payload)
                        parsed_plan = Plan.model_validate(decoded)
                        if require_final:
                            validate_confirmation_batch(parsed_plan.candidates,self.config)
                        elif explicit_criteria and any(candidate.phase == "confirmatory" for candidate in parsed_plan.candidates):
                            raise ValueError("The predefined protocol is still exploratory; do not consume held-out confirmation seeds before the exploratory target is met")
                        return decoded
                    plan = self.ask(Plan, task, self.context(), output_schema, decode_and_check)
                except ValueError as exc:
                    self.repo.event(s.id, "planning_error", {"error": str(exc)})
                    plan = Plan(candidates=[])
                self.transition("VALIDATING")
                ids = {h.id for h in self.repo.hypotheses(s.id)}
                candidates = plan.candidates[:b.max_candidates]
                prior_actions = self.repo.specs(s.id)
                for event in self.repo.events(s.id, "proposal"):
                    try:
                        prior_actions.append(ExperimentSpec.model_validate(event["payload"]))
                    except ValueError:
                        continue
                repeated = repeated_actions(candidates, prior_actions)
                if repeated:
                    self.repo.event(s.id, "reasoning_loop_warning", {"experiment_ids": repeated,
                                    "reason": "Repeated normalized scientific actions; change conditions or independent seed"})
                confirmation = [e for e in candidates if e.phase == "confirmatory"]
                if confirmation:
                    try:
                        if len(confirmation) != len(candidates) or not observations or len(confirmation) > b.max_experiments-s.budget_consumed["experiments"]:
                            raise ValueError("Final confirmation must be one fully budgeted held-out batch after exploration")
                        validate_confirmation_batch(confirmation,self.config)
                    except ValueError as exc:
                        for e in confirmation:
                            self.repo.event(s.id, "invalid_confirmation", {"experiment_id": e.id, "reason": str(exc)})
                        candidates = []
                ranked = []
                for e in candidates:
                    # Replication-group identity is provenance metadata, not a
                    # reason to discard a scientifically valid independent seed.
                    for prior, _ in observed_specs(self.repo, s.id):
                        if prior.parameters == e.parameters and prior.replicate_group:
                            e.replicate_group = prior.replicate_group
                            break
                    self.repo.event(s.id, "proposal", e.model_dump(mode="json"))
                    try:
                        validate_proposal(e, self.config, ids)
                        if any(p.id == e.id for p in self.repo.specs(s.id)):
                            e = e.model_copy(update={"id": uid()})
                        self.repo.save_spec(s.id, e)
                        d, cached = decide(e, s, self.config, self.repo)
                        ranked.append((e, d, cached))
                    except ValueError as exc:
                        from slothlab.schemas import LazyLoopDecision
                        self.repo.save_decision(LazyLoopDecision(experiment_id=e.id, session_id=s.id, decision="REJECT", reason=str(exc)))
                if s.mode == "lazyloop":
                    ranked.sort(key=lambda item: item[1].priority_score, reverse=True)
                if confirmation and ranked:
                    self.repo.event(s.id, "confirmation_batch", {"experiment_ids": [e.id for e, _, _ in ranked]})
                progress = 0
                actions = []
                information_values = []
                for e, d, cached in ranked:
                    self.budget_check()
                    # Recheck budgets/cache after earlier candidates execute.
                    d, cached = decide(e, s, self.config, self.repo)
                    self.repo.save_decision(d)
                    actions.append(d.decision)
                    self.repo.event(s.id, "action_trace", {"experiment_id": e.id,
                                    "signature": action_signature(e), "action": d.decision,
                                    "evidence_ids": [r.id for r in self.repo.results(s.id)]})
                    if d.decision == "REUSE":
                        already_known = {r.id for r in self.repo.results(s.id)}
                        self.repo.save_result(s.id, cached)
                        if cached.id not in already_known:
                            progress += 1
                        s.budget_consumed["cache_hits"] += 1
                        self.checkpoint()
                        continue
                    if d.decision not in {"EXECUTE", "REPLICATE"}:
                        continue
                    for hypothesis in self.repo.hypotheses(s.id):
                        if hypothesis.id == e.hypothesis_id:
                            hypothesis.status = "TESTING"
                            self.repo.save_hypothesis(hypothesis)
                    self.transition("EXECUTING")
                    s.budget_consumed["experiments"] += 1
                    self.repo.event(s.id, "execution_reserved", {"experiment_id": e.id, "fingerprint": fingerprint(e)})
                    self.checkpoint()
                    timeout = min(b.experiment_timeout, b.wall_seconds-s.budget_consumed["wall_seconds"])
                    result = execute(e, Path(self.config.artifact_dir)/s.id/"experiments", timeout=timeout, memory_mb=b.memory_mb, isolation=self.config.execution_isolation)
                    if result.status == "COMPLETED" and not self.repo.verified(result):
                        result = result.model_copy(update={"status":"FAILED","metrics":{},"error_details":"Critical numerical or artifact integrity failure"})
                    self.repo.save_result(s.id, result)
                    self.repo.event(s.id, "experiment_completed", {"result_id": result.id, "status": result.status})
                    self.checkpoint()
                    if result.status == "FAILED":
                        return self.stop("Execution failure: " + str(result.error_details), failed=True)
                    progress += 1
                    information_values.append(d.score_components.get("information", 1.0))
                if progress:
                    self.transition("ANALYZING")
                    interpretation = self.ask(Analysis, "Interpret recorded evidence. Cite result IDs for each assessment. Statuses are provisional; numerical checks determine actual status. Revise next_direction when observed deltas conflict with predictions. When a hypothesis needs revision, supply revised_statement, revised_prediction and revised_direction, grounded in the cited results; do not claim the revised hypothesis is already proven.", self.context(), _compact(Analysis.model_json_schema()))
                    self.apply_analysis(interpretation)
                s.no_progress_count = 0 if progress else s.no_progress_count+1
                low_information = bool(information_values) and max(information_values) < 0.25
                previous_low = s.budget_consumed.get("low_information_rounds", 0)
                s.budget_consumed["low_information_rounds"] = previous_low+1 if low_information else 0
                if low_information:
                    self.repo.event(s.id,"low_information_warning",{"rounds":previous_low+1,
                                    "reason":"The replication target is already met and measured directions are consistent; consider a new condition"})
                self.checkpoint()
                if self.complete_if_satisfied():
                    return s
                if confirmation and progress:
                    return self.stop("Final confirmatory batch completed; consult deterministic quality assessment; hypothesis conclusions remain provisional")
                if actions and all(action == "DEFER" for action in actions):
                    return self.stop("No viable experiments fit the remaining resource constraints")
                if s.mode == "lazyloop" and s.no_progress_count >= b.no_progress_rounds:
                    return self.stop("Repeated unproductive planning: evidence insufficient")
                if s.mode == "lazyloop" and s.budget_consumed["low_information_rounds"] >= b.no_progress_rounds:
                    return self.stop("Estimated information remained low after the configured replication target; evidence insufficient for broader claims")
                self.transition("REPLANNING")
            return self.stop("Maximum planning rounds reached: evidence insufficient")
        except BudgetExhausted as exc:
            return self.stop(str(exc))
        except Exception as exc:
            self.repo.event(s.id, "error", {"type": type(exc).__name__, "message": str(exc)})
            self.stop(f"Execution failure: {exc}", failed=True)
            raise
        finally:
            self.checkpoint()
