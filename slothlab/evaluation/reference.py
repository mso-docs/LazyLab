"""Independent registered-science reference grid, never supplied to the planner."""
import json
from pathlib import Path
import time

from slothlab.schemas import Parameters, ResearchSession, Hypothesis, ExperimentSpec, now
from slothlab.memory.repository import Repository
from slothlab.memory.factory import open_repository
from slothlab.experiments.executor import execute
from slothlab.evaluation.quality import condition_key, interval
from statistics import mean, stdev


def reference_seeds(config, count):
    excluded = set(config.exploratory_seeds) | set(config.confirmatory_seeds)
    chosen = []
    for seed in range(2**31-1, -1, -1):
        if seed not in excluded:
            chosen.append(seed)
        if len(chosen) == count:
            return chosen
    raise ValueError('Unable to reserve independent reference seeds')


def reference_conditions(config, max_conditions):
    if not 1 <= max_conditions <= 100:
        raise ValueError('max_conditions must be between 1 and 100')
    keys = sorted(config.objective.permitted_parameters)
    values = [config.objective.permitted_parameters[k] for k in keys]
    total = 1
    for options in values:
        total *= len(options)
    targets = {round(i*(total-1)/max(1,min(max_conditions,total)-1)) for i in range(min(max_conditions,total))}
    rows = []
    for index in sorted(targets):
        remainder=index
        combination=[]
        for options in reversed(values):
            remainder,offset=divmod(remainder,len(options))
            combination.append(options[offset])
        rows.append(Parameters(**dict(zip(keys,reversed(combination)))))
    return rows


def generate_reference_grid(config, output_dir, *, max_conditions=4, seeds_per_condition=3):
    if not 3 <= seeds_per_condition <= 30:
        raise ValueError('seeds_per_condition must be between 3 and 30')
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    db = output/('reference.jsondoc' if config.storage_backend=='document' else 'reference.sqlite')
    if db.exists():
        raise ValueError('Reference generation requires fresh storage')
    seeds = reference_seeds(config, seeds_per_condition)
    conditions = reference_conditions(config, max_conditions)
    if len(conditions)*seeds_per_condition > config.budget.max_experiments:
        raise ValueError('Reference grid exceeds configured max_experiments; explicitly raise its budget or reduce the grid')
    try:
        with (output/'.reference.lock').open('x') as lock:
            lock.write(now())
    except FileExistsError as exc:
        raise ValueError('Reference output is already claimed; use fresh storage') from exc
    rows, started = [], time.monotonic()
    with open_repository(db,config.storage_backend) as repo:
        repo.save_objective(config.objective)
        session = ResearchSession(objective_id=config.objective.id, model_name='none: independent reference grid', mode='baseline', budget_configuration=config.budget)
        repo.save_session(session)
        repo.event(session.id,'reference_protocol',{'planner_access': False, 'seeds':seeds,'conditions':[p.model_dump() for p in conditions]})
        hypothesis = Hypothesis(session_id=session.id,statement='Independent characterization of oracle prior correction',falsifiable_prediction='Measured delta sign, variance and no-shift identity are retained without assuming improvement')
        repo.save_hypothesis(hypothesis)
        for condition_index, params in enumerate(conditions):
            measured = []
            for seed in seeds:
                if time.monotonic()-started >= config.budget.wall_seconds:
                    break
                spec = ExperimentSpec(hypothesis_id=hypothesis.id,seed=seed,phase='confirmatory',parameters=params,
                                      replicate_group=f'reference-{condition_index}',rationale='Independent reference-only trial; withheld from agent planning')
                repo.save_spec(session.id,spec)
                session.budget_consumed['experiments'] += 1
                repo.event(session.id,'execution_reserved',{'experiment_id':spec.id,'reference_only':True})
                repo.save_session(session)
                result = execute(spec,output/session.id/'experiments',timeout=min(config.budget.experiment_timeout,max(.001,config.budget.wall_seconds-(time.monotonic()-started))),memory_mb=config.budget.memory_mb,isolation=getattr(config,"execution_isolation","auto"))
                repo.save_result(session.id,result)
                if repo.verified(result):
                    measured.append(result)
            deltas=[r.metrics['delta_brier'] for r in measured]
            rows.append({'condition_key':condition_key(params),'parameters':params.model_dump(),'seeds':seeds,
                         'result_ids':[r.id for r in measured],'completed':len(measured),
                         'scientific_source_versions':sorted({r.environment_metadata['source_sha256'] for r in measured if r.environment_metadata.get('source_sha256')}),
                         'mean_delta_brier':mean(deltas) if deltas else None,
                         'std_delta_brier':stdev(deltas) if len(deltas)>1 else None,
                         'delta_brier_ci95':interval(deltas)})
        session.budget_consumed['wall_seconds']=time.monotonic()-started
        session.state='COMPLETED' if all(r['completed']==seeds_per_condition for r in rows) else 'FAILED'
        session.termination_reason='Independent reference grid complete' if session.state=='COMPLETED' else 'One or more reference trials failed; incomplete conditions are not truth labels'
        repo.save_session(session)
        from slothlab.reporting.generator import generate_report
        report=generate_report(repo,session.id,output)
    data={'kind':'independent reference grid','created_at':now(),'session_id':session.id,'db_path':str(db),'storage_backend':config.storage_backend,'report':str(report),
          'planner_access':False,'reference_seeds':seeds,'conditions':rows,
          'limitations':['Reference means are independent finite-sample estimates, not exact population truth.','Reference outcomes must be inspected only after an autonomous investigation terminates.']}
    path=output/'reference.json'
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)
    return path


