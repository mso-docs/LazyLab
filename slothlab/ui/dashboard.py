"""Interactive local research workspace; all findings are persisted measurements."""
from __future__ import annotations

import html
import json
import os
import sqlite3
from pathlib import Path
from dataclasses import replace
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import altair as alt
import streamlit as st

from slothlab.config import Config
from slothlab.memory.repository import Repository
from slothlab.memory.factory import open_repository
from slothlab.reporting.generator import generate_report, report_data
from slothlab.schemas import Budget, ResearchObjective
from slothlab.ui.presentation import comparison_files, comparison_frame, experiment_frame, proposal_frame, format_seconds, tail_log
from slothlab.ui.style import STYLE
from slothlab.ui.themes import theme_css, LIGHT, DARK
from slothlab.ui.identity import render_identity_controls, IdentityContext
from slothlab.runtime.profiles import LocalProfileStore
from slothlab.ui.learning import render_learning_center

ACTIVE_JOBS = {'queued', 'running', 'stopping'}
TERMINAL_SESSIONS = {'COMPLETED', 'STOPPED', 'FAILED'}


def show_chart(chart, **kwargs):
    mode=st.session_state.get('appearance_theme','System')
    dark=mode=='Dark' or (mode=='System' and st.session_state.get('_identity_browser_observed',{}).get('system_dark') is True)
    palette=DARK if dark else LIGHT
    styled=chart.configure(background=palette['panel']).configure_view(stroke=None).configure_axis(
        labelColor=palette['ink'],titleColor=palette['ink'],gridColor=palette['line'],domainColor=palette['line']).configure_legend(
        labelColor=palette['ink'],titleColor=palette['ink']).configure_title(color=palette['ink'])
    st.altair_chart(styled,theme=None,**kwargs)


def literal_markdown(value):
    encoded = html.escape(str(value))
    return ''.join(f'&#{ord(c)};' if c in '*_[]!`#\\' else c for c in encoded)


def safe_prose(value, strong=False):
    """Render model/uploaded prose without interpreting links, images or HTML."""
    encoded=literal_markdown(value)
    tag = 'strong' if strong else 'span'
    st.markdown(f'<{tag}>{encoded}</{tag}>',unsafe_allow_html=True)


def job_manager(root_dir=None):
    try:
        from slothlab.runtime.jobs import JobManager
        return JobManager(Path(root_dir or os.getenv('SLOTHLAB_JOB_DIR', 'artifacts/jobs')))
    except (ImportError, OSError) as exc:
        st.session_state['job_service_error'] = str(exc)
        return None


def get_jobs(manager):
    if manager is None:
        return []
    try:
        return manager.list_jobs()
    except (OSError, ValueError, RuntimeError) as exc:
        st.warning(f'Background job status is unavailable: {exc}')
        return []


def show_empty():
    st.markdown('<div class="lab-empty"><h3>A clear question is the first experiment.</h3><p>Create an investigation to begin. Your hypotheses, measurements and decisions will appear here.</p></div>', unsafe_allow_html=True)
    st.info('No research memory found yet. Open “New investigation” to configure and start research, or open an exported bundle in guest mode.')


