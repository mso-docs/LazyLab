"""Validated configuration, with environment overrides for local paths and inference."""
import os
import math
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import yaml
from pydantic import Field
from slothlab.schemas import Schema, ResearchObjective, Budget, Parameters


class Config(Schema):
    objective: ResearchObjective = Field(default_factory=ResearchObjective)
    budget: Budget = Field(default_factory=Budget)
    model: str | None = None
    base_url: str = "http://localhost:11434"
    inference_timeout_seconds: float = Field(default=300, gt=0, le=1200)
    inference_context_tokens: int = Field(default=8192, ge=2048, le=131072)
    inference_threads: int | None = Field(default=None, ge=1, le=256)
    inference_thinking: bool | None = None
    execution_isolation: Literal["auto", "subprocess", "bubblewrap"] = "auto"
    db_path: str = "artifacts/slothlab.sqlite"
    storage_backend: Literal['sqlite','document'] = 'sqlite'
    artifact_dir: str = "artifacts"
    mode: Literal["baseline", "cache_only", "lazyloop"] = "lazyloop"
    cost_penalty: float = Field(default=0.25, ge=0, le=1)
    exploratory_seeds: list[int] = Field(default_factory=lambda: list(range(100)))
    confirmatory_seeds: list[int] = Field(default_factory=lambda: list(range(10000, 10020)))

    def model_post_init(self, context):
        if self.storage_backend=='document' and self.db_path=='artifacts/slothlab.sqlite':
            self.db_path='artifacts/research.json'
        endpoint=urlsplit(self.base_url)
        if endpoint.scheme not in {'http','https'} or not endpoint.hostname or endpoint.username or endpoint.password:
            raise ValueError('base_url must be an HTTP(S) endpoint without embedded credentials')
        if not self.db_path.strip() or not self.artifact_dir.strip():
            raise ValueError('Database and artifact paths must not be empty')
        if set(self.exploratory_seeds) & set(self.confirmatory_seeds):
            raise ValueError("Exploratory and confirmatory seeds must be disjoint")
        if not self.exploratory_seeds or not self.confirmatory_seeds:
            raise ValueError("Both seed partitions must be non-empty")
        if any(type(s) is not int or s < 0 or s >= 2**31 for s in self.exploratory_seeds + self.confirmatory_seeds):
            raise ValueError("Seeds must be nonnegative 31-bit integers")
        unknown = set(self.objective.permitted_parameters) - set(Parameters.model_fields)
        if unknown:
            raise ValueError(f"Unknown permitted parameters: {sorted(unknown)}")
        for key, values in self.objective.permitted_parameters.items():
            if not values:
                raise ValueError(f"Permitted parameter {key} has no allowed values")
            for value in values:
                Parameters.model_validate({key: value})
        constraints = self.objective.constraints
        if set(constraints) - {"parameter_bounds", "max_estimated_compute_seconds", "allowed_phases", "require_replication_group"}:
            raise ValueError("Unsupported objective constraint; use parameter_bounds, max_estimated_compute_seconds, allowed_phases, or require_replication_group")
        if not isinstance(constraints.get("parameter_bounds", {}), dict):
            raise ValueError("parameter_bounds must be a mapping")
        for parameter, bounds in constraints.get("parameter_bounds", {}).items():
            if parameter not in Parameters.model_fields or not isinstance(bounds, dict) or set(bounds)-{"min", "max"}:
                raise ValueError("Invalid parameter_bounds constraint")
            for value in bounds.values():
                if type(value) not in {int, float} or not math.isfinite(value):
                    raise ValueError("Parameter bounds must be finite numbers")
            if bounds.get("min", float('-inf')) > bounds.get("max", float('inf')):
                raise ValueError("Parameter minimum exceeds maximum")
            allowed=self.objective.permitted_parameters.get(parameter)
            if allowed and not any(bounds.get('min',float('-inf')) <= value <= bounds.get('max',float('inf')) for value in allowed):
                raise ValueError(f'Authorized domain for {parameter} is empty after applying bounds')
        if "max_estimated_compute_seconds" in constraints:
            value = constraints["max_estimated_compute_seconds"]
            if type(value) not in {int, float} or not 0 < value <= 600:
                raise ValueError("max_estimated_compute_seconds must be positive and at most 600")
        if "allowed_phases" in constraints:
            phases = constraints["allowed_phases"]
            if not isinstance(phases, list) or not phases or any(p not in {"exploratory", "confirmatory"} for p in phases):
                raise ValueError("allowed_phases must contain exploratory and/or confirmatory")
        if "require_replication_group" in constraints and type(constraints["require_replication_group"]) is not bool:
            raise ValueError("require_replication_group must be boolean")
        criteria = self.objective.success_criteria
        if set(criteria) - {"minimum_replications", "minimum_exploratory_experiments", "minimum_conditions", "require_confirmation", "minimum_confirmatory_groups", "effect_direction", "effect_tolerance"}:
            raise ValueError("Unsupported success criterion")
        minimum = criteria.get("minimum_replications", 3)
        if type(minimum) is not int or minimum < 3:
            raise ValueError("minimum_replications must be an integer of at least three")
        self.budget.minimum_replications = max(self.budget.minimum_replications, minimum)
        for name in ("minimum_exploratory_experiments", "minimum_conditions", "minimum_confirmatory_groups"):
            if name in criteria and (type(criteria[name]) is not int or criteria[name] < 1):
                raise ValueError(f"{name} must be a positive integer")
        if "require_confirmation" in criteria and type(criteria["require_confirmation"]) is not bool:
            raise ValueError("require_confirmation must be boolean")
        if criteria.get("effect_direction", "either") not in {"negative", "positive", "either", "zero"}:
            raise ValueError("Unsupported effect_direction")
        tolerance = criteria.get("effect_tolerance", 1e-10)
        if type(tolerance) not in {int, float} or not 0 <= tolerance <= 1:
            raise ValueError("effect_tolerance must be between zero and one")
        required_candidates=self.budget.minimum_replications*criteria.get('minimum_confirmatory_groups',1)
        if criteria.get('require_confirmation') and self.budget.max_candidates < required_candidates:
            raise ValueError('Final confirmation requires max_candidates at least minimum_replications times minimum_confirmatory_groups')


def load_config(path: str | Path | None = None) -> Config:
    from slothlab.assets import asset_path
    try:
        data = yaml.safe_load(asset_path(path).read_text()) if path else {}
    except yaml.YAMLError as exc:
        raise ValueError(f'Invalid YAML configuration: {exc}') from exc
    data = data or {}
    if not isinstance(data,dict):
        raise ValueError('Configuration must be a YAML mapping')
    for env, key in [("OLLAMA_MODEL", "model"), ("OLLAMA_BASE_URL", "base_url"), ("SLOTHLAB_DB_PATH", "db_path"), ("SLOTHLAB_ARTIFACT_DIR", "artifact_dir"),('SLOTHLAB_STORAGE_BACKEND','storage_backend')]:
        if os.getenv(env):
            data[key] = os.environ[env]
    return Config.model_validate(data)