def compare_reference(quality, reference):
    """Compare final confirmed estimates only; no reference result is sent to the model."""
    reference_rows={row['condition_key']:row for row in reference.get('conditions',[])}
    rows=[]
    for group in quality['groups']:
        ref=reference_rows.get(condition_key(group['parameters']))
        observed=group['confirmatory_mean_delta_brier']
        if ref is None or observed is None or ref['mean_delta_brier'] is None:
            continue
        ref_ci=ref.get('delta_brier_ci95')
        obs_ci=group.get('confirmatory_delta_brier_ci95')
        sources=quality.get('scientific_source_versions',[])
        compatible=len(sources)==1 and sources==ref.get('scientific_source_versions',[])
        resolved=bool(compatible and ref.get('completed',len(ref.get('result_ids',[])))>=3 and ref_ci and (ref_ci[1]<0 or ref_ci[0]>0))
        rows.append({'parameters':group['parameters'],'agent_mean_delta_brier':observed,'reference_mean_delta_brier':ref['mean_delta_brier'],
                     'absolute_mean_difference':abs(observed-ref['mean_delta_brier']),
                     'direction_agreement':(observed<0)==(ref['mean_delta_brier']<0) if resolved else None,
                     'reference_direction_resolved':resolved,'protocol_source_compatible':compatible,'agent_result_ids':group['confirmatory_result_ids'],'reference_result_ids':ref['result_ids']})
    judged=[r['direction_agreement'] for r in rows if r['direction_agreement'] is not None]
    return {'matched_conditions':len(rows),'resolved_direction_conditions':len(judged),
            'direction_agreement':sum(judged)/len(judged) if judged else None,'conditions':rows,
            'note':'Independent grid is a noisy final-check estimate; unresolved reference directions are not graded as failures.'}


def load_reference_grid(path):
    """Verify a reference summary against its immutable persisted measurements."""
    import math
    data=json.loads(Path(path).read_text())
    if not isinstance(data,dict) or data.get('kind')!='independent reference grid' or data.get('planner_access') is not False:
        raise ValueError('Expected an independent reference grid withheld from planning')
    if not isinstance(data.get('conditions'),list) or not isinstance(data.get('reference_seeds'),list):
        raise ValueError('Reference grid has no valid conditions/seed manifest')
    if any(type(seed) is not int or not 0<=seed<2**31 for seed in data['reference_seeds']):
        raise ValueError('Reference seed manifest is invalid')
    database=Path(data.get('db_path',''))
    if not database.is_file():
        raise ValueError('Reference memory is unavailable; generate or restore the complete local reference artifacts')
    with open_repository(database,data.get('storage_backend','sqlite')) as repo:
        stored={result.id:result for result in repo.results(data.get('session_id',''))}
        if not stored:
            raise ValueError('Reference memory has no persisted measurements')
        for condition in data['conditions']:
            if not isinstance(condition,dict):
                raise ValueError('Reference condition is malformed')
            parameters=Parameters.model_validate(condition.get('parameters',{}))
            if condition.get('condition_key')!=condition_key(parameters):
                raise ValueError('Reference condition identity was modified')
            observations={}
            if not isinstance(condition.get('result_ids'),list) or not all(isinstance(identity,str) for identity in condition['result_ids']):
                raise ValueError('Reference result manifest is malformed')
            for identity in condition['result_ids']:
                result=stored.get(identity)
                if result is None or not repo.verified(result):
                    raise ValueError('Reference contains missing or unverified evidence')
                spec=repo.get_spec(result.experiment_id)
                if spec.seed not in data['reference_seeds'] or spec.phase!='confirmatory' or spec.parameters!=parameters:
                    raise ValueError('Reference measurement does not match its declared condition/seed')
                observations.setdefault(spec.seed,result)
            deltas=[r.metrics['delta_brier'] for r in observations.values()]
            expected_mean=mean(deltas) if deltas else None
            actual_mean=condition.get('mean_delta_brier')
            if condition.get('completed')!=len(deltas) or (expected_mean is None and actual_mean is not None) or (expected_mean is not None and (type(actual_mean) not in (int,float) or not math.isfinite(actual_mean) or not math.isclose(actual_mean,expected_mean,abs_tol=1e-12))):
                raise ValueError('Reference summary disagrees with persisted measurements')
            condition['delta_brier_ci95']=interval(deltas)
            condition['scientific_source_versions']=sorted({r.environment_metadata['source_sha256'] for r in observations.values() if r.environment_metadata.get('source_sha256')})
    return data
