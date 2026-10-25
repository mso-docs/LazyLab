"""Research reports consist of persisted observations and conservative checks."""
from __future__ import annotations

import json
import csv
import html
import io
from uuid import uuid4
from pathlib import Path
from slothlab.evaluation.quality import assess_quality
from slothlab.schemas import now


def report_data(repo, session_id: str) -> dict:
    session = repo.get_session(session_id)
    objective = repo.get_objective(session.objective_id)
    results = repo.results(session_id)
    specs = {s.id: s for s in repo.specs(session_id)}
    for result in results:
        if result.experiment_id not in specs:
            try:
                specs[result.experiment_id] = repo.get_spec(result.experiment_id)
            except KeyError:
                pass
    decisions = repo.decisions(session_id)
    own_spec_ids={s.id for s in repo.specs(session_id)}
    executed_results=[r for r in results if r.experiment_id in own_spec_ids]
    resource_usage=[r.environment_metadata.get('resource_usage',{}) for r in executed_results]
    cpu_seconds=sum(r['cpu_seconds'] for r in resource_usage) if all(r.get('cpu_seconds') is not None for r in resource_usage) else None
    peak_memory_bytes=max((r['peak_memory_bytes'] for r in resource_usage),default=None) if all(r.get('peak_memory_bytes') is not None for r in resource_usage) else None
    missing_execution_receipts=session.budget_consumed.get('experiments',0)>len(executed_results)
    if missing_execution_receipts:
        cpu_seconds=None
        peak_memory_bytes=None
    successful = [r for r in results if r.status == 'COMPLETED']
    budget = session.budget_consumed
    from slothlab.lazyloop.fingerprint import fingerprint
    fingerprints = [fingerprint(s) for s in repo.specs(session_id)]
    duplicate_count = len(fingerprints)-len(set(fingerprints))
    assessments = [e['payload'] for e in repo.events(session_id, 'verified_assessment')]
    # Missing telemetry is unknown rather than a measured zero.
    tokens = budget.get('tokens')
    if budget.get('token_usage_missing') or budget.get('tokens_unknown'):
        tokens = None
    quality=assess_quality(list(specs.values()),results,session.budget_configuration.minimum_replications,
                           hypotheses=repo.hypotheses(session_id),interpretations=[e['payload'] for e in repo.events(session_id,'interpretation')],
                           verified_assessments=assessments)
    minimum=session.budget_configuration.minimum_replications
    supported_findings=sum(len(group['independent_confirmatory_seeds'])>=minimum and (
        group['protocol_assessment'] in {'CONSISTENT_IMPROVEMENT','CONSISTENT_REGRESSION'} or
        (group['confirmatory_mean_delta_brier'] is not None and abs(group['confirmatory_mean_delta_brier'])<=1e-10 and
         group['confirmatory_std_delta_brier'] is not None and abs(group['confirmatory_std_delta_brier'])<=1e-10)) for group in quality['groups'])
    audits=[event['payload'] for event in repo.events(session_id,'termination_audit')]
    audited=[audit['known_protocol_premature_stop'] for audit in audits if type(audit.get('known_protocol_premature_stop')) is bool]
    premature_stops=sum(audited) if audited else None
    return {
        'generated_at': now(),
        'session': session.model_dump(mode='json'),
        'objective': objective.model_dump(mode='json'),
        'hypotheses': [h.model_dump(mode='json') for h in repo.hypotheses(session_id)],
        'experiments': [s.model_dump(mode='json') for s in specs.values()],
        'results': [r.model_dump(mode='json') for r in results],
        'decisions': [d.model_dump(mode='json') for d in decisions],
        'interpretations': [e['payload'] for e in repo.events(session_id, 'interpretation')],
        'verified_assessments': assessments,
        'model_provenance':[event['payload'] for event in repo.events(session_id,'model_provenance')],
        'termination_audits':audits,
        'telemetry': {
            'mode': session.mode,
            'executed_experiments': budget.get('experiments', 0),
            'successful_measurements': len(successful),
            'supported_findings':supported_findings,
            'premature_stops':premature_stops,
            'failed_execution_attempts':None if missing_execution_receipts else sum(result.status=='FAILED' for result in executed_results),
            'cache_hits': sum(d.decision == 'REUSE' for d in decisions),
            'redundant_proposals': duplicate_count,
            'failed_measurements': sum(r.status == 'FAILED' for r in results),
            'rejected_proposals': sum(d.decision == 'REJECT' for d in decisions),
            'model_tokens': tokens,
            'model_calls': budget.get('model_calls'),
            'inference_seconds': budget.get('inference_seconds'),
            'wall_seconds': budget.get('wall_seconds'),
            'execution_seconds': None if missing_execution_receipts else sum(r.runtime_seconds for r in executed_results),
            'scientific_cpu_seconds':cpu_seconds,
            'peak_memory_bytes':peak_memory_bytes,
            'termination_reason': session.termination_reason,
            'count_definitions':{'supported_findings':'Distinct confirmed fixed-condition groups with consistently directional or effectively zero deltas under the minimum independent replication protocol; not general scientific truth.',
                                 'premature_stops':'Detected known-protocol soft-stop violations in persisted termination audits; null without an audit, not a claim of universal optimal stopping.',
                                 'failed_execution_attempts':'Persisted FAILED local execution receipts; null if a charged execution has no result receipt.'},
        },
        'quality': quality,
    }