def launch_form(manager, db_path: str, artifact_dir: str, active_job_count: int = 0, storage_backend='sqlite'):
    st.subheader('Design an investigation')
    st.caption('Choose the scientific question and permitted experimental space. The agent works inside these boundaries.')
    with st.expander('AI server connection · local or remote', expanded=not bool(os.getenv('OLLAMA_MODEL'))):
        st.caption('Any reachable Ollama-compatible HTTP(S) endpoint can provide inference. Experiments run on this app host; research context is sent to the selected AI server. Other API formats and authenticated gateways are not currently supported.')
        endpoint = st.text_input('Ollama endpoint', value=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'), key='ollama_endpoint')
        if st.button('Discover installed models', key='discover_models'):
            try:
                Config(base_url=endpoint)
                with urlopen(endpoint.rstrip('/')+'/api/tags', timeout=5) as response:
                    models = json.loads(response.read(1024*1024))
                if not isinstance(models,dict) or not isinstance(models.get('models'),list):
                    raise ValueError('The endpoint returned an invalid installed-model list.')
                st.session_state['installed_models'] = [item['name'] for item in models.get('models', [])]
                if st.session_state['installed_models'] and not st.session_state.get('model_name'):
                    st.session_state['model_name'] = st.session_state['installed_models'][0]
                st.success(f"Found {len(st.session_state['installed_models'])} installed models.")
            except (URLError, OSError, ValueError, KeyError,TypeError) as exc:
                st.error(f'Cannot discover Ollama models. Start Ollama and check the endpoint. {exc}')
        installed = st.session_state.get('installed_models', [])
        if installed:
            st.caption('Installed: '+', '.join(installed))
    with st.form('new_investigation', border=True):
        title = st.text_input('Investigation title', value='Prior correction under prevalence shift', max_chars=200)
        question = st.text_area('Research question', value='When does adjusting predicted probabilities for a known change in class prevalence improve Brier score, and are the effects consistent across independent seeds?', height=95)
        left, right = st.columns(2)
        with left:
            st.session_state.setdefault('model_name', os.getenv('OLLAMA_MODEL', installed[0] if installed else ''))
            model = st.text_input('Ollama model', key='model_name', placeholder='A model from ollama list')
        with right:
            mode = st.selectbox('Execution strategy', ['lazyloop', 'cache_only', 'baseline'], format_func=lambda value: {'lazyloop':'LazyLoop · prioritize, reuse & stop', 'cache_only':'Cache-only · verified exact reuse', 'baseline':'Baseline · no reuse optimization'}[value])
        st.markdown('**Permitted experimental conditions**')
        c1, c2, c3 = st.columns(3)
        with c1:
            train_prevalence = st.slider('Training prevalence', min_value=0.05, max_value=0.95, value=0.5, step=0.05)
            evaluation_prevalences = st.multiselect('Evaluation prevalences', [0.05,0.1,0.2,0.3,0.5,0.7,0.8,0.9,0.95], default=[0.1,0.2,0.5,0.8])
        with c2:
            sample_sizes = st.multiselect('Sample sizes per split', [100,250,500,1000,2000,5000,10000,20000], default=[500,1000,2000])
            class_separations = st.multiselect('Class separation', [0.25,0.5,1.0,1.5,2.0,3.0,5.0], default=[0.5,1.0])
        with c3:
            temperatures = st.multiselect('Probability temperatures', [0.5,1.0,1.5,2.0,3.0,4.0], default=[1.0,2.0], help='A temperature of 1 leaves probabilities unchanged; other values model miscalibration.')
            noise = st.select_slider('Gaussian feature noise', options=[0.0,0.05,0.1,0.2], value=0.0)
        st.markdown('**Completion protocol**')
        st.caption('Define what would complete this finite investigation. Meeting these targets scopes the conclusion to tested conditions; it does not establish a universal law.')
        p1,p2,p3 = st.columns(3)
        with p1:
            require_confirmation = st.checkbox('Require independent confirmation',value=True)
            minimum_exploratory = st.number_input('Minimum exploratory experiments',min_value=1,max_value=1000,value=3,step=1)
        with p2:
            minimum_conditions = st.number_input('Minimum distinct conditions',min_value=1,max_value=100,value=1,step=1)
            minimum_confirmatory_groups = st.number_input('Minimum confirmed condition groups',min_value=1,max_value=100,value=1,step=1)
        with p3:
            effect_direction = st.selectbox('Replicated effect target',['either','negative','positive','zero'],format_func=lambda value:{'either':'Consistent improvement, regression, or zero','negative':'Consistent improvement · negative delta','positive':'Consistent regression · positive delta','zero':'Within declared numerical tolerance'}[value])
            effect_tolerance = st.number_input('Absolute delta tolerance',min_value=0.0,max_value=1.0,value=0.0000000001,format='%.10f',help='A predeclared numerical completion tolerance, not a confidence interval or statistical significance threshold.')
            st.caption('Mixed independent effects remain inconclusive rather than satisfying a directional target.')
        st.markdown('**Compute budget**')
        b1,b2,b3,b4 = st.columns(4)
        with b1:
            experiments = st.number_input('Maximum experiments', min_value=1, max_value=1000, value=12, step=1)
        with b2:
            minutes = st.number_input('Wall-clock minutes', min_value=1, max_value=1440, value=20, step=1)
        with b3:
            tokens = st.number_input('Model token budget', min_value=1000, max_value=2000000, value=20000, step=1000)
        with b4:
            rounds = st.number_input('Maximum planning rounds', min_value=1, max_value=1000, value=20, step=1)
        with st.expander('Advanced execution settings'):
            a1,a2,a3 = st.columns(3)
            with a1:
                candidate_limit = st.number_input('Candidates per round', min_value=1, max_value=20, value=5, step=1)
                call_tokens = st.number_input('Maximum output tokens per call', min_value=64, max_value=16000, value=2000, step=100)
            with a2:
                timeout = st.number_input('Experiment timeout (seconds)', min_value=1, max_value=600, value=30, step=1)
                memory = st.number_input('Worker memory limit (MiB)', min_value=256, max_value=32768, value=2048, step=256)
            with a3:
                inference_timeout = st.number_input('Inference timeout (seconds)', min_value=1, max_value=1200, value=300, step=1)
                confirmation_seeds = st.number_input('Minimum independent replications', min_value=3, max_value=20, value=3, step=1)
            x1,x2,x3 = st.columns(3)
            with x1:
                isolation = st.selectbox('Execution isolation',['auto','bubblewrap','subprocess'],help='Auto uses Bubblewrap when available and records a weaker subprocess fallback. Bubblewrap explicitly requires OS isolation and fails closed if unavailable.')
            with x2:
                context_tokens = st.number_input('Inference context tokens',min_value=2048,max_value=131072,value=8192,step=1024)
                cpu_threads = st.number_input('Inference CPU threads · 0 for auto',min_value=0,max_value=256,value=0,step=1)
            with x3:
                thinking = st.selectbox('Model thinking',['Auto','Disabled','Enabled'],help='Only use an explicit setting when the selected Ollama model supports it.')
        st.caption('Synthetic oracle protocol: true evaluation prevalence is supplied. No model-generated code is executed.')
        submitted = st.form_submit_button('Start investigation', type='primary', disabled=manager is None or active_job_count > 0, width='stretch')
    if active_job_count:
        st.info('One local worker is already active. Stop it or wait for completion before starting another investigation.')
    if manager is None:
        st.warning('Background execution service is unavailable. Existing research can still be inspected. '+st.session_state.get('job_service_error',''))
    if submitted:
        if not title.strip() or not question.strip() or not model.strip():
            st.error('Add an investigation title, research question, and installed Ollama model before starting.')
            return
        if not all([evaluation_prevalences,sample_sizes,class_separations,temperatures]):
            st.error('Choose at least one allowed value in each experimental condition.')
            return
        required_final_candidates = confirmation_seeds*minimum_confirmatory_groups
        if require_confirmation and candidate_limit < required_final_candidates:
            st.error(f'Independent final confirmation requires candidates per round to cover every condition group: {minimum_confirmatory_groups} × {confirmation_seeds} = {required_final_candidates}.')
            return
        try:
            objective = ResearchObjective(title=title.strip(), question=question.strip(), permitted_parameters={
                'train_prevalence':[float(train_prevalence)], 'evaluation_prevalence':evaluation_prevalences,
                'sample_size':sample_sizes, 'feature_count':[6], 'class_separation':class_separations,
                'noise':[float(noise)], 'logistic_c':[1.0], 'probability_temperature':temperatures,
            }, success_criteria={'minimum_replications':int(confirmation_seeds),
                'minimum_exploratory_experiments':int(minimum_exploratory),
                'minimum_conditions':int(minimum_conditions), 'require_confirmation':require_confirmation,
                'minimum_confirmatory_groups':int(minimum_confirmatory_groups),'effect_direction':effect_direction,
                'effect_tolerance':float(effect_tolerance)})
            budget = Budget(max_experiments=int(experiments),max_rounds=int(rounds),max_candidates=int(candidate_limit),
                wall_seconds=float(minutes*60),max_tokens=int(tokens),call_token_reserve=int(call_tokens),
                experiment_timeout=float(timeout),memory_mb=int(memory),minimum_replications=int(confirmation_seeds))
            config = Config(objective=objective,budget=budget,model=model.strip(),base_url=endpoint.strip(),mode=mode,
                db_path=db_path,artifact_dir=artifact_dir,inference_timeout_seconds=float(inference_timeout),
                inference_context_tokens=int(context_tokens),inference_threads=int(cpu_threads) or None,
                inference_thinking={'Auto':None,'Disabled':False,'Enabled':True}[thinking],execution_isolation=isolation,storage_backend=storage_backend)
            launched = manager.launch(config)
            st.session_state['last_launched_job'] = launched['id']
            st.session_state['launch_flash'] = 'Investigation started in the background. Open “Research” to follow its recorded progress.'
            if launched.get('session_id'):
                st.session_state['selected_session'] = launched['session_id']
            st.rerun()
        except (ValueError,OSError,RuntimeError) as exc:
            st.error(f'Investigation could not start: {exc}')


def render_jobs(manager, jobs):
    if not jobs:
        return
    st.subheader('Execution queue')
    for job in jobs[:8]:
        with st.container(border=True):
            left,right = st.columns([4,1])
            with left:
                state = str(job.get('state','unknown'))
                kind = 'Benchmark' if job.get('kind') == 'benchmark' else 'Investigation'
                st.markdown(f"**{state.replace('_',' ').title()}** · {kind} · `{str(job.get('id',''))[:12]}`")
                if job.get('session_id'):
                    st.caption('Session '+job['session_id'])
                if job.get('error'):
                    st.error(str(job['error']))
                comparison_path = job.get('comparison_path')
                if comparison_path and Path(comparison_path).is_file():
                    if st.button('Open comparison',key='open_comparison_'+str(job['id'])):
                        st.session_state['requested_comparison_path'] = str(Path(comparison_path).resolve())
                        st.success('Comparison selected in the Comparisons tab.')
            with right:
                if manager and state in ACTIVE_JOBS and st.button('Stop run', key='stop_'+str(job['id']), type='secondary'):
                    try:
                        manager.stop(job['id'])
                        st.success('Stop requested.')
                        st.rerun()
                    except (ValueError,OSError,RuntimeError) as exc:
                        st.error(f'Cannot stop run: {exc}')
            log = tail_log(job.get('log_path'))
            if log:
                with st.expander('Execution log'):
                    st.code(log,language='text')


def render_investigation(repo, identity, manager, jobs, artifact_dir):
    data = report_data(repo,identity)
    session = data['session']
    st.markdown('<div class="lab-eyebrow">INVESTIGATION</div>',unsafe_allow_html=True)
    st.subheader(literal_markdown(data['objective']['title']))
    safe_prose(data['objective']['question'])
    cols = st.columns(4)
    cols[0].metric('State',session['state'])
    cols[1].metric('Executed',data['telemetry']['executed_experiments'])
    cols[2].metric('Cache hits',data['telemetry']['cache_hits'])
    cols[3].metric('Model tokens',data['telemetry']['model_tokens'] if data['telemetry']['model_tokens'] is not None else 'Unknown')
    budget,used = session['budget_configuration'],session['budget_consumed']
    st.progress(min(1.0,used['experiments']/budget['max_experiments']),text=f"Experiment budget · {used['experiments']} of {budget['max_experiments']} reserved")
    st.caption(literal_markdown(f"Model: {session['model_name']}  ·  Strategy: {session['mode']}  ·  Wall time: {format_seconds(used['wall_seconds'])}  ·  Remaining: {format_seconds(max(0,budget['wall_seconds']-used['wall_seconds']))}"))
    if session.get('termination_reason'):
        st.info(session['termination_reason'])
    active = any(j.get('session_id')==identity and j.get('state') in ACTIVE_JOBS for j in jobs)
    if session['state'] not in TERMINAL_SESSIONS and not active and manager:
        imported=bool(repo.events(identity,'bundle_import'))
        reviewed=True
        if imported:
            saved=repo.events(identity,'configuration')
            if saved:
                st.caption('Imported AI endpoint and execution settings')
                st.json({key:saved[0]['payload'].get(key) for key in ('base_url','model','budget','execution_isolation')})
            reviewed=st.checkbox('I reviewed the imported AI endpoint and execution settings',key='review_import_'+identity)
        if st.button('Resume investigation',key='resume_'+identity,disabled=not reviewed or any(j.get('state') in ACTIVE_JOBS for j in jobs)):
            try:
                saved = repo.events(identity,'configuration')
                if not saved:
                    raise ValueError('This session has no saved execution configuration.')
                config = Config.model_validate(saved[0]['payload'])
                config.db_path=str(repo.path)
                config.storage_backend='document' if repo.__class__.__name__=='DocumentRepository' else 'sqlite'
                manager.resume(config,identity)
                st.success('Resume started in the background.')
                st.rerun()
            except (ValueError,OSError,RuntimeError) as exc:
                st.error(f'Cannot resume investigation: {exc}')
    overview,history,trace,findings,provenance = st.tabs(['Overview','Experiments','Decision trace','Findings','Provenance & export'])
    frame = experiment_frame(data)
    with overview:
        left,right = st.columns([3,2])
        with left:
            st.markdown('#### Measured loss change')
            if not frame.empty and 'delta_brier' in frame:
                chart = frame[frame['status']=='COMPLETED'].copy()
                if not chart.empty:
                    chart['Trial'] = chart.apply(lambda row: f"Seed {row['seed']} · {str(row['result_id'])[:6]}",axis=1)
                    bars = alt.Chart(chart).mark_bar(cornerRadiusEnd=3).encode(
                        x=alt.X('delta_brier:Q',title='Δ Brier · corrected − baseline'),
                        y=alt.Y('Trial:N',sort=None,title=None),
                        color=alt.condition(alt.datum.delta_brier < 0,alt.value('#21856c'),alt.value('#bb6a4a')),
                        tooltip=['Trial','seed','delta_brier','baseline_brier','corrected_brier'])
                    zero = alt.Chart(pd.DataFrame({'zero':[0]})).mark_rule(color='#82959a',strokeDash=[3,3]).encode(x='zero:Q')
                    show_chart((bars+zero).properties(height=260),width='stretch')
                    st.caption('Δ Brier = corrected − baseline. Values below zero favor correction. Each bar is a persisted measurement.')
                else:
                    st.info('No completed measurements yet.')
            else:
                st.info('Measurements will appear after the first experiment completes.')
        with right:
            st.markdown('#### Research hypotheses')
            for hypothesis in data['hypotheses']:
                with st.container(border=True):
                    st.caption(hypothesis['status'].replace('_',' '))
                    safe_prose(hypothesis['statement'],strong=True)
                    safe_prose(hypothesis['falsifiable_prediction'])
            if not data['hypotheses']:
                st.caption('The model has not recorded hypotheses yet.')
        if data['decisions']:
            decision = data['decisions'][-1]
            st.markdown('#### Latest decision')
            st.write(f"**{decision['decision']}** · {decision['reason']}")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Model calls',data['telemetry'].get('model_calls') or 0)
        c2.metric('Inference time',format_seconds(data['telemetry'].get('inference_seconds')))
        c3.metric('Evidence coverage',f"{data['quality'].get('quality_score',0):.0%}",help='A protocol coverage proxy, not a correctness probability or proof.')
        scientific_score = data['quality'].get('scientific_quality_score')
        c4.metric('Scientific checks', f'{scientific_score:.0%}' if scientific_score is not None else 'Not scored', help='Deterministic scientific checks are separate from coverage and do not establish a universal scientific law.')
    with history:
        proposals = proposal_frame(data)
        if not proposals.empty:
            st.markdown('#### Proposal history')
            st.dataframe(proposals,hide_index=True,width='stretch')
            st.caption('Reuse rows point to the original result. A blank execution runtime means that proposal did not run a new experiment.')
            st.download_button('Download proposal history',proposals.to_csv(index=False),file_name=f'{identity}-proposals.csv',mime='text/csv')
        st.markdown('#### Original measurements')
        if frame.empty:
            st.info('No experimental results recorded yet.')
        else:
            columns = [c for c in ['seed','phase','status','action','baseline_brier','corrected_brier','delta_brier','delta_log_loss','runtime_seconds','parameters','result_id','experiment_id'] if c in frame]
            st.dataframe(frame[columns],hide_index=True,width='stretch')
            st.download_button('Download experiment table',frame.to_csv(index=False),file_name=f'{identity}-experiments.csv',mime='text/csv')
    with trace:
        st.caption('Candidate priorities are transparent engineering heuristics. Hard authorization and resource limits always apply.')
        for index,decision in enumerate(reversed(data['decisions'])):
            with st.expander(f"{decision['decision']} · {decision['reason']}",expanded=index==0):
                st.json(decision)
        if not data['decisions']:
            st.info('No decisions recorded yet.')
    with findings:
        st.warning('True evaluation prevalence is an oracle input in this synthetic protocol. Uncertainty is preserved; model interpretations alone cannot establish a scientific claim.')
        quality = data['quality']
        for group in quality.get('groups',[]):
            with st.container(border=True):
                st.markdown('**'+group.get('protocol_assessment','INSUFFICIENT_EVIDENCE').replace('_',' ').title()+'**')
                st.caption(f"Independent confirmation seeds: {len(group.get('independent_confirmatory_seeds',[]))}")
                delta = group.get('confirmatory_mean_delta_brier')
                if delta is not None:
                    st.write(f'Mean confirmatory Δ Brier: **{delta:+.6f}**')
                with st.expander('Conditions and evidence references'):
                    st.json(group)
        if not quality.get('groups'):
            st.info('There is not yet sufficient recorded evidence for a protocol assessment.')
        with st.expander('Model interpretations · provisional'):
            if data['interpretations']:
                for interpretation in data['interpretations']:
                    safe_prose(interpretation.get('explanation',''))
                    st.caption('Evidence: '+', '.join(interpretation.get('evidence_ids',[])))
            else:
                st.caption('No interpretation has been recorded.')
        with st.expander('Quality method and limitations'):
            st.json(quality)
    with provenance:
        render_portable_export(repo,identity,any(j.get('state') in ACTIVE_JOBS for j in jobs))
        st.caption('Exports preserve the original parameters, environment, artifact hashes, measured results and decision trace. Cache reuse never creates an independent replication.')
        left,right = st.columns(2)
        with left:
            st.download_button('Download evidence JSON',json.dumps(data,indent=2),file_name=f'{identity}-metrics.json',mime='application/json',width='stretch')
        with right:
            if st.button('Prepare Markdown report',key='prepare_report_'+identity,width='stretch'):
                try:
                    report = generate_report(repo,identity,artifact_dir)
                    st.session_state['report_'+identity] = report.read_text()
                    html_report = report.with_suffix('.html')
                    if html_report.is_file():
                        st.session_state['html_report_'+identity] = html_report.read_text()
                except (ValueError,OSError) as exc:
                    st.error(f'Cannot prepare report: {exc}')
            if st.session_state.get('report_'+identity):
                st.download_button('Download Markdown report',st.session_state['report_'+identity],file_name=f'{identity}-report.md',mime='text/markdown')
            if st.session_state.get('html_report_'+identity):
                st.download_button('Download printable HTML',st.session_state['html_report_'+identity],file_name=f'{identity}-report.html',mime='text/html')
        with st.expander('Budget and session checkpoint'):
            st.json({'session':session,'budget':budget,'consumed':used})
        for result in data['results']:
            with st.expander('Result '+result['id'][:12]+' · '+result['status']):
                st.code(result['fingerprint'],language='text')
                st.json({'artifact_paths':result['artifact_paths'],'environment_metadata':result['environment_metadata'],'error_details':result.get('error_details')})



def benchmark_form(manager, artifact_dir, active_job_count, storage_backend='sqlite', isolated=False):
    with st.expander('Run a comparison',expanded=False):
        st.caption('Every scenario runs baseline, cache-only, and LazyLoop in separate cold memories. Autonomous inference can take substantial time; fixed replay runs real science without an LLM.')
        with st.form('benchmark_launch'):
            left,right = st.columns([3,1])
            with left:
                protocol = st.selectbox('Evaluation protocol',['Autonomous Ollama comparison','Fixed proposal replay'],key='benchmark_protocol')
                model = st.text_input('Benchmark model',value=st.session_state.get('model_name',os.getenv('OLLAMA_MODEL','')),placeholder='Required for autonomous comparison')
            with right:
                repeats = st.number_input('Repeated trials',min_value=1,max_value=5,value=1,step=1)
            suite = st.selectbox('Benchmark suite',['benchmarks/objectives','benchmarks/behavioral']) if isolated else st.text_input('Benchmark suite directory',value='benchmarks/objectives')
            from slothlab.assets import asset_path
            scenario_count = len(list(asset_path(suite).glob('*.yaml')))
            st.caption(f'Scheduled variant runs: {scenario_count} scenarios × 3 modes × {repeats} trials = {scenario_count*3*repeats}. Each variant has its own scientific and inference budgets.')
            reference = '' if isolated else st.text_input('Independent reference grid (optional path)',value='',help='A separately generated reference grid provides an independent comparison. Leave empty to use the benchmark runner’s default behavior.')
            submitted = st.form_submit_button('Start benchmark',type='primary',disabled=manager is None or active_job_count>0,width='stretch')
        if submitted:
            use_replay = protocol == 'Fixed proposal replay'
            if not use_replay and not model.strip():
                st.error('Select an installed benchmark model for autonomous evaluation, or choose fixed proposal replay.')
                return
            try:
                config = Config(model=model.strip() or None,base_url=st.session_state.get('ollama_endpoint',os.getenv('OLLAMA_BASE_URL','http://localhost:11434')),artifact_dir=artifact_dir,storage_backend=storage_backend)
                job = manager.launch_benchmark(config,suite=suite,repeats=int(repeats),use_replay=use_replay,reference_path=reference.strip() or None)
                st.session_state['last_benchmark_job'] = job['id']
                st.session_state['launch_flash'] = 'Benchmark started in the background. Follow its execution queue and open the recorded comparison after completion.'
                st.rerun()
            except (OSError,ValueError,RuntimeError) as exc:
                st.error(f'Benchmark could not start: {exc}')


def render_comparisons(artifact_dir, manager, active_job_count=0, storage_backend='sqlite', isolated=False):
    st.subheader('Efficiency, with scientific context')
    st.caption('Compare ordinary autonomous execution, exact caching, and full LazyLoop using measured benchmark outputs.')
    benchmark_form(manager,artifact_dir,active_job_count,storage_backend,isolated)
    discovered = comparison_files(artifact_dir)
    requested = st.session_state.pop('requested_comparison_path',None)
    if requested and Path(requested).is_file():
        if Path(requested) not in discovered:
            discovered.insert(0,Path(requested))
        st.session_state['comparison_picker'] = requested
    chosen = st.selectbox('Recorded comparisons',['Choose a comparison']+[str(p) for p in discovered],key='comparison_picker')
    path = st.text_input('Comparison JSON path',value='' if chosen=='Choose a comparison' else chosen,key='comparison_json_path_'+str(chosen))
    if not path:
        st.info('No comparison selected. Run a benchmark from the CLI or choose an existing comparison above. Fixed replay measures the controller; autonomous comparisons use real model inference.')
        st.code('slothlab benchmark --suite benchmarks/objectives\nslothlab benchmark --suite benchmarks/objectives --replay',language='bash')
        return
    if isolated and not Path(path).resolve().is_relative_to(Path(artifact_dir).resolve()):
        st.error('Choose a comparison from this history workspace.')
        return
    try:
        content = json.loads(Path(path).read_text())
        if not isinstance(content,dict) or not isinstance(content.get('runs'),list):
            raise ValueError('The selected file is not a SlothLab comparison.')
        frame = comparison_frame(content)
    except (OSError,ValueError,TypeError,AttributeError,KeyError) as exc:
        st.error(f'Cannot open comparison: {exc}')
        return
    st.info(content.get('evaluation_kind','Recorded evaluation'))
    if frame.empty:
        st.warning('This comparison has no measured runs.')
        return
    scenarios = list(frame['scenario'].dropna().unique())
    selected = st.multiselect('Scenarios',scenarios,default=scenarios,key='comparison_scenarios_'+path)
    filtered = frame[frame['scenario'].isin(selected)]
    if filtered.empty:
        st.info('Select at least one scenario to view measured results.')
        return
    left,right = st.columns(2)
    colors = alt.Scale(domain=['baseline','cache_only','lazyloop'],range=['#526e8b','#c99855','#21856c'])
    means = filtered.groupby(['scenario','mode'],as_index=False)[['executed','wall_seconds']].mean()
    with left:
        st.markdown('#### Actual executions')
        plot = alt.Chart(means).mark_bar(cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(
            x=alt.X('scenario:N',title=None),y=alt.Y('executed:Q',title='Mean executed experiments'),
            xOffset='mode:N',color=alt.Color('mode:N',scale=colors,title='Strategy'),tooltip=['scenario','mode','executed'])
        show_chart(plot.properties(height=280),width='stretch')
    with right:
        st.markdown('#### End-to-end runtime')
        plot = alt.Chart(means).mark_bar(cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(
            x=alt.X('scenario:N',title=None),y=alt.Y('wall_seconds:Q',title='Mean wall time · seconds'),
            xOffset='mode:N',color=alt.Color('mode:N',scale=colors,title='Strategy'),tooltip=['scenario','mode','wall_seconds'])
        show_chart(plot.properties(height=280),width='stretch')
    st.caption('Bars show means when multiple trials are present. Runtime and scientific-quality checks are reported separately; reduced compute alone is not research success.')
    st.dataframe(filtered,hide_index=True,width='stretch')
    if content.get('paired_comparisons'):
        with st.expander('Paired scientific-quality and efficiency checks'):
            st.json(content['paired_comparisons'])
    for limitation in content.get('limitations',[]):
        st.caption('• '+str(limitation))
    st.download_button('Download comparison JSON',json.dumps(content,indent=2),file_name='comparison.json',mime='application/json')


def render_portable_export(repo, session_id, active):
    from slothlab.memory.bundles import export_bundle
    document_mode=repo.__class__.__name__=='DocumentRepository'
    st.markdown('#### Portable research history')
    include_all=st.checkbox('Include all history in this workspace',value=document_mode,key='bundle_all_'+session_id,
        help='Includes original investigations needed to preserve shared evidence provenance. Exported archives contain real artifact files.')
    st.caption('Pause active work before exporting. Bundles preserve measurements and artifacts; credentials are excluded. Imported archives are data, not proof of their scientific origin.')
    version=str([(session.id,session.last_checkpoint) for session in repo.list_sessions()])
    source=f'{repo.path}:{session_id}:{include_all}:{version}'
    if st.button('Prepare research bundle',key='prepare_bundle_'+session_id,disabled=active):
        try:
            st.session_state['_portable_bundle_data']=export_bundle(repo,session_id,include_workspace=include_all)
            st.session_state['_portable_bundle_source']=source
        except (OSError,ValueError,KeyError) as exc:
            st.error(f'Cannot prepare research bundle: {exc}')
    if st.session_state.get('_portable_bundle_source')==source:
        label='Download guest history bundle (all sessions)' if document_mode and include_all else 'Download research bundle'
        st.download_button(label,st.session_state['_portable_bundle_data'],file_name='slothlab-research.zip',mime='application/zip',disabled=active,key='download_bundle_'+session_id)


def render_guest_import(context, active):
    if context.mode!='guest':
        return
    with st.expander('Guest history · open a downloaded research bundle'):
        st.caption('No SQL database is used. This guest workspace lives in temporary server files; download a bundle to keep it when your browser session ends. Opening a file does not start inference.')
        uploaded=st.file_uploader('Research history bundle',type=['zip'],key='guest_bundle_upload')
        if st.button('Open research bundle',disabled=uploaded is None or active,key='guest_bundle_open'):
            try:
                from slothlab.memory.bundles import import_bundle
                root=Path(st.session_state['_guest_directory'])/'imports'
                imported,session_id=import_bundle(uploaded.getvalue(),root)
                st.session_state['_guest_document_override']=str(imported.path)
                st.session_state['_guest_artifact_override']=str(Path(imported.path).parent/'artifacts')
                st.session_state['selected_session']=session_id
                imported.close()
                st.session_state['launch_flash']='Research history opened in guest mode. Review any imported connection and execution settings before resuming.'
                st.rerun()
            except (OSError,ValueError,KeyError) as exc:
                st.error(f'Cannot open research bundle: {exc}')


def main():
    st.set_page_config(page_title='SlothLab · Research workspace',page_icon='🦥',layout='wide',initial_sidebar_state='expanded')
    st.sidebar.markdown('<div class="lab-brand">🦥 Sloth<span>Lab</span></div><div class="lab-brand-sub">LAZYLOOP RESEARCH WORKSPACE</div>',unsafe_allow_html=True)
    context=render_identity_controls(LocalProfileStore(os.getenv('SLOTHLAB_PROFILE_DIR','artifacts/profiles')),
        os.getenv('SLOTHLAB_DB_PATH','artifacts/slothlab.sqlite'),os.getenv('SLOTHLAB_ARTIFACT_DIR','artifacts'),
        os.getenv('SLOTHLAB_JOB_DIR','artifacts/jobs'))
    if context.mode=='workspace' and os.getenv('SLOTHLAB_STORAGE_BACKEND')=='document':
        context=replace(context,storage_backend='document')
    st.markdown(theme_css(context.theme),unsafe_allow_html=True)
    previous=st.session_state.get('_workspace_id')
    if previous and previous != context.workspace_id:
        preserved={'history_mode','appearance_theme','slothlab_browser_preferences','_workspace_id',
                   '_guest_directory','_guest_document_override','_guest_artifact_override','_guest_import_hash'}
        for key in list(st.session_state):
            if key not in preserved and not str(key).startswith(('_identity','_browser_profile')):
                del st.session_state[key]
    st.session_state['_workspace_id']=context.workspace_id
    if context.mode=='workspace':
        db_path=st.sidebar.text_input('Research memory',value=str(context.db_path),key='memory_path',help='Local research memory. Opening an empty path does not start research.')
        artifact_dir=st.sidebar.text_input('Artifact directory',value=str(context.artifact_dir),key='artifact_directory')
    else:
        db_path=str(context.db_path)
        artifact_dir=str(context.artifact_dir)
        st.sidebar.text('History · '+context.profile_label)
    if context.mode=='guest' and st.session_state.get('_guest_document_override'):
        db_path=st.session_state['_guest_document_override']
        artifact_dir=st.session_state['_guest_artifact_override']
    manager=job_manager(context.job_dir)
    jobs = get_jobs(manager)
    active = [job for job in jobs if job.get('state') in ACTIVE_JOBS]
    st.sidebar.caption(f"{len(active)} active background {'run' if len(active)==1 else 'runs'}")
    st.sidebar.markdown('---')
    st.sidebar.caption('LOCAL-FIRST · EVIDENCE-GROUNDED')
    st.sidebar.caption('Only registered scientific procedures run. Model inference stays on your configured Ollama endpoint.')
    st.markdown('<div class="lab-eyebrow">AUTONOMOUS SCIENTIFIC RESEARCH</div>',unsafe_allow_html=True)
    st.title('Research workspace')
    if st.session_state.get('launch_flash'):
        st.success(st.session_state.pop('launch_flash'))
    st.markdown('<div class="lab-hero"><div class="lab-pill">SLOTHLAB + LAZYLOOP</div><h2>Ask better questions.<br>Make every experiment count.</h2><p>A local laboratory for hypothesis-driven investigation, reproducible measurements, and thoughtful use of compute.</p></div>',unsafe_allow_html=True)
    render_guest_import(context,bool(active))
    research,new,comparisons,guide = st.tabs(['Research','New investigation','Comparisons','Learn & help'])
    with research:
        @st.fragment(run_every=3 if active else None)
        def live_research():
            live_jobs = get_jobs(manager)
            launched_job = next((j for j in live_jobs if j.get('id') == st.session_state.get('last_launched_job')), None)
            if launched_job and launched_job.get('session_id') and st.session_state.get('followed_job') != launched_job['id']:
                st.session_state['selected_session'] = launched_job['session_id']
                st.session_state['followed_job'] = launched_job['id']
            render_jobs(manager,live_jobs)
            if active and not any(job.get('state') in ACTIVE_JOBS for job in live_jobs):
                # Refresh the outer form/interval state when the last worker ends.
                st.rerun()
            if not Path(db_path).is_file():
                show_empty()
                return
            try:
                with open_repository(db_path,context.storage_backend) as repo:
                    sessions = repo.list_sessions()
                    if not sessions:
                        show_empty()
                        return
                    choices = [s.id for s in reversed(sessions)]
                    sessions_by_id = {s.id:s for s in sessions}
                    if st.session_state.get('selected_session') not in choices:
                        st.session_state['selected_session'] = choices[0]
                    labels = {sid: f"{repo.get_objective(sessions_by_id[sid].objective_id).title} · {sessions_by_id[sid].state.lower()} · {sid[:8]}" for sid in choices}
                    identity = st.selectbox('Research session',choices,key='selected_session',format_func=labels.get)
                    st.button('Refresh recorded state',key='refresh_research')
                    render_investigation(repo,identity,manager,live_jobs,artifact_dir)
            except (OSError,ValueError,KeyError,sqlite3.Error) as exc:
                st.error(f'Cannot read research memory: {exc}')
        live_research()
    with new:
        launch_form(manager,db_path,artifact_dir,len(active),context.storage_backend)
    with comparisons:
        render_comparisons(artifact_dir,manager,len(active),context.storage_backend,context.mode!='workspace')
    with guide:
        render_learning_center()
    st.markdown('<div class="lab-footer">SlothLab · Reproducible by design. Uncertainty by default. All displayed findings come from recorded evidence.</div>',unsafe_allow_html=True)


if __name__ == '__main__':
    main()
