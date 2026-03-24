"""Tests for API dependency injection — Supabase clients + JWT auth."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from agent_fleet.api.deps import (
    _get_anon_client,
    get_current_user,
    get_service_client,
    get_supabase_client,
)


@pytest.fixture(autouse=True)
def clear_lru_caches():
    """Clear lru_cache on client factories before each test."""
    _get_anon_client.cache_clear()
    get_service_client.cache_clear()
    yield
    _get_anon_client.cache_clear()
    get_service_client.cache_clear()


def test_get_supabase_client_returns_client_when_configured():
    """Anon client created from SUPABASE_URL + SUPABASE_ANON_KEY."""
    with patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "anon-key"},
    ), patch("agent_fleet.api.deps.create_client") as mock_create:
        mock_create.return_value = MagicMock()
        client = get_supabase_client()
        mock_create.assert_called_once_with(
            "https://test.supabase.co", "anon-key"
        )
        assert client is not None


def test_get_supabase_client_raises_when_not_configured():
    """Raises RuntimeError if env vars missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Supabase not configured"):
            get_supabase_client()


def test_get_service_client_uses_service_role_key():
    """Service client uses SUPABASE_SERVICE_ROLE_KEY."""
    with patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key",
        },
    ), patch("agent_fleet.api.deps.create_client") as mock_create:
        mock_create.return_value = MagicMock()
        client = get_service_client()
        mock_create.assert_called_once_with(
            "https://test.supabase.co", "service-key"
        )
        assert client is not None


def test_get_service_client_raises_when_not_configured():
    """Raises RuntimeError if env vars missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Supabase service role not configured"):
            get_service_client()


@pytest.mark.asyncio
async def test_get_current_user_extracts_user_from_jwt():
    """Valid JWT returns user dict with id and email."""
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer valid-token"

    mock_user = MagicMock()
    mock_user.user.id = "user-123"
    mock_user.user.email = "test@example.com"

    with patch("agent_fleet.api.deps.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_user
        mock_get_client.return_value = mock_client

        user = await get_current_user(mock_request)
        assert user == {"id": "user-123", "email": "test@example.com"}


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_token():
    """Missing Authorization header returns 401."""
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token():
    """Invalid token returns 401."""
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer bad-token"

    with patch("agent_fleet.api.deps.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = Exception("Invalid token")
        mock_get_client.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        assert exc_info.value.status_code == 401