def generate_report(repo, session_id: str, artifact_dir: str | Path) -> Path:
    data = report_data(repo, session_id)
    # Session IDs are not allowed to create arbitrary directories.
    if not session_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in session_id):
        raise ValueError('Invalid session identifier for artifact path')
    folder = Path(artifact_dir).resolve() / session_id / 'reports'
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / 'metrics.json'
    _atomic_write(json_path, json.dumps(data, indent=2, allow_nan=False) + '\n')
    session = data['session']
    lines = [
        f"# SlothLab research report: {data['objective']['title']}", '',
        data['objective']['question'], '',
        f"Session: `{session_id}` · model: `{session['model_name']}` · mode: `{session['mode']}`", '',
        f"State: **{session['state']}**. Termination reason: {session['termination_reason'] or 'Investigation in progress' }.", '',
        'The protocol supplies true evaluation prevalence as an oracle input. These synthetic results do not establish that deployment prevalence is known.', '',
        '## Measured evidence', '',
        'Negative delta means correction reduced the loss. Each row is a stored measurement; reuse does not create an independent replication.', '',
        '| Result ID | Experiment ID | Status | Baseline Brier | Corrected Brier | Δ Brier | Δ log loss | Runtime (s) |',
        '|---|---|---|---:|---:|---:|---:|---:|',
    ]
    for result in data['results']:
        m = result['metrics']
        fmt = lambda k: f"{m[k]:.8g}" if k in m else '—'
        lines.append(f"| `{result['id']}` | `{result['experiment_id']}` | {result['status']} | {fmt('baseline_brier')} | {fmt('corrected_brier')} | {fmt('delta_brier')} | {fmt('delta_log_loss')} | {result['runtime_seconds']:.4f} |")
    if not data['results']:
        lines.append('| — | — | No measurements | — | — | — | — | — |')
    lines += ['', '## Hypotheses and uncertainty', '']
    for h in data['hypotheses']:
        lines += [f"- **{h['status']}** (`{h['id']}`): {h['statement']}", f"  Prediction: {h['falsifiable_prediction']}"]
        for assessment in data['verified_assessments']:
            if assessment.get('hypothesis_id') == h['id']:
                refs=', '.join('`'+identity+'`' for identity in assessment.get('evidence_ids',[])) or 'none'
                lines += [f"  Deterministic assessment: {assessment.get('reason','No reason stored')} Evidence: {refs}."]
    lines += ['', 'Free-form model interpretations are unverified proposals. Hypotheses without a predeclared expected_delta_direction remain INCONCLUSIVE. Explicit directional predictions are assessed deterministically using verified measurements and independent seeds; these statuses do not establish a general law. The protocol checks below assess measured directions under fixed conditions.', '', '## Deterministic protocol checks', '']
    quality = data['quality']
    for group in quality['groups']:
        refs = ', '.join(f'`{i}`' for i in group['confirmatory_result_ids']) or 'none'
        lines += [f"- {group['protocol_assessment']}: {len(group['independent_confirmatory_seeds'])} independent confirmatory seeds; mean delta Brier {group['confirmatory_mean_delta_brier']}; 95% Student-t interval {group['confirmatory_delta_brier_ci95']}; evidence: {refs}."]
    if not quality['groups']:
        lines.append('Evidence insufficient: no valid completed measurements.')
    lines += ['', f"Evidence-coverage proxy: {quality['quality_score']:.3f}. {quality['quality_score_definition']}", '']
    lines += [f'- {limitation}' for limitation in quality['limitations']]
    lines += ['', f"Scientific rubric score: {quality['scientific_quality_score']:.3f}. {quality['scientific_quality_score_definition']}", '', '### Expected controls and claim audit', '', f"Unjustified established claims: {quality['unjustified_established_claims']}. Invalid measurements: {len(quality['invalid_result_ids'])}."]
    for check in quality['control_checks']:
        lines.append(f"- {check['check']}: {'PASS' if check['passed'] else 'FAIL'}; evidence `{check['result_id']}`.")
    lines += ['', '## Resource telemetry', '', '```json', json.dumps(data['telemetry'], indent=2), '```', '', 'Unknown token usage is represented as null. Scientific runtime excludes model inference; end-to-end wall time is reported separately.', '', '## Provenance and decisions', '']
    for decision in data['decisions']:
        lines.append(f"- `{decision['experiment_id']}`: **{decision['decision']}** — {decision['reason']} Evidence: {', '.join(decision['evidence_references']) or 'none'}.")
    for result in data['results']:
        lines.append(f"- Result `{result['id']}` fingerprint `{result['fingerprint']}`; artifacts: {', '.join(result['artifact_paths']) or 'none'}.")
    lines += ['', 'Full parameters, environment metadata, decision features and machine-readable measurements are in `metrics.json`.', '']
    path = folder / 'report.md'
    _atomic_write(path, '\n'.join(lines))
    _write_additional_exports(folder, data)
    return path


