"""Shared contracts. Extra fields and non-finite numbers are always rejected."""
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True, allow_inf_nan=False)


class Parameters(Schema):
    train_prevalence: float = Field(default=0.5, gt=0.01, lt=0.99)
    evaluation_prevalence: float = Field(default=0.2, gt=0.01, lt=0.99)
    sample_size: int = Field(default=1000, ge=100, le=20000, strict=True)
    feature_count: int = Field(default=6, ge=2, le=50, strict=True)
    class_separation: float = Field(default=1.0, gt=0, le=5)
    noise: float = Field(default=0.0, ge=0, le=0.2)
    logistic_c: float = Field(default=1.0, gt=0, le=100)
    probability_temperature: float = Field(default=1.0, ge=0.25, le=4)


class Budget(Schema):
    max_experiments: int = Field(default=12, ge=1, le=1000)
    max_rounds: int = Field(default=20, ge=1, le=1000)
    max_candidates: int = Field(default=5, ge=1, le=20)
    wall_seconds: float = Field(default=1200, gt=0)
    max_tokens: int = Field(default=20000, ge=1)
    call_token_reserve: int = Field(default=2000, ge=64)
    repair_attempts: int = Field(default=2, ge=0, le=5)
    no_progress_rounds: int = Field(default=3, ge=1)
    experiment_timeout: float = Field(default=30, gt=0, le=600)
    memory_mb: int = Field(default=2048, ge=256)
    minimum_replications: int = Field(default=3, ge=3)


class ResearchObjective(Schema):
    id: str = Field(default_factory=uid)
    title: str = "Prior correction under label shift"
    question: str = "When does oracle prior-probability correction improve Brier score under label shift?"
    experiment_family: Literal["prior_correction"] = "prior_correction"
    primary_metric: Literal["delta_brier"] = "delta_brier"
    permitted_parameters: dict[str, list[float | int]] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    success_criteria: dict[str, Any] = Field(default_factory=lambda: {"minimum_replications": 3})


class Hypothesis(Schema):
    id: str = Field(default_factory=uid)
    session_id: str
    statement: str
    falsifiable_prediction: str
    expected_delta_direction: Literal["negative", "positive"] | None = None
    assumptions: list[str] = Field(default_factory=list)
    status: Literal["PROPOSED", "TESTING", "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"] = "PROPOSED"
    created_at: str = Field(default_factory=now)


class ExperimentSpec(Schema):
    id: str = Field(default_factory=uid)
    hypothesis_id: str
    experiment_family: Literal["prior_correction"] = "prior_correction"
    dataset_id: Literal["synthetic-label-shift-v1"] = "synthetic-label-shift-v1"
    protocol_version: Literal["1"] = "1"
    parameters: Parameters = Field(default_factory=Parameters)
    seed: int = Field(ge=0, le=2**31-1, strict=True)
    phase: Literal["exploratory", "confirmatory"] = "exploratory"
    replicate_group: str | None = None
    estimated_compute_seconds: float = Field(default=1, gt=0, le=600)
    rationale: str = Field(min_length=1)


class ExperimentResult(Schema):
    id: str = Field(default_factory=uid)
    experiment_id: str
    fingerprint: str
    status: Literal["COMPLETED", "FAILED"]
    metrics: dict[str, float] = Field(default_factory=dict)
    runtime_seconds: float = Field(ge=0)
    artifact_paths: list[str] = Field(default_factory=list)
    environment_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now)
    error_details: str | None = None


class LazyLoopDecision(Schema):
    experiment_id: str
    session_id: str
    decision: Literal["EXECUTE", "REUSE", "REPLICATE", "DEFER", "REJECT", "STOP"]
    reason: str
    evidence_references: list[str] = Field(default_factory=list)
    priority_score: float = 0
    score_components: dict[str, float] = Field(default_factory=dict)
    estimated_cost: float = 0
    available_budget: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=now)


class ResearchSession(Schema):
    id: str = Field(default_factory=uid)
    objective_id: str
    state: Literal["INITIALIZED", "HYPOTHESIZING", "PLANNING", "VALIDATING", "EXECUTING", "ANALYZING", "REPLANNING", "COMPLETED", "STOPPED", "FAILED"] = "INITIALIZED"
    model_name: str
    mode: Literal["baseline", "cache_only", "lazyloop"] = "lazyloop"
    budget_configuration: Budget = Field(default_factory=Budget)
    budget_consumed: dict[str, Any] = Field(default_factory=lambda: {"experiments": 0, "tokens": 0, "token_reservations": 0, "wall_seconds": 0.0, "cache_hits": 0, "model_calls": 0, "inference_seconds": 0.0})
    iteration_count: int = 0
    no_progress_count: int = 0
    started_at: str = Field(default_factory=now)
    last_checkpoint: str = Field(default_factory=now)
    termination_reason: str | None = None


class HypothesisBatch(Schema):
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)


class Plan(Schema):
    candidates: list[ExperimentSpec] = Field(max_length=20)


class Assessment(Schema):
    hypothesis_id: str
    status: Literal["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"]
    evidence_ids: list[str]
    explanation: str
    revised_statement: str | None = None
    revised_prediction: str | None = None
    revised_direction: Literal["negative", "positive"] | None = None


class Analysis(Schema):
    assessments: list[Assessment]
    next_direction: str
