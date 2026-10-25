"""Presentation helpers operating on measured, persisted research data only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def experiment_frame(data: dict[str, Any]) -> pd.DataFrame:
    specs = {spec['id']: spec for spec in data.get('experiments', [])}
    actions = {d['experiment_id']: d['decision'] for d in data.get('decisions', [])}
    rows = []
    for result in data.get('results', []):
        spec = specs.get(result['experiment_id'], {})
        rows.append({
            'result_id': result['id'], 'experiment_id': result['experiment_id'],
            'hypothesis_id': spec.get('hypothesis_id'), 'seed': spec.get('seed'),
            'phase': spec.get('phase', 'unknown'), 'status': result['status'],
            'action': actions.get(result['experiment_id'], 'RECORDED'),
            'runtime_seconds': result['runtime_seconds'],
            'parameters': json.dumps(spec.get('parameters', {}), sort_keys=True),
            **result.get('metrics', {}),
        })
    return pd.DataFrame(rows)


def comparison_files(artifact_dir: str | Path) -> list[Path]:
    """Discover benchmark products, never manufacture a comparison."""
    root = Path(artifact_dir).resolve()
    return sorted(root.glob('benchmarks/**/comparison.json'), key=lambda p: p.stat().st_mtime, reverse=True) if root.exists() else []


def comparison_frame(content: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for run in content.get('runs', []):
        quality = run.get('quality', {})
        rows.append({
            'scenario': run.get('scenario'), 'trial': run.get('trial'), 'mode': run.get('mode'),
            'executed': run.get('experiment_count'), 'cache_hits': run.get('cache_hits'),
            'wall_seconds': run.get('wall_seconds'), 'model_tokens': run.get('model_tokens'),
            'inference_seconds': run.get('inference_seconds'),
            'quality_coverage': quality.get('quality_score'),
            'scientific_quality': quality.get('scientific_quality_score'),
            'redundant_proposals': run.get('redundant_proposals'),
            'state': run.get('state'),
            'termination_reason': run.get('termination_reason'), 'session_id': run.get('session_id'),
        })
    return pd.DataFrame(rows)


def format_seconds(value: float | int | None) -> str:
    if value is None:
        return 'Unknown'
    seconds = float(value)
    return f'{seconds / 60:.1f} min' if seconds >= 60 else f'{seconds:.1f} s'


def tail_log(path: str | None, limit: int = 12000) -> str:
    if not path:
        return ''
    filename = Path(path)
    if not filename.is_file():
        return ''
    with filename.open('rb') as source:
        source.seek(max(0, filename.stat().st_size-limit))
        return source.read(limit).decode('utf-8', errors='replace')


def proposal_frame(data: dict[str, Any]) -> pd.DataFrame:
    """Trace proposals to original measurements without inventing cache results."""
    specs = {spec['id']: spec for spec in data.get('experiments', [])}
    results = {result['id']: result for result in data.get('results', [])}
    executed = {result['experiment_id']: result for result in results.values()}
    rows = []
    for decision in data.get('decisions', []):
        proposal_id = decision['experiment_id']
        spec = specs.get(proposal_id, {})
        result = executed.get(proposal_id)
        if decision['decision'] == 'REUSE':
            result = next((results[ref] for ref in decision.get('evidence_references', []) if ref in results), None)
        rows.append({
            'experiment_id': proposal_id, 'action': decision['decision'],
            'seed': spec.get('seed'), 'phase': spec.get('phase'),
            'result_id': result['id'] if result else None,
            'status': result['status'] if result else decision['decision'],
            'delta_brier': result.get('metrics', {}).get('delta_brier') if result else None,
            'delta_log_loss': result.get('metrics', {}).get('delta_log_loss') if result else None,
            'runtime_seconds': result.get('runtime_seconds') if result and decision['decision'] != 'REUSE' else None,
            'reason': decision['reason'], 'parameters': json.dumps(spec.get('parameters', {}), sort_keys=True),
        })
    return pd.DataFrame(rows)
