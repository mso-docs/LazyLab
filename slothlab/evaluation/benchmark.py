"""Cold-store comparisons: autonomous Ollama runs or explicitly labeled fixture replay."""
import json
from pathlib import Path
from slothlab.config import Config, load_config
from slothlab.schemas import ResearchSession, Hypothesis, ExperimentSpec, now
from slothlab.memory.repository import Repository
from slothlab.memory.factory import open_repository
from slothlab.lazyloop.controller import decide, validate_proposal
from slothlab.experiments.executor import execute
from slothlab.agent.orchestrator import ResearchAgent
from slothlab.models import client_from_config
from slothlab.reporting.generator import generate_report, report_data

MODES = ("baseline", "cache_only", "lazyloop")


def _replay_spec(hypothesis_id, item, base_parameters):
    if not isinstance(item,dict):
        raise ValueError('A replay proposal must be an object')
    allowed={'phase','seed','parameters','replicate_group','estimated_compute_seconds','experiment_family','dataset_id','protocol_version','rationale'}
    if set(item)-allowed:
        raise ValueError('Replay proposal contains an unauthorized field')
    return ExperimentSpec(hypothesis_id=hypothesis_id,seed=item['seed'],phase=item.get('phase','exploratory'),
        parameters={**base_parameters,**item.get('parameters',{})},replicate_group=item.get('replicate_group','fixture-condition'),
        estimated_compute_seconds=item.get('estimated_compute_seconds',1),
        experiment_family=item.get('experiment_family','prior_correction'),dataset_id=item.get('dataset_id','synthetic-label-shift-v1'),
        protocol_version=item.get('protocol_version','1'),rationale=item.get('rationale','Predeclared replay fixture; no model inference'))


def _future_authorized(schedule, start_index, hypothesis_id, base_parameters, config):
    future=[]
    for index,item in enumerate(schedule[start_index:],start_index):
        try:
            candidate=_replay_spec(hypothesis_id,item,base_parameters)
            validate_proposal(candidate,config,{hypothesis_id})
            future.append((index,candidate))
        except (ValueError,TypeError,KeyError):
            continue
    return future


