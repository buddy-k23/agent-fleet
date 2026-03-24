"""API key management — encrypted storage + CRUD."""

import base64
import hashlib
import os

import structlog
from cryptography.fernet import Fernet

from agent_fleet.api.deps import get_supabase_client

logger = structlog.get_logger()


def _get_fernet() -> Fernet:
    """Get Fernet cipher from ENCRYPTION_KEY env var (or derive from JWT_SECRET)."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # Derive from JWT_SECRET or a default
        secret = os.getenv("JWT_SECRET", "default-dev-key-change-in-production")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        return Fernet(key)
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_key(api_key: str) -> str:
    """Encrypt an API key."""
    f = _get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    """Decrypt an API key."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def mask_key(api_key: str) -> str:
    """Mask an API key for display: sk-ant-***...QwAA."""
    if len(api_key) <= 10:
        return "***"
    return api_key[:6] + "***..." + api_key[-4:]


def store_api_key(
    user_id: str, provider: str, api_key: str, label: str = ""
) -> dict | None:
    """Store an encrypted API key."""
    client = get_supabase_client()
    if not client:
        return None

    encrypted = encrypt_key(api_key)
    result = client.table("api_keys").insert({
        "user_id": user_id,
        "provider": provider,
        "encrypted_key": encrypted,
        "label": label,
    }).execute()

    logger.info("api_key_stored", provider=provider, user_id=user_id)
    return result.data[0] if result.data else None


def list_api_keys(user_id: str) -> list[dict]:
    """List API keys for a user (masked)."""
    client = get_supabase_client()
    if not client:
        return []

    result = (
        client.table("api_keys")
        .select("id, provider, label, is_active, created_at, encrypted_key")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )

    keys = []
    for row in result.data:
        try:
            decrypted = decrypt_key(row["encrypted_key"])
            masked = mask_key(decrypted)
        except Exception:
            masked = "***invalid***"

        keys.append({
            "id": row["id"],
            "provider": row["provider"],
            "label": row["label"],
            "is_active": row["is_active"],
            "masked_key": masked,
            "created_at": row["created_at"],
        })
    return keys


def get_api_key(user_id: str, provider: str) -> str | None:
    """Get decrypted API key for a provider. Returns None if not found."""
    client = get_supabase_client()
    if not client:
        return None

    result = (
        client.table("api_keys")
        .select("encrypted_key")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    try:
        return decrypt_key(result.data[0]["encrypted_key"])
    except Exception:
        logger.warning("api_key_decrypt_failed", provider=provider)
        return None


def delete_api_key(key_id: str) -> None:
    """Delete an API key."""
    client = get_supabase_client()
    if client:
        client.table("api_keys").delete().eq("id", key_id).execute()
        logger.info("api_key_deleted", key_id=key_id)
