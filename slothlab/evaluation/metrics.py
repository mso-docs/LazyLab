"""Paired computational and scientific comparisons from recorded telemetry."""
from collections import defaultdict
from statistics import mean
from slothlab.evaluation.quality import interval


def summarize_comparison(rows, *, replay=False, quality_tolerance=0.05):
    pairs=defaultdict(dict)
    for row in rows:
        pairs[(row['scenario'],row['trial'])][row['mode']]=row
    summaries=[]
    for mode in ('cache_only','lazyloop'):
        quality_deltas=[]; savings=[]; token_savings=[]; execution_savings=[]; valid_pairs=0
        failures=[]
        sufficient_confirmation=True
        all_model_weights_verified=True
        scenario_deltas=defaultdict(list)
        for (scenario,trial), arms in pairs.items():
            baseline=arms.get('baseline'); candidate=arms.get(mode)
            if not baseline or not candidate or baseline.get('state')=='FAILED' or candidate.get('state')=='FAILED':
                failures.append({'scenario':scenario,'trial':trial})
                continue
            if baseline.get('constraints_signature') != candidate.get('constraints_signature'):
                failures.append({'scenario':scenario,'trial':trial,'reason':'Mismatched scenario/model/budget/seed constraints'})
                continue
            if 'scientific_source_versions' in baseline and (len(baseline['scientific_source_versions'])!=1 or baseline['scientific_source_versions']!=candidate.get('scientific_source_versions')):
                failures.append({'scenario':scenario,'trial':trial,'reason':'Missing, mixed or mismatched scientific source versions'})
                continue
            base_digest=baseline.get('model_digest');candidate_digest=candidate.get('model_digest')
            if base_digest and candidate_digest and base_digest!=candidate_digest:
                failures.append({'scenario':scenario,'trial':trial,'reason':'Mismatched known model weight digests'})
                continue
            all_model_weights_verified &= bool(base_digest and candidate_digest)
            valid_pairs+=1
            for arm in (baseline,candidate):
                sufficient_confirmation &= any(len(g.get('independent_confirmatory_seeds',[]))>=3 for g in arm['quality'].get('groups',[]))
            delta=candidate['quality']['scientific_quality_score']-baseline['quality']['scientific_quality_score']
            quality_deltas.append(delta)
            scenario_deltas[scenario].append(delta)
            if baseline['wall_seconds']>0:
                savings.append(1-candidate['wall_seconds']/baseline['wall_seconds'])
            if baseline['experiment_count']>0:
                execution_savings.append(1-candidate['experiment_count']/baseline['experiment_count'])
            if baseline['model_tokens'] and candidate['model_tokens'] is not None:
                token_savings.append(1-candidate['model_tokens']/baseline['model_tokens'])
        ci=interval(quality_deltas)
        if replay:
            verdict='CONTROLLER_REPLAY_ONLY'
        elif failures or not scenario_deltas or any(len(values)<3 for values in scenario_deltas.values()):
            verdict='INSUFFICIENT_REPEATED_EVIDENCE'
        elif all(interval(values)[0]>=-quality_tolerance for values in scenario_deltas.values()):
            verdict='QUALITY_NONINFERIOR_UNDER_RUBRIC'
        elif any(interval(values)[1]<-quality_tolerance for values in scenario_deltas.values()):
            verdict='QUALITY_DEGRADED_UNDER_RUBRIC'
        else:
            verdict='QUALITY_PRESERVATION_UNRESOLVED'
        wall_ci=interval(savings)
        tokens_ci=interval(token_savings)
        if replay:
            hypothesis_verdict='NOT_AN_AUTONOMY_EVALUATION'
        elif verdict=='QUALITY_DEGRADED_UNDER_RUBRIC':
            hypothesis_verdict='FAILED_SCIENTIFIC_QUALITY'
        elif verdict!='QUALITY_NONINFERIOR_UNDER_RUBRIC':
            hypothesis_verdict='INSUFFICIENT_OR_UNRESOLVED_REPEATED_EVIDENCE'
        elif not sufficient_confirmation:
            hypothesis_verdict='INSUFFICIENT_CONFIRMATORY_EVIDENCE'
        elif (wall_ci is not None and wall_ci[0]>0) or (tokens_ci is not None and tokens_ci[0]>0):
            hypothesis_verdict='COMPUTE_REDUCTION_WITH_PRESERVED_RUBRIC_QUALITY'
        else:
            hypothesis_verdict='NO_ESTABLISHED_COMPUTE_BENEFIT'
        summaries.append({'mode':mode,'valid_pairs':valid_pairs,'failed_or_missing_pairs':failures,
                          'mean_quality_delta':mean(quality_deltas) if quality_deltas else None,'quality_delta_ci95':ci,
                          'quality_noninferiority_tolerance':quality_tolerance,
                          'per_scenario_quality':{name:{'paired_trials':len(values),'mean_delta':mean(values),'delta_ci95':interval(values)} for name,values in scenario_deltas.items()},
                          'mean_wall_fraction_saved':mean(savings) if savings else None,'wall_fraction_saved_ci95':wall_ci,
                          'mean_execution_fraction_saved':mean(execution_savings) if execution_savings else None,
                          'mean_token_fraction_saved':mean(token_savings) if token_savings else None,'token_fraction_saved_ci95':tokens_ci,
                          'model_weights_verified':None if replay else all_model_weights_verified and valid_pairs>0,
                          'model_identity_note':('No inference was used in replay; model weight pinning is not applicable' if replay else ('Known weight digests matched across all valid pairs' if all_model_weights_verified and valid_pairs>0 else 'At least one arm lacks a recorded weight digest; model tags are not cryptographic weight pinning')),
                          'sufficient_confirmatory_coverage':sufficient_confirmation,'research_hypothesis_verdict':hypothesis_verdict,
                          'verdict':verdict})
    return summaries
