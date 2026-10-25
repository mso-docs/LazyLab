"""Observational terminal checks against a recorded final-batch obligation.

This never predicts useful future research and never changes a stopping decision.
It can identify only an unfinished, already-persisted authorized protocol whose
remaining declared estimates fit the remaining hard limits.
"""
from slothlab.lazyloop.controller import validate_proposal

SCOPE = "known authorized final-batch protocol only"


def termination_audit(repo, session, config):
    def outcome(premature, remaining, reason):
        return {"known_protocol_premature_stop": premature, "scope": SCOPE,
                "remaining_confirmation_ids": sorted(remaining), "reason": reason}

    batches = repo.events(session.id, "confirmation_batch")
    if not batches:
        return outcome(False, [], "No persisted final confirmation batch exists; omitted future research is not inferred")
    expected = set(batches[-1]["payload"].get("experiment_ids", []))
    results = [result for result in repo.results(session.id) if repo.verified(result)]
    completed = {result.experiment_id for result in results}
    valid_result_ids = {result.id for result in results}
    # Exact reuse satisfies a proposal's measurement obligation without changing
    # the stored result's original experiment ID or inventing another replication.
    for decision in repo.decisions(session.id):
        if (decision.decision == "REUSE" and decision.evidence_references
                and all(reference in valid_result_ids for reference in decision.evidence_references)):
            completed.add(decision.experiment_id)
    remaining = expected-completed
    if not remaining:
        return outcome(False, [], "All recorded final confirmation proposals have verified completed evidence")
    reason = (session.termination_reason or "").lower()
    if session.state == "FAILED" or "integrity failure" in reason or "critical failure" in reason:
        return outcome(False, remaining, "Critical execution or integrity failure is a justified terminal boundary")
    budget, used = session.budget_configuration, session.budget_consumed
    try:
        count_left = budget.max_experiments-used.get("experiments", 0)
        wall_left = budget.wall_seconds-used.get("wall_seconds", 0.0)
        tokens_left = budget.max_tokens-used.get("token_reservations", 0)
        rounds_left = budget.max_rounds-session.iteration_count
        if count_left < len(remaining) or wall_left <= 0 or tokens_left <= 0 or rounds_left <= 0 or "budget exhausted" in reason:
            return outcome(False, remaining, "A hard execution, wall, token or planning budget justifies termination")
        hypotheses = {hypothesis.id for hypothesis in repo.hypotheses(session.id)}
        pending = [repo.get_spec(identity) for identity in remaining]
        for spec in pending:
            if spec.phase != "confirmatory":
                return outcome(False, remaining, "The remaining record does not describe an authorized final confirmation proposal")
            validate_proposal(spec, config, hypotheses)
        if any(spec.estimated_compute_seconds > budget.experiment_timeout for spec in pending) or sum(spec.estimated_compute_seconds for spec in pending) > wall_left:
            return outcome(False, remaining, "The remaining final batch cannot fit its declared execution-time estimates")
    except (KeyError, ValueError, TypeError, AttributeError):
        return outcome(False, remaining, "Remaining protocol authorization or resource estimates cannot be independently established")
    return outcome(True, remaining,
                   "A soft/completion decision left recorded authorized final confirmation work unfinished while declared resource and planning limits allowed it; no scientific benefit is predicted")
