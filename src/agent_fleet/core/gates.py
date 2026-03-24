"""Gate evaluation logic for quality checkpoints."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from agent_fleet.core.workflow import GateConfig

logger = structlog.get_logger()


@dataclass
class GateResult:
    """Result of a gate evaluation."""

    passed: bool
    gate_type: str
    reason: str
    details: dict[str, Any] | None = field(default=None)


def evaluate_gate(
    gate: GateConfig,
    check_results: dict[str, bool] | None = None,
    score: int | None = None,
    approved: bool | None = None,
    custom_result: bool | None = None,
) -> GateResult:
    """Evaluate a quality gate and return the result."""
    if gate.type == "automated":
        return _evaluate_automated(gate, check_results or {})
    elif gate.type == "score":
        return _evaluate_score(gate, score)
    elif gate.type == "approval":
        return _evaluate_approval(approved)
    elif gate.type == "custom":
        return GateResult(
            passed=bool(custom_result),
            gate_type="custom",
            reason="Custom gate evaluation",
        )
    else:
        return GateResult(
            passed=False,
            gate_type=gate.type,
            reason=f"Unknown gate type: {gate.type}",
        )


def _evaluate_automated(gate: GateConfig, check_results: dict[str, bool]) -> GateResult:
    """Evaluate automated gate — all checks must pass."""
    failed_checks = [name for name in gate.checks if not check_results.get(name, False)]
    if failed_checks:
        logger.info("gate_automated_failed", failed=failed_checks)
        return GateResult(
            passed=False,
            gate_type="automated",
            reason=f"Failed checks: {', '.join(failed_checks)}",
            details={"check_results": check_results},
        )
    return GateResult(passed=True, gate_type="automated", reason="All checks passed")


def _evaluate_score(gate: GateConfig, score: int | None) -> GateResult:
    """Evaluate score gate — score must meet min_score threshold."""
    if score is None:
        return GateResult(passed=False, gate_type="score", reason="No score provided")
    min_score = gate.min_score or 0
    if score >= min_score:
        return GateResult(
            passed=True,
            gate_type="score",
            reason=f"Score {score} >= {min_score}",
        )
    logger.info("gate_score_failed", score=score, min_score=min_score)
    return GateResult(
        passed=False,
        gate_type="score",
        reason=f"Score {score} < {min_score}",
        details={"score": score, "min_score": min_score},
    )


def _evaluate_approval(approved: bool | None) -> GateResult:
    """Evaluate approval gate — must be explicitly approved."""
    if approved:
        return GateResult(passed=True, gate_type="approval", reason="Approved")
    return GateResult(passed=False, gate_type="approval", reason="Not approved")
