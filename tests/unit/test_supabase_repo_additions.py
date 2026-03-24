"""Tests for new/updated Supabase repository methods."""

from unittest.mock import MagicMock

from agent_fleet.store.supabase_repo import (
    SupabaseExecutionRepository,
    SupabaseGateResultRepository,
    SupabaseTaskRepository,
)


class TestSupabaseGateResultRepository:
    def test_create_gate_result(self):
        """Insert gate result with all fields."""
        client = MagicMock()
        row = {
            "id": "gr-1",
            "execution_id": "ex-1",
            "gate_type": "automated",
            "passed": True,
            "score": None,
            "details": {"checks": {"tests_pass": True}},
        }
        client.table.return_value.insert.return_value.execute.return_value.data = [row]

        repo = SupabaseGateResultRepository(client)
        result = repo.create(
            execution_id="ex-1",
            gate_type="automated",
            passed=True,
            details={"checks": {"tests_pass": True}},
        )
        assert result == row
        client.table.assert_called_with("gate_results")

    def test_list_by_execution(self):
        """List gate results ordered by created_at."""
        client = MagicMock()
        rows = [{"id": "gr-1"}, {"id": "gr-2"}]
        mock_chain = client.table.return_value.select.return_value
        mock_chain.eq.return_value.order.return_value.execute.return_value.data = rows

        repo = SupabaseGateResultRepository(client)
        result = repo.list_by_execution("ex-1")
        assert result == rows


class TestAtomicPickup:
    def test_atomic_pickup_succeeds(self):
        """Atomic pickup returns True when row is claimed."""
        client = MagicMock()
        mock_chain = client.table.return_value.update.return_value
        mock_chain.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "task-1", "status": "running"}
        ]

        repo = SupabaseTaskRepository(client)
        assert repo.atomic_pickup("task-1") is True

    def test_atomic_pickup_fails_when_already_claimed(self):
        """Atomic pickup returns False when another worker grabbed it."""
        client = MagicMock()
        mock_chain = client.table.return_value.update.return_value
        mock_chain.eq.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseTaskRepository(client)
        assert repo.atomic_pickup("task-1") is False


class TestEnhancedExecutionUpdate:
    def test_update_status_with_tokens_and_files(self):
        """Update execution with tokens_used and files_changed."""
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        repo = SupabaseExecutionRepository(client)
        repo.update_status(
            "ex-1",
            "completed",
            summary="Done",
            tokens_used=5000,
            files_changed=["src/main.py"],
        )
        call_args = client.table.return_value.update.call_args[0][0]
        assert call_args["tokens_used"] == 5000
        assert call_args["files_changed"] == ["src/main.py"]
        assert call_args["status"] == "completed"

    def test_update_status_sets_finished_at_on_completed(self):
        """When status is 'completed', the update dict includes finished_at."""
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        repo = SupabaseExecutionRepository(client)
        repo.update_status("ex-1", "completed")

        call_args = client.table.return_value.update.call_args[0][0]
        assert "finished_at" in call_args
        assert call_args["status"] == "completed"

    def test_update_status_sets_finished_at_on_error(self):
        """When status is 'error', the update dict includes finished_at."""
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        repo = SupabaseExecutionRepository(client)
        repo.update_status("ex-1", "error", summary="Something went wrong")

        call_args = client.table.return_value.update.call_args[0][0]
        assert "finished_at" in call_args
        assert call_args["status"] == "error"

    def test_update_status_no_finished_at_for_running(self):
        """When status is 'running', finished_at must NOT be in the update dict."""
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        repo = SupabaseExecutionRepository(client)
        repo.update_status("ex-1", "running")

        call_args = client.table.return_value.update.call_args[0][0]
        assert "finished_at" not in call_args
        assert call_args["status"] == "running"

    def test_update_status_with_only_status(self):
        """Calling update_status with just status (no optional fields) should work."""
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        repo = SupabaseExecutionRepository(client)
        # Should not raise
        repo.update_status("ex-1", "completed")

        call_args = client.table.return_value.update.call_args[0][0]
        assert call_args["status"] == "completed"
        assert "summary" not in call_args
        assert "tokens_used" not in call_args
        assert "files_changed" not in call_args


class TestGateResultEdgeCases:
    def test_create_gate_result_with_score(self):
        """Create gate result with score=85 and verify it's in the insert payload."""
        client = MagicMock()
        row = {
            "id": "gr-10",
            "execution_id": "ex-5",
            "gate_type": "score",
            "passed": True,
            "score": 85,
            "details": None,
        }
        client.table.return_value.insert.return_value.execute.return_value.data = [row]

        repo = SupabaseGateResultRepository(client)
        result = repo.create(
            execution_id="ex-5",
            gate_type="score",
            passed=True,
            score=85,
        )

        insert_payload = client.table.return_value.insert.call_args[0][0]
        assert insert_payload["score"] == 85
        assert insert_payload["passed"] is True
        assert result == row

    def test_list_by_execution_empty(self):
        """Empty result list returns []."""
        client = MagicMock()
        mock_chain = client.table.return_value.select.return_value
        mock_chain.eq.return_value.order.return_value.execute.return_value.data = []

        repo = SupabaseGateResultRepository(client)
        result = repo.list_by_execution("ex-nonexistent")
        assert result == []
