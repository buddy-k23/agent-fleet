"""Supabase integration smoke test — verifies auth, DB, repos work together."""

import os

import pytest

# Skip if Supabase not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"),
    reason="SUPABASE_URL not set — skipping Supabase integration tests",
)


@pytest.fixture
def svc_client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@pytest.fixture
def anon_client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


class TestSupabaseConnection:
    def test_tables_exist(self, svc_client) -> None:  # type: ignore[no-untyped-def]
        tables = [
            "profiles",
            "agents",
            "workflows",
            "tasks",
            "executions",
            "gate_results",
            "events",
        ]
        for table in tables:
            result = svc_client.table(table).select("*").limit(1).execute()
            assert isinstance(result.data, list), f"Table {table} query failed"

    def test_agents_seeded(self, svc_client) -> None:  # type: ignore[no-untyped-def]
        result = svc_client.table("agents").select("name").execute()
        names = {r["name"] for r in result.data}
        assert "Architect" in names
        assert "Backend Dev" in names

    def test_workflows_seeded(self, svc_client) -> None:  # type: ignore[no-untyped-def]
        result = svc_client.table("workflows").select("name").execute()
        names = {r["name"] for r in result.data}
        assert "Full Development Pipeline" in names


class TestSupabaseRepos:
    def test_task_crud(self, svc_client) -> None:  # type: ignore[no-untyped-def]
        import uuid

        from agent_fleet.store.supabase_repo import SupabaseTaskRepository

        repo = SupabaseTaskRepository(svc_client)

        users = svc_client.auth.admin.list_users()
        if not users:
            pytest.skip("No users in Supabase")
        user_id = str(users[0].id)
        task_id = str(uuid.uuid4())

        # Create
        task = repo.create(
            task_id=task_id,
            user_id=user_id,
            repo_path="/test/repo",
            description="Supabase integration test",
            workflow="default",
        )
        assert task["id"] == task_id

        # Get
        fetched = repo.get(task_id)
        assert fetched is not None
        assert fetched["description"] == "Supabase integration test"

        # Update
        repo.update_status(task_id, "running")
        updated = repo.get(task_id)
        assert updated["status"] == "running"

        # Cleanup
        svc_client.table("tasks").delete().eq("id", task_id).execute()
