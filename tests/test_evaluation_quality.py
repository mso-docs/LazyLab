import json
from pathlib import Path
import pytest
from slothlab.schemas import ExperimentSpec,ExperimentResult,Hypothesis
from slothlab.evaluation.quality import assess_quality,interval
from slothlab.evaluation.metrics import summarize_comparison


def measurement(spec,delta=-.1):
    return ExperimentResult(experiment_id=spec.id,fingerprint='fixture',status='COMPLETED',runtime_seconds=.1,
        metrics={'baseline_brier':.2,'corrected_brier':.2+delta,'delta_brier':delta,'baseline_log_loss':.5,'corrected_log_loss':.5+delta,'delta_log_loss':delta})


def test_quality_audits_identity_controls_and_claim_receipts():
    spec=ExperimentSpec(hypothesis_id='h',seed=1,rationale='test',parameters={'train_prevalence':.5,'evaluation_prevalence':.5})
    result=measurement(spec,0)
    h=Hypothesis(id='h',session_id='s',statement='test',falsifiable_prediction='negative',status='SUPPORTED',expected_delta_direction='negative')
    quality=assess_quality([spec],[result],hypotheses=[h])
    assert quality['control_checks'][0]['passed'] is True
    assert quality['unjustified_established_claims']==1
    assert quality['rubric']['claim_evidence_calibration']['score']==0
    corrupted=measurement(spec,-.1)
    quality=assess_quality([spec],[corrupted],hypotheses=[h])
    assert quality['control_checks'][0]['passed'] is False


def test_independent_confirmation_interval_and_duplicate_seeds():
    specs=[ExperimentSpec(hypothesis_id='h',seed=seed,phase='confirmatory',replicate_group='same',rationale='test') for seed in [1,2,3,3]]
    results=[measurement(spec,-.1) for spec in specs]
    quality=assess_quality(specs,results)
    assert quality['groups'][0]['independent_confirmatory_seeds']==[1,2,3]
    assert quality['groups'][0]['confirmatory_delta_brier_ci95']==[-.1,-.1]
    assert interval([1]) is None
    assert interval([1,2,3])[0]<1
    assert quality['scientific_quality_score']==1


def rows(repeats=3):
    return [{'scenario':'test','trial':trial,'mode':mode,'state':'STOPPED','wall_seconds':2 if mode=='baseline' else 1,
             'experiment_count':6 if mode=='baseline' else 3,'model_tokens':None,'quality':{'scientific_quality_score':1}} for trial in range(repeats) for mode in ['baseline','cache_only','lazyloop']]


def test_quality_preservation_needs_repeated_successful_autonomous_pairs():
    assert summarize_comparison(rows(1))[0]['verdict']=='INSUFFICIENT_REPEATED_EVIDENCE'
    summaries=summarize_comparison(rows())
    assert all(s['verdict']=='QUALITY_NONINFERIOR_UNDER_RUBRIC' for s in summaries)
    assert summaries[0]['mean_execution_fraction_saved']==.5
    assert summaries[0]['mean_token_fraction_saved'] is None
    assert summarize_comparison(rows(),replay=True)[0]['verdict']=='CONTROLLER_REPLAY_ONLY'
    failed=rows();failed[0]['state']='FAILED'
    assert summarize_comparison(failed)[0]['verdict']=='INSUFFICIENT_REPEATED_EVIDENCE'


def test_quality_degradation_never_counts_as_optimization_success():
    values=rows()
    for row in values:
        if row['mode']=='lazyloop':row['quality']['scientific_quality_score']=.5
    assert summarize_comparison(values)[1]['verdict']=='QUALITY_DEGRADED_UNDER_RUBRIC'


def test_multiple_scenarios_are_not_substituted_for_repeat_trials():
    values=[]
    for i in range(4):
        values.extend([dict(r,scenario=str(i)) for r in rows(1)])
    assert summarize_comparison(values)[0]['verdict']=='INSUFFICIENT_REPEATED_EVIDENCE'


def test_compute_benefit_requires_actual_independent_confirmation():
    values=rows()
    assert summarize_comparison(values)[0]['research_hypothesis_verdict']=='INSUFFICIENT_CONFIRMATORY_EVIDENCE'
    for row in values:
        row['quality']['groups']=[{'independent_confirmatory_seeds':[100,101,102]}]
    assert summarize_comparison(values)[0]['research_hypothesis_verdict']=='COMPUTE_REDUCTION_WITH_PRESERVED_RUBRIC_QUALITY'


def test_mismatched_protocol_versions_cannot_support_paired_claims():
    values=rows()
    for row in values:
        row['scientific_source_versions']=['source-a' if row['mode']=='baseline' else 'source-b']
    summary=summarize_comparison(values)[0]
    assert summary['valid_pairs']==0
    assert summary['verdict']=='INSUFFICIENT_REPEATED_EVIDENCE'


def test_paired_model_weight_identity_does_not_invent_legacy_provenance():
    values=rows()
    assert summarize_comparison(values)[0]['model_weights_verified'] is False
    for row in values:row['model_digest']='same-digest'
    assert summarize_comparison(values)[0]['model_weights_verified'] is True
    values[1]['model_digest']='different-digest'
    summary=summarize_comparison(values)[0]
    assert summary['valid_pairs']==2
    assert summary['failed_or_missing_pairs'][0]['reason']=='Mismatched known model weight digests'