def _atomic_write(path, content):
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(content)
    temporary.replace(path)


def _write_additional_exports(folder, data):
    columns=['result_id','experiment_id','seed','phase','status','baseline_brier','corrected_brier','delta_brier','baseline_log_loss','corrected_log_loss','delta_log_loss','runtime_seconds','parameters']
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=columns)
    writer.writeheader()
    specs={s['id']:s for s in data['experiments']}
    for result in data['results']:
        spec=specs.get(result['experiment_id'],{})
        row={'result_id':result['id'],'experiment_id':result['experiment_id'],'seed':spec.get('seed'),'phase':spec.get('phase'),
                         'status':result['status'],'runtime_seconds':result['runtime_seconds'],'parameters':json.dumps(spec.get('parameters',{})),
                         **{k:v for k,v in result['metrics'].items() if k in columns}}
        writer.writerow({key:("'"+value if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')) else value) for key,value in row.items()})
    _atomic_write(folder/'experiments.csv',buffer.getvalue())
    escape=lambda value:html.escape(str(value))
    table_rows=[]
    for result in data['results']:
        metrics=result['metrics']
        values=[result['id'],specs.get(result['experiment_id'],{}).get('seed','—'),result['status'],
                metrics.get('baseline_brier','—'),metrics.get('corrected_brier','—'),metrics.get('delta_brier','—'),result['runtime_seconds']]
        table_rows.append('<tr>'+''.join('<td>'+escape(f'{v:.7g}' if isinstance(v,float) else v)+'</td>' for v in values)+'</tr>')
    hypotheses=''.join('<li><strong>'+escape(h['status'])+'</strong> '+escape(h['statement'])+'<br><small>'+escape(h['falsifiable_prediction'])+'</small></li>' for h in data['hypotheses'])
    quality=data['quality']; telemetry=data['telemetry']; session=data['session']
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SlothLab research report</title>
<style>body{{font:15px/1.6 system-ui,sans-serif;background:#f3f5f8;color:#172239;margin:0}}main{{max-width:1100px;margin:40px auto;padding:32px;background:white;border:1px solid #dde4ee;border-radius:20px}}.eyebrow{{color:#06786b;font-weight:700;letter-spacing:.12em;font-size:12px}}h1{{font-size:34px;line-height:1.15}}h2{{margin-top:32px}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{flex:1;min-width:160px;border:1px solid #e0e7ef;border-radius:12px;padding:16px}}.card b{{display:block;font-size:25px}}.note{{background:#edf7f5;border-left:4px solid #108577;padding:14px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #e4e9f0}}td:first-child{{font:11px monospace;word-break:break-all}}th{{background:#f5f7fa}}small,footer{{color:#5b6a7f}}pre{{overflow:auto;background:#f5f7fa;padding:16px;border-radius:12px}}li{{margin:12px 0}}@media print{{body{{background:white}}main{{margin:0;border:0;padding:0}}}}</style>
<main><div class="eyebrow">SLOTHLAB · RESEARCH RECORD</div><h1>{escape(data['objective']['title'])}</h1><p>{escape(data['objective']['question'])}</p>
<p><strong>{escape(session['state'])}</strong> · {escape(session['model_name'])} · {escape(session['mode'])}</p><p>{escape(session['termination_reason'] or 'Investigation in progress')}</p>
<div class="cards"><div class="card">Executed<b>{escape(telemetry['executed_experiments'])}</b></div><div class="card">Exact reuses<b>{escape(telemetry['cache_hits'])}</b></div><div class="card">Model tokens<b>{escape(telemetry['model_tokens'] if telemetry['model_tokens'] is not None else 'Unknown')}</b></div><div class="card">Scientific rubric<b>{quality['scientific_quality_score']:.3f}</b></div></div>
<p class="note">True evaluation prevalence is an oracle input. Negative delta means lower loss. A finite benchmark score is not proof of scientific truth; hypotheses require independent evidence.</p>
<h2>Measured evidence</h2><div style="overflow:auto"><table><thead><tr><th>Result ID</th><th>Seed</th><th>Status</th><th>Baseline Brier</th><th>Corrected Brier</th><th>Delta Brier</th><th>Seconds</th></tr></thead><tbody>{''.join(table_rows) or '<tr><td colspan="7">No measurements</td></tr>'}</tbody></table></div>
<h2>Hypotheses and uncertainty</h2><ul>{hypotheses or '<li>No hypotheses recorded</li>'}</ul><h2>Deterministic evidence audit</h2><pre>{escape(json.dumps(quality,indent=2))}</pre>
<h2>Reproducibility</h2><p>Full parameters, artifact fingerprints, environment versions, measured results and decision receipts accompany this report in metrics.json and experiments.csv.</p><footer>Session {escape(session['id'])} · Generated {escape(data['generated_at'])}</footer></main></html>'''
    _atomic_write(folder/'report.html',body)
