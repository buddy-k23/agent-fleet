"""Supabase-backed repositories for Agent Fleet state store."""

import structlog

from supabase import Client

logger = structlog.get_logger()


class SupabaseTaskRepository:
    """Task CRUD via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(
        self, task_id: str, user_id: str, repo_path: str, description: str, workflow: str
    ) -> dict:
        result = self._client.table("tasks").insert({
            "id": task_id,
            "user_id": user_id,
            "repo": repo_path,
            "description": description,
            "workflow_name": workflow,
            "status": "queued",
        }).execute()
        logger.info("task_created", task_id=task_id)
        return result.data[0] if result.data else {}

    def get(self, task_id: str) -> dict | None:
        result = self._client.table("tasks").select("*").eq("id", task_id).execute()
        return result.data[0] if result.data else None

    def update_status(self, task_id: str, status: str, **kwargs: object) -> None:
        update = {"status": status, **kwargs}
        self._client.table("tasks").update(update).eq("id", task_id).execute()
        logger.info("task_status_updated", task_id=task_id, status=status)

    def list_by_user(self, user_id: str) -> list[dict]:
        result = (
            self._client.table("tasks")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    def list_by_status(self, status: str) -> list[dict]:
        result = self._client.table("tasks").select("*").eq("status", status).execute()
        return result.data


class SupabaseExecutionRepository:
    """Execution CRUD via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(
        self, task_id: str, stage: str, agent: str, model: str
    ) -> dict:
        result = self._client.table("executions").insert({
            "task_id": task_id,
            "stage": stage,
            "agent": agent,
            "model": model,
            "status": "running",
        }).execute()
        return result.data[0] if result.data else {}

    def update_status(
        self, execution_id: str, status: str, summary: str | None = None
    ) -> None:
        update: dict = {"status": status}
        if summary:
            update["summary"] = summary
        self._client.table("executions").update(update).eq("id", execution_id).execute()

    def list_by_task(self, task_id: str) -> list[dict]:
        result = (
            self._client.table("executions")
            .select("*")
            .eq("task_id", task_id)
            .order("started_at")
            .execute()
        )
        return result.data


class SupabaseEventRepository:
    """Append-only event log via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def append(
        self, task_id: str, event_type: str, payload: dict, execution_id: str | None = None
    ) -> dict:
        data: dict = {
            "task_id": task_id,
            "event_type": event_type,
            "payload": payload,
        }
        if execution_id:
            data["execution_id"] = execution_id
        result = self._client.table("events").insert(data).execute()
        return result.data[0] if result.data else {}

    def list_for_task(self, task_id: str) -> list[dict]:
        result = (
            self._client.table("events")
            .select("*")
            .eq("task_id", task_id)
            .order("timestamp")
            .execute()
        )
        return result.data


class SupabaseAgentRepository:
    """Agent config CRUD via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, user_id: str, agent_data: dict) -> dict:
        agent_data["user_id"] = user_id
        result = self._client.table("agents").insert(agent_data).execute()
        logger.info("agent_created", name=agent_data.get("name"))
        return result.data[0] if result.data else {}

    def list_by_user(self, user_id: str) -> list[dict]:
        result = (
            self._client.table("agents")
            .select("*")
            .eq("user_id", user_id)
            .order("name")
            .execute()
        )
        return result.data

    def update(self, agent_id: str, agent_data: dict) -> dict:
        result = (
            self._client.table("agents")
            .update(agent_data)
            .eq("id", agent_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, agent_id: str) -> None:
        self._client.table("agents").delete().eq("id", agent_id).execute()
        logger.info("agent_deleted", agent_id=agent_id)


class SupabaseWorkflowRepository:
    """Workflow config CRUD via Supabase."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, user_id: str, workflow_data: dict) -> dict:
        workflow_data["user_id"] = user_id
        result = self._client.table("workflows").insert(workflow_data).execute()
        logger.info("workflow_created", name=workflow_data.get("name"))
        return result.data[0] if result.data else {}

    def list_by_user(self, user_id: str) -> list[dict]:
        result = (
            self._client.table("workflows")
            .select("*")
            .eq("user_id", user_id)
            .order("name")
            .execute()
        )
        return result.data

    def get(self, workflow_id: str) -> dict | None:
        result = (
            self._client.table("workflows")
            .select("*")
            .eq("id", workflow_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def update(self, workflow_id: str, workflow_data: dict) -> dict:
        result = (
            self._client.table("workflows")
            .update(workflow_data)
            .eq("id", workflow_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, workflow_id: str) -> None:
        self._client.table("workflows").delete().eq("id", workflow_id).execute()
        logger.info("workflow_deleted", workflow_id=workflow_id)