def replay(repo, config, schedule=None):
    """Execute explicit proposals with real science and inspectable controller decisions."""
    import time
    from slothlab.schemas import LazyLoopDecision,uid
    from slothlab.lazyloop.fingerprint import fingerprint
    from slothlab.lazyloop.stopping import objective_completion
    start=time.monotonic()
    repo.save_objective(config.objective)
    session=ResearchSession(objective_id=config.objective.id,model_name='none: deterministic proposal replay',mode=config.mode,budget_configuration=config.budget)
    repo.save_session(session)
    repo.event(session.id,'configuration',config.model_dump(mode='json'))
    hypothesis=Hypothesis(session_id=session.id,statement='Characterize oracle prior correction under the declared conditions',falsifiable_prediction='Retain measured effect directions and independent evidence without presuming improvement')
    repo.save_hypothesis(hypothesis)
    schedule=schedule if schedule is not None else ([{'phase':'exploratory','seed':seed} for seed in config.exploratory_seeds[:3] for _ in range(2)]+[{'phase':'confirmatory','seed':seed} for seed in config.confirmatory_seeds[:3]])
    try:
        json.dumps(schedule,allow_nan=False)
        raw_schedule=schedule
    except (ValueError,TypeError):
        raw_schedule={'raw':repr(schedule),'contains_non_json_values':True}
    repo.event(session.id,'replay_protocol',{'schedule':raw_schedule,'planner_inference':False})
    base_parameters={key:values[0] for key,values in config.objective.permitted_parameters.items() if values}
    seen_results=set();processed=0
    for index,item in enumerate(schedule):
        session.budget_consumed['wall_seconds']=time.monotonic()-start
        if session.budget_consumed['wall_seconds']>=config.budget.wall_seconds or session.iteration_count>=config.budget.max_rounds:
            session.termination_reason='Hard wall/planning budget exhausted in fixed replay'
            break
        session.iteration_count+=1;processed=index+1
        proposal_id=uid()
        try:
            json.dumps(item,allow_nan=False)
            proposal_payload=item
        except (ValueError,TypeError):
            proposal_payload={'raw':repr(item)}
        repo.event(session.id,'proposal',{'id':proposal_id,'raw_proposal':proposal_payload,'replay':True})
        try:
            spec=_replay_spec(hypothesis.id,item,base_parameters)
            spec.id=proposal_id
            validate_proposal(spec,config,{hypothesis.id})
            repo.save_spec(session.id,spec)
        except (ValueError,TypeError,KeyError) as exc:
            repo.save_decision(LazyLoopDecision(experiment_id=proposal_id,session_id=session.id,decision='REJECT',reason='Invalid or unauthorized replay proposal: '+str(exc)))
            session.no_progress_count+=1
            repo.save_session(session)
            continue
        decision,cached=decide(spec,session,config,repo)
        repo.save_decision(decision)
        if decision.decision=='REUSE':
            repo.save_result(session.id,cached)
            session.budget_consumed['cache_hits']+=1
            session.no_progress_count=session.no_progress_count+1 if cached.id in seen_results else 0
            seen_results.add(cached.id)
        elif decision.decision in {'EXECUTE','REPLICATE'}:
            session.budget_consumed['experiments']+=1
            repo.event(session.id,'execution_reserved',{'experiment_id':spec.id,'fingerprint':fingerprint(spec),'replay':True})
            repo.save_session(session)
            result=execute(spec,Path(config.artifact_dir)/session.id/'experiments',timeout=min(config.budget.experiment_timeout,max(.001,config.budget.wall_seconds-session.budget_consumed['wall_seconds'])),memory_mb=config.budget.memory_mb,isolation=getattr(config,'execution_isolation','auto'))
            repo.save_result(session.id,result)
            repo.event(session.id,'experiment_completed',{'result_id':result.id,'status':result.status})
            seen_results.add(result.id);session.no_progress_count=0
            if result.status=='FAILED':
                session.state='FAILED';session.termination_reason=result.error_details
                break
        else:
            session.no_progress_count+=1
        repo.save_session(session)
        future=_future_authorized(schedule,processed,hypothesis.id,base_parameters,config)
        remaining_confirmation=[candidate for _,candidate in future if candidate.phase=='confirmatory']
        verdict=objective_completion(config,repo.specs(session.id),repo.results(session.id),repo.verified)
        repo.event(session.id,'completion_check',verdict)
        if verdict['satisfied'] and not remaining_confirmation:
            session.state='COMPLETED';session.termination_reason=verdict['reason']
            break
        if verdict['satisfied'] and remaining_confirmation:
            repo.event(session.id,'strategy_revision',{'decision':'DEFER','reason':'Minimum evidence is sufficient but every predeclared confirmation must finish before completion','remaining_confirmation_count':len(remaining_confirmation)})
        if session.mode=='lazyloop' and session.no_progress_count>=config.budget.no_progress_rounds:
            known={result.fingerprint for result in repo.results(session.id) if repo.verified(result)}
            future_work=bool(remaining_confirmation) or any(fingerprint(candidate) not in known for _,candidate in future)
            if future_work:
                reason='A predeclared independent experiment remains; known confirmation must not be discarded as repetition'
                repo.event(session.id,'soft_stop_deferred',{'reason':reason})
                repo.event(session.id,'strategy_revision',{'decision':'DEFER','reason':reason,'evidence_references':[result.id for result in repo.results(session.id)]})
            else:
                session.termination_reason='Repeated unproductive planning in fixed replay: evidence insufficient'
                break
    if session.state not in {'FAILED','COMPLETED'}:
        session.state='STOPPED'
        session.termination_reason=session.termination_reason or 'Fixed replay schedule completed or hard budget reached; no autonomous inference evaluated'
    session.budget_consumed['wall_seconds']=time.monotonic()-start
    remaining=_future_authorized(schedule,processed,hypothesis.id,base_parameters,config)
    known={result.fingerprint for result in repo.results(session.id) if repo.verified(result)}
    pending_confirmation=[str(index) for index,candidate in remaining if candidate.phase=='confirmatory' and fingerprint(candidate) not in known]
    soft_stop='Repeated unproductive planning' in (session.termination_reason or '')
    repo.event(session.id,'termination_audit',{'known_protocol_premature_stop':bool(soft_stop and pending_confirmation),'scope':'predeclared replay schedule','reason':'Known remaining confirmation checked independently of future outcomes','remaining_confirmation_ids':pending_confirmation,'remaining_authorized_proposals':len(remaining)})
    repo.save_session(session)
    return session


