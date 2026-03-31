"""Tests for SupabaseProjectRepository."""

from unittest.mock import MagicMock

from agent_fleet.store.supabase_repo import SupabaseProjectRepository


class TestProjectRepoCreate:
    def test_create_inserts_with_user_id(self):
        """Create project inserts user_id and data."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "My Project", "user_id": "user-1"}
        client.table.return_value.insert.return_value.execute.return_value.data = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.create("user-1", {"name": "My Project", "repo_path": "/tmp/repo"})

        insert_payload = client.table.return_value.insert.call_args[0][0]
        assert insert_payload["user_id"] == "user-1"
        assert insert_payload["name"] == "My Project"
        assert result == row


class TestProjectRepoGet:
    def test_get_returns_project(self):
        """Get returns project dict."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "My Project"}
        (
            client.table.return_value.select.return_value.eq.return_value.execute.return_value.data
        ) = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.get("proj-1")
        assert result == row

    def test_get_returns_none_when_missing(self):
        """Get returns None when project not found."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseProjectRepository(client)
        assert repo.get("nonexistent") is None


class TestProjectRepoListByUser:
    def test_list_returns_user_projects(self):
        """List returns projects ordered by created_at desc."""
        client = MagicMock()
        rows = [{"id": "p1"}, {"id": "p2"}]
        chain = client.table.return_value.select.return_value
        chain.eq.return_value.order.return_value.execute.return_value.data = rows

        repo = SupabaseProjectRepository(client)
        result = repo.list_by_user("user-1")
        assert result == rows


class TestProjectRepoUpdate:
    def test_update_sends_data(self):
        """Update sends data dict to Supabase."""
        client = MagicMock()
        row = {"id": "proj-1", "name": "Updated"}
        (
            client.table.return_value.update.return_value.eq.return_value.execute.return_value.data
        ) = [row]

        repo = SupabaseProjectRepository(client)
        result = repo.update("proj-1", {"name": "Updated"})
        assert result == row


class TestProjectRepoDelete:
    def test_delete_removes_project(self):
        """Delete calls Supabase delete."""
        client = MagicMock()
        client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        repo = SupabaseProjectRepository(client)
        repo.delete("proj-1")
        client.table.assert_called_with("projects")
