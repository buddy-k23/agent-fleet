"""Tests for gate evaluation logic."""

from agent_fleet.core.gates import GateResult, evaluate_gate
from agent_fleet.core.workflow import GateConfig


class TestAutomatedGate:
    def test_passes_when_all_checks_pass(self) -> None:
        gate = GateConfig(type="automated", checks=["tests_pass", "lint_clean"])
        check_results = {"tests_pass": True, "lint_clean": True}
        result = evaluate_gate(gate, check_results=check_results)
        assert result.passed is True
        assert result.gate_type == "automated"

    def test_fails_when_check_fails(self) -> None:
        gate = GateConfig(type="automated", checks=["tests_pass"])
        check_results = {"tests_pass": False}
        result = evaluate_gate(gate, check_results=check_results)
        assert result.passed is False
        assert "tests_pass" in result.reason

    def test_fails_when_check_missing(self) -> None:
        gate = GateConfig(type="automated", checks=["tests_pass"])
        check_results: dict[str, bool] = {}
        result = evaluate_gate(gate, check_results=check_results)
        assert result.passed is False

    def test_passes_with_empty_checks(self) -> None:
        gate = GateConfig(type="automated", checks=[])
        result = evaluate_gate(gate, check_results={})
        assert result.passed is True


class TestScoreGate:
    def test_passes_above_threshold(self) -> None:
        gate = GateConfig(type="score", min_score=80)
        result = evaluate_gate(gate, score=85)
        assert result.passed is True

    def test_passes_at_threshold(self) -> None:
        gate = GateConfig(type="score", min_score=80)
        result = evaluate_gate(gate, score=80)
        assert result.passed is True

    def test_fails_below_threshold(self) -> None:
        gate = GateConfig(type="score", min_score=80)
        result = evaluate_gate(gate, score=60)
        assert result.passed is False
        assert "60" in result.reason
        assert "80" in result.reason

    def test_fails_when_no_score_provided(self) -> None:
        gate = GateConfig(type="score", min_score=80)
        result = evaluate_gate(gate)
        assert result.passed is False
        assert "No score" in result.reason


class TestApprovalGate:
    def test_passes_when_approved(self) -> None:
        gate = GateConfig(type="approval")
        result = evaluate_gate(gate, approved=True)
        assert result.passed is True

    def test_fails_when_not_approved(self) -> None:
        gate = GateConfig(type="approval")
        result = evaluate_gate(gate, approved=False)
        assert result.passed is False


class TestCustomGate:
    def test_passes_when_custom_result_true(self) -> None:
        gate = GateConfig(type="custom")
        result = evaluate_gate(gate, custom_result=True)
        assert result.passed is True

    def test_fails_when_custom_result_false(self) -> None:
        gate = GateConfig(type="custom")
        result = evaluate_gate(gate, custom_result=False)
        assert result.passed is False


class TestGateResult:
    def test_gate_result_fields(self) -> None:
        result = GateResult(
            passed=False,
            gate_type="score",
            reason="Score 60 < 80",
            details={"score": 60},
        )
        assert result.passed is False
        assert result.gate_type == "score"
        assert result.details is not None
        assert result.details["score"] == 60

    def test_unknown_gate_type_fails(self) -> None:
        gate = GateConfig(type="unknown_type")
        result = evaluate_gate(gate)
        assert result.passed is False
        assert "Unknown" in result.reason
