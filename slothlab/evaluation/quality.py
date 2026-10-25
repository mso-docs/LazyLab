"""Evidence integrity, replication, controls and claim calibration without model grading."""
from collections import defaultdict
import json
import math
from statistics import mean, stdev

from slothlab.schemas import ExperimentSpec, ExperimentResult

EPSILON = 1e-10


def interval(values, confidence=0.95):
    """Student-t interval across independent seeds; None when variance is unidentified."""
    values = list(values)
    if len(values) < 2:
        return None
    from scipy.stats import t
    half = float(t.ppf((1+confidence)/2, len(values)-1))*stdev(values)/math.sqrt(len(values))
    return [mean(values)-half, mean(values)+half]


def condition_key(parameters):
    return json.dumps(parameters.model_dump() if hasattr(parameters, 'model_dump') else parameters, sort_keys=True, separators=(',', ':'))


def assess_quality(specs: list[ExperimentSpec], results: list[ExperimentResult], minimum_replications: int = 3,
                   hypotheses=None, interpretations=None, verified_assessments=None) -> dict:
    """Explicit rubric; numerical scores are diagnostics, never a universal truth score.

    The legacy quality_score remains coverage for backwards-compatible artifacts.
    scientific_quality_score additionally audits measurement integrity, the identity
    control where applicable and supported/contradicted claim provenance.
    """
    from slothlab.memory.repository import Repository
    by_id = {spec.id: spec for spec in specs}
    groups = defaultdict(list)
    valid, invalid_ids = [], []
    for result in results:
        spec = by_id.get(result.experiment_id)
        if spec is None or not Repository.verified(result):
            invalid_ids.append(result.id)
            continue
        valid.append((spec, result))
        key = json.dumps({'parameters': spec.parameters.model_dump(), 'replicate_group': spec.replicate_group}, sort_keys=True)
        groups[key].append((spec, result))
    summaries, control_checks = [], []
    confirmed = 0
    for key, observations in groups.items():
        exploratory_seeds = {spec.seed for spec, _ in observations if spec.phase == 'exploratory'}
        independent = {}
        for spec, result in observations:
            if spec.phase == 'confirmatory' and spec.seed not in exploratory_seeds:
                independent.setdefault(spec.seed, result)
            if abs(spec.parameters.train_prevalence-spec.parameters.evaluation_prevalence) <= EPSILON:
                control_checks.append({'result_id': result.id, 'check': 'no_shift_identity',
                                       'passed': abs(result.metrics['delta_brier']) <= EPSILON and abs(result.metrics['delta_log_loss']) <= EPSILON})
        deltas = [result.metrics['delta_brier'] for result in independent.values()]
        direction = 'INSUFFICIENT_EVIDENCE'
        if len(deltas) >= max(3, minimum_replications):
            if all(delta < -EPSILON for delta in deltas):
                direction = 'CONSISTENT_IMPROVEMENT'
                confirmed += 1
            elif all(delta > EPSILON for delta in deltas):
                direction = 'CONSISTENT_REGRESSION'
                confirmed += 1
            else:
                direction = 'MIXED_OR_ZERO_EFFECT'
        summaries.append({
            **json.loads(key),
            'independent_confirmatory_seeds': sorted(independent),
            'confirmatory_result_ids': [r.id for r in independent.values()],
            'confirmatory_mean_delta_brier': mean(deltas) if deltas else None,
            'confirmatory_std_delta_brier': stdev(deltas) if len(deltas) > 1 else None,
            'confirmatory_delta_brier_ci95': interval(deltas),
            'protocol_assessment': direction,
            'exploratory_result_ids': [r.id for s, r in observations if s.phase == 'exploratory'],
            'all_result_ids': [r.id for _, r in observations],
        })
    coverage = min(1.0, len({s.seed for s, _ in valid}) / max(3, minimum_replications))
    replication = min(1.0, sum(len(g['independent_confirmatory_seeds']) for g in summaries) / max(3, minimum_replications))
    score = (coverage + replication) / 2 if valid else 0.0
    integrity = len(valid)/len(results) if results else 0.0
    controls = sum(c['passed'] for c in control_checks)/len(control_checks) if control_checks else None
    valid_ids = {r.id for _, r in valid}
    assessments = {a['hypothesis_id']: a for a in (verified_assessments or [])}
    claims = []
    for h in hypotheses or []:
        h = h.model_dump() if hasattr(h, 'model_dump') else h
        if h['status'] not in {'SUPPORTED', 'CONTRADICTED'}:
            claims.append({'hypothesis_id': h['id'], 'status': h['status'], 'justified': True, 'reason': 'No established directional claim asserted'})
            continue
        assessment = assessments.get(h['id'], {})
        refs = assessment.get('evidence_ids', [])
        justified = bool(assessment.get('verified_claim')) and assessment.get('status') == h['status'] and bool(refs) and all(i in valid_ids for i in refs)
        claims.append({'hypothesis_id': h['id'], 'status': h['status'], 'justified': justified,
                       'evidence_ids': refs, 'reason': 'Deterministic assessment and valid result references' if justified else 'Established claim lacks a matching deterministic evidence receipt'})
    claim_score = sum(c['justified'] for c in claims)/len(claims) if claims else None
    proposed_invalid = sum(not a.get('references_valid', False) for a in (interpretations or []))
    rubric = {'measurement_integrity': {'weight': .30, 'score': integrity},
              'independent_confirmation': {'weight': .30, 'score': replication},
              'controlled_expected_behavior': {'weight': .20, 'score': controls},
              'claim_evidence_calibration': {'weight': .20, 'score': claim_score}}
    denominator = sum(c['weight'] for c in rubric.values() if c['score'] is not None)
    scientific_score = sum(c['weight']*c['score'] for c in rubric.values() if c['score'] is not None)/denominator if denominator else 0.0
    if not valid:
        scientific_score = 0.0
    return {
        'quality_score': score,
        'quality_score_definition': 'Equal-weight independent-seed and reserved-confirmatory-seed coverage, capped at minimum_replications. Coverage is not scientific truth.',
        'scientific_quality_score': scientific_score,
        'scientific_quality_score_definition': 'Predeclared weighted diagnostic: measurement integrity .30, independent confirmation .30, applicable no-shift identity controls .20, claim/evidence calibration .20; inapplicable components are excluded and remaining weights renormalized. No valid measurements scores zero.',
        'rubric': rubric,
        'valid_measurements': len(valid), 'invalid_result_ids': invalid_ids,
        'scientific_source_versions':sorted({r.environment_metadata['source_sha256'] for _,r in valid if r.environment_metadata.get('source_sha256')}),
        'independent_seed_count': len({s.seed for s, _ in valid}),
        'protocol_supported_groups': confirmed, 'groups': summaries,
        'control_checks': control_checks, 'claim_checks': claims,
        'unjustified_established_claims': sum(not c['justified'] for c in claims),
        'model_interpretations_with_invalid_references': proposed_invalid,
        'limitations': [
            'Oracle evaluation prevalence is supplied; deployment prevalence estimation is not evaluated.',
            'Scores are a transparent finite benchmark rubric, not a general measure of scientific truth.',
            'Student-t intervals assume independent seeds sampled from the generator distribution; no multiplicity correction is applied.',
            'Consistent replicated effects alone do not establish a general law or statistical significance.',
            'Reusing an exploratory seed invalidates its confirmatory independence.',
        ],
    }


scientific_quality = assess_quality