def _write_comparison(output, rows, use_replay, complete):
    from slothlab.evaluation.metrics import summarize_comparison
    result = {'evaluation_kind': 'fixed proposal replay (real experiments; no LLM autonomy evaluated)' if use_replay else 'autonomous Ollama comparison',
              'created_at': now(), 'complete':complete,'runs': rows,
              'failed_runs':sum(row['state']=='FAILED' for row in rows),
              'successful_runs':sum(row['state']!='FAILED' for row in rows),
              'all_runs_failed':bool(rows) and all(row['state']=='FAILED' for row in rows),
              'paired_comparisons':summarize_comparison(rows,replay=use_replay),
              'limitations': [
                  'Scientific scores use a predeclared finite benchmark rubric, not general scientific truth.',
                  'Replay has intentionally repeated proposals and does not establish autonomous model efficiency.',
                  'Student-t intervals assume independent trial differences; no multiplicity adjustment is applied.',
                  'Timing includes process startup; OS caching and scheduling affect duration.',
                  'Autonomous trajectories may differ despite identical constraints; fewer than three successful paired trials cannot establish quality preservation.'
              ]}
    destination=output/'comparison.json'
    temporary=output/'comparison.json.tmp'
    temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    temporary.replace(destination)
    lines=['# SlothLab efficiency comparison','',result['evaluation_kind'],'',
           '| Scenario | Trial | Mode | State | Executed | Reused | Wall seconds | Model tokens | Evidence coverage | Scientific rubric |',
           '|---|---:|---|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        tokens=row['model_tokens'] if row['model_tokens'] is not None else 'unknown'
        lines.append(f"| {row['scenario']} | {row['trial']} | {row['mode']} | {row['state']} | {row['experiment_count']} | {row['cache_hits']} | {row['wall_seconds']:.3f} | {tokens} | {row['quality']['quality_score']:.3f} | {row['quality']['scientific_quality_score']:.3f} |")
    lines+=['','## Paired comparisons','']
    for comparison in result['paired_comparisons']:
        lines.append(f"- **{comparison['mode']}**: {comparison['verdict']}; {comparison['valid_pairs']} paired observations. Quality difference (candidate minus baseline): {comparison['mean_quality_delta']}; 95% interval: {comparison['quality_delta_ci95']}.")
    lines+=['','## Limits','',*['- '+text for text in result['limitations']]]
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    return destination


def run_benchmark(suite, output_dir, use_replay=False, repeats=1, reference_path=None, config_overrides=None):
    """Run all arms, preserve failed sessions, and write progress after every arm.

    Constraints are preflighted before any execution. A reference grid is used
    exclusively for final scoring and is never attached to model context.
    """
    import hashlib
    from slothlab.evaluation.quality import assess_quality
    from slothlab.evaluation.reference import compare_reference,load_reference_grid
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ValueError('repeats must be an integer between 1 and 100')
    output=Path(output_dir).resolve()
    paths=sorted(Path(suite).glob('*.yaml'))
    if not paths:
        raise ValueError(f'No YAML benchmark objectives found in {suite}')
    allowed_overrides={'model','base_url','inference_timeout_seconds','inference_context_tokens','inference_threads','inference_thinking','execution_isolation','storage_backend'}
    if set(config_overrides or {})-allowed_overrides:
        raise ValueError('Benchmark overrides may change model/runtime settings only; objective and budgets remain scenario-controlled')
    templates={path:Config.model_validate({**load_config(path).model_dump(mode='json'),**(config_overrides or {})}) for path in paths}
    if not use_replay and any(not config.model for config in templates.values()):
        raise ValueError('Set OLLAMA_MODEL or model in benchmark YAML; --replay is a separate no-inference controller check')
    for path in paths:
        for trial in range(repeats):
            for mode in MODES:
                filename='memory.json' if templates[path].storage_backend=='document' else 'memory.sqlite'
                db=output/f'{path.stem}-{trial}-{mode}'/filename
                if db.exists():
                    raise ValueError(f'Benchmark requires fresh storage; output already exists: {db}')
    reference=load_reference_grid(reference_path) if reference_path else None
    if reference and (reference.get('kind')!='independent reference grid' or reference.get('planner_access') is not False):
        raise ValueError('Expected an independent reference grid withheld from planning')
    output.mkdir(parents=True,exist_ok=True)
    try:
        with (output/'.benchmark.lock').open('x') as lock:
            lock.write(now())
    except FileExistsError as exc:
        raise ValueError('Benchmark output is already claimed; use fresh storage') from exc
    rows=[]
    for path,template in templates.items():
        partitions=trial_seed_partitions(template,repeats)
        if reference and set(reference.get('reference_seeds',[])) & {s for part in partitions for values in part.values() for s in values}:
            raise ValueError('Reference seeds overlap benchmark trial partitions; generate a new independent reference grid')
        signature_payload={'objective':template.objective.model_dump(exclude={'id'}),'budget':template.budget.model_dump(),
                           'exploratory_seeds':template.exploratory_seeds,'confirmatory_seeds':template.confirmatory_seeds,
                           'model':template.model,'base_url':template.base_url,'context_tokens':template.inference_context_tokens,
                           'inference_thinking':template.inference_thinking,'inference_threads':template.inference_threads,
                           'inference_timeout_seconds':template.inference_timeout_seconds,'execution_isolation':template.execution_isolation}
        replay_file=path.with_suffix('.replay.json')
        replay_schedule=json.loads(replay_file.read_text())['schedule'] if use_replay and replay_file.is_file() else None
        for trial in range(repeats):
            trial_partitions=partitions[trial]
            signature_payload.update(trial_partitions)
            signature=hashlib.sha256(json.dumps(signature_payload,sort_keys=True).encode()).hexdigest()
            seed_map={old:new for key in ('exploratory_seeds','confirmatory_seeds') for old,new in zip(getattr(template,key),trial_partitions[key])}
            trial_schedule=[dict(item,seed=seed_map.get(item['seed'],item['seed'])) for item in replay_schedule] if replay_schedule is not None else None
            # Counterbalance arm order over repeat trials to reduce model/OS warmup bias.
            mode_order=MODES[trial%len(MODES):]+MODES[:trial%len(MODES)]
            for mode in mode_order:
                run_dir=output/f'{path.stem}-{trial}-{mode}'
                run_dir.mkdir(parents=True,exist_ok=True)
                db=run_dir/('memory.json' if template.storage_backend=='document' else 'memory.sqlite')
                config=Config.model_validate({**template.model_dump(mode='json'),'mode':mode,'db_path':str(db),'artifact_dir':str(run_dir),**trial_partitions})
                with open_repository(db,config.storage_backend) as repo:
                    failure=None
                    try:
                        if use_replay:
                            s=replay(repo,config,trial_schedule) if trial_schedule is not None else replay(repo,config)
                        else:
                            s=ResearchAgent(repo,client_from_config(config),config).create()
                    except Exception as exc:
                        failure=f'{type(exc).__name__}: {exc}'
                        sessions=repo.list_sessions()
                        if sessions:
                            s=sessions[-1]
                            s.state='FAILED'
                            s.termination_reason=failure
                            repo.save_session(s)
                        else:
                            repo.save_objective(config.objective)
                            s=ResearchSession(objective_id=config.objective.id,model_name=config.model or 'none',mode=mode,budget_configuration=config.budget,state='FAILED',termination_reason=failure)
                            s.budget_consumed['tokens']=None
                            repo.save_session(s)
                    report=generate_report(repo,s.id,run_dir)
                    data=report_data(repo,s.id)
                    row={'scenario':path.stem,'trial':trial,'mode':mode,'arm_order':list(mode_order),'state':s.state,'session_id':s.id,
                         'constraints_signature':signature,'seed_partitions':trial_partitions,'experiment_count':s.budget_consumed['experiments'],'cache_hits':s.budget_consumed['cache_hits'],
                         'model_tokens':s.budget_consumed['tokens'],'model_digest':next((entry.get('digest') for entry in reversed(data['model_provenance']) if entry.get('digest')),None),'token_reservations':s.budget_consumed['token_reservations'],
                         'model_calls':s.budget_consumed['model_calls'],'inference_seconds':s.budget_consumed['inference_seconds'],
                         'wall_seconds':s.budget_consumed['wall_seconds'],'experiment_seconds':data['telemetry']['execution_seconds'],
                         'redundant_proposals':data['telemetry']['redundant_proposals'],
                         'supported_findings':data['telemetry']['supported_findings'],'premature_stops':data['telemetry']['premature_stops'],
                         'failed_execution_attempts':data['telemetry']['failed_execution_attempts'],'rejected_proposals':data['telemetry']['rejected_proposals'],
                         'scientific_cpu_seconds':data['telemetry']['scientific_cpu_seconds'],'peak_memory_bytes':data['telemetry']['peak_memory_bytes'],
                         'scientific_source_versions':sorted({r.environment_metadata['source_sha256'] for r in repo.results(s.id) if r.environment_metadata.get('source_sha256')}),
                         'quality':data['quality'],'termination_reason':s.termination_reason,'error':failure,
                         'report':str(report),'db_path':str(db)}
                    if reference:
                        row['reference_comparison']=compare_reference(data['quality'],reference)
                    rows.append(row)
                    _write_comparison(output,rows,use_replay,False)
    return _write_comparison(output,rows,use_replay,True)


def trial_seed_partitions(config, repeats):
    """Disjoint scientific draws per trial; matched within each comparison arm."""
    original={'exploratory_seeds':list(config.exploratory_seeds),'confirmatory_seeds':list(config.confirmatory_seeds)}
    partitions=[original]
    used=set(config.exploratory_seeds+config.confirmatory_seeds)
    candidate=(max(used)+1)%(2**31)
    for _ in range(1,repeats):
        current={}
        for key,values in original.items():
            selected=[]
            while len(selected)<len(values):
                if candidate not in used:
                    selected.append(candidate)
                    used.add(candidate)
                candidate=(candidate+1)%(2**31)
            current[key]=selected
        partitions.append(current)
    return partitions
