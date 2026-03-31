"""Tests for checkpointer factory — creates PostgresSaver from env vars."""

from unittest.mock import MagicMock, patch

import pytest

from agent_fleet.worker.checkpointer import get_checkpointer


def test_get_checkpointer_creates_saver_with_db_url():
    """Creates PostgresSaver using SUPABASE_DB_URL env var."""
    with (
        patch.dict(
            "os.environ",
            {"SUPABASE_DB_URL": "postgresql://postgres:pass@db.example.com:5432/postgres"},
        ),
        patch("agent_fleet.worker.checkpointer.PostgresSaver") as mock_cls,
    ):
        mock_saver = MagicMock()
        mock_cls.from_conn_string.return_value = mock_saver

        result = get_checkpointer()

        mock_cls.from_conn_string.assert_called_once_with(
            "postgresql://postgres:pass@db.example.com:5432/postgres"
        )
        assert result is mock_saver


def test_get_checkpointer_raises_when_not_configured():
    """Raises RuntimeError if SUPABASE_DB_URL not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
            get_checkpointer()


def test_get_checkpointer_calls_setup():
    """Calls setup() on the saver to create checkpoint tables."""
    with (
        patch.dict(
            "os.environ",
            {"SUPABASE_DB_URL": "postgresql://postgres:pass@localhost:5432/postgres"},
        ),
        patch("agent_fleet.worker.checkpointer.PostgresSaver") as mock_cls,
    ):
        mock_saver = MagicMock()
        mock_cls.from_conn_string.return_value = mock_saver

        get_checkpointer()

        mock_saver.setup.assert_called_once()
